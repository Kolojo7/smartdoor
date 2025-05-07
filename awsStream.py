import asyncio
import threading
import time
import datetime
import os
import cv2
import numpy as np
import boto3
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import pyrealsense2 as rs
import av

# --- Config ---
SIGNALING_SERVER = "http://54.151.64.7:8000"
DEFAULT_BUCKET = "streambuffer"
MOTION_BUCKET = "smartdoor-events"
RECORD_SECONDS = 5
MOTION_COOLDOWN = 30
OUTPUT_DIR = "/home/pi/streambuffer"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Globals ---
s3 = boto3.client("s3")
streaming_event = threading.Event()
stop_event = threading.Event()
streaming_lock = threading.Lock()
video_track_instance = None
last_motion_upload_time = 0

# --- Upload helper ---
def upload_to_s3(filepath, bucket):
    filename = os.path.basename(filepath)
    try:
        s3.upload_file(filepath, bucket, filename)
        print(f"[UPLOAD] {filename} → s3://{bucket}/{filename}")
        os.remove(filepath)
    except Exception as e:
        print(f"[ERROR] Failed to upload {filename} to {bucket}: {e}")

# --- RealSense Track ---
class RealSenseVideoTrack(VideoStreamTrack):
    def __init__(self, motion_check_fn=None):
        super().__init__()
        self.motion_check_fn = motion_check_fn
        self.pipeline = None
        self.keep_recording = True
        self.start_pipeline()

        self.recording_thread = threading.Thread(target=self.record_loop, daemon=True)
        self.recording_thread.start()

    def start_pipeline(self):
        with streaming_lock:
            self.pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            self.pipeline.start(config)
            print("[RealSense] Camera pipeline started.")

    def stop(self):
        self.keep_recording = False
        with streaming_lock:
            if self.pipeline:
                self.pipeline.stop()
                self.pipeline = None
                print("[RealSense] Camera pipeline stopped.")

    def record_loop(self):
        global last_motion_upload_time

        while self.keep_recording:
            now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.join(OUTPUT_DIR, f"{now}.mp4")
            out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 480))
            start_time = time.time()

            while time.time() - start_time < RECORD_SECONDS and self.keep_recording:
                with streaming_lock:
                    if self.pipeline:
                        frames = self.pipeline.wait_for_frames()
                        color_frame = frames.get_color_frame()
                        if color_frame:
                            img = np.asanyarray(color_frame.get_data())
                            out.write(img)

            out.release()

            if not os.path.exists(filename):
                continue

            # 🧠 Decide which bucket to use
            bucket = DEFAULT_BUCKET
            if self.motion_check_fn:
                try:
                    is_motion = self.motion_check_fn()
                    now_time = time.time()
                    if is_motion and now_time - last_motion_upload_time >= MOTION_COOLDOWN:
                        bucket = MOTION_BUCKET
                        last_motion_upload_time = now_time
                        print(f"[MOTION DETECTED] Uploading chunk to {bucket}")
                except Exception as e:
                    print(f"[WARN] Motion check failed: {e}")

            upload_to_s3(filename, bucket)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        with streaming_lock:
            if not self.pipeline:
                await asyncio.sleep(0.01)
                return await self.recv()

            frames = self.pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                await asyncio.sleep(0.01)
                return await self.recv()

            img = np.asanyarray(color_frame.get_data())
            frame = av.VideoFrame.from_ndarray(img, format="bgr24")
            frame.pts = pts
            frame.time_base = time_base
            return frame

# --- WebRTC streaming ---
async def stream_offer(video_track):
    print("[WebRTC] Connecting to signaling server...")
    pc = RTCPeerConnection()
    pc.addTrack(video_track)

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    async with aiohttp.ClientSession() as session:
        await session.post(f"{SIGNALING_SERVER}/offer", json={
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })

        while True:
            async with session.get(f"{SIGNALING_SERVER}/answer") as resp:
                data = await resp.json()
                if data.get("sdp"):
                    print("[WebRTC] Received answer.")
                    await pc.setRemoteDescription(
                        RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                    )
                    break
            await asyncio.sleep(1)

    print("[WebRTC] Streaming started.")
    while streaming_event.is_set() and not stop_event.is_set():
        await asyncio.sleep(1)

    print("[WebRTC] Stopping stream...")
    video_track.stop()
    await pc.close()
    cv2.destroyAllWindows()

# --- Controls ---
def start_streaming_thread(motion_check_fn=None):
    global video_track_instance
    if streaming_event.is_set():
        print("[awsStream] Streaming is already active. Skipping start.")
        return

    streaming_event.set()
    stop_event.clear()

    def run():
        global video_track_instance
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            video_track_instance = RealSenseVideoTrack(motion_check_fn)
            loop.run_until_complete(stream_offer(video_track_instance))
        except Exception as e:
            print(f"[ERROR] Streaming thread failed: {e}")
            video_track_instance = None

    threading.Thread(target=run, daemon=True).start()

def pause_streaming():
    global video_track_instance
    print("[awsStream] Pausing stream...")
    stop_event.set()
    streaming_event.clear()
    time.sleep(1)

    with streaming_lock:
        if video_track_instance:
            try:
                video_track_instance.stop()
                video_track_instance = None
                print("[awsStream] Stream paused and camera released.")
            except Exception as e:
                print(f"[ERROR] Failed to stop stream: {e}")

def resume_streaming():
    print("[awsStream] Resuming stream...")
    start_streaming_thread()

def stop_streaming():
    print("[awsStream] Stopping stream.")
    stop_event.set()
    streaming_event.clear()

