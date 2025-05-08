
# --- Shared RealSense Pipeline ---
pipeline = None

def get_shared_pipeline():
    global pipeline
    if pipeline is None:
        pipeline = get_shared_pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 1280, 800, rs.format.bgr8, 30)
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        # Start handled by get_shared_pipeline()
        print("[INFO] Shared RealSense pipeline started.")
    return pipeline

def stop_shared_pipeline():
    global pipeline
    if pipeline:
        stop_shared_pipeline()
        print("[INFO] Shared RealSense pipeline stopped.")
        pipeline = None

import asyncio
import threading
import time
import datetime
import os
import subprocess
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
AUDIO_BUCKET = "audioforstream"
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
LAST_PLAYED_FILE = ""
AUDIO_POLL_INTERVAL = 1  # seconds

# --- Upload helper ---
def upload_to_s3(filepath, bucket):
    filename = os.path.basename(filepath)
    try:
        s3.upload_file(filepath, bucket, filename)
        print(f"[UPLOAD] {filename} → s3://{bucket}/{filename}")
        os.remove(filepath)
    except Exception as e:
        print(f"[ERROR] Failed to upload {filename} to {bucket}: {e}")

# --- Audio polling and playback ---
def start_audio_polling_thread():
    def poll_audio():
        global LAST_PLAYED_FILE
        print("[AUDIO] Starting audio polling thread...")

        while True:
            try:
                response = s3.list_objects_v2(Bucket=AUDIO_BUCKET)
                for obj in response.get("Contents", []):
                    key = obj["Key"]
                    if key == LAST_PLAYED_FILE:
                        continue

                    if not key.lower().endswith((".mp3", ".wav", ".ogg", ".3gp")):
                        continue

                    local_path = f"/tmp/{key}"
                    print(f"[AUDIO] New file found: {key}. Downloading...")

                    s3.download_file(AUDIO_BUCKET, key, local_path)

                    # Play audio
                    print(f"[AUDIO] Playing: {local_path}")
                    try:
                        subprocess.run(["ffplay", "-nodisp", "-autoexit", local_path], check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"[AUDIO] Failed to play audio: {e}")

                    # Delete after playing
                    s3.delete_object(Bucket=AUDIO_BUCKET, Key=key)
                    print(f"[AUDIO] Deleted {key} from S3 bucket.")
                    LAST_PLAYED_FILE = key

            except Exception as e:
                print(f"[AUDIO] Error while polling audio bucket: {e}")

            time.sleep(AUDIO_POLL_INTERVAL)

    threading.Thread(target=poll_audio, daemon=True).start()

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
            self.pipeline = get_shared_pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            self.# Start handled by get_shared_pipeline()
            print("[RealSense] Camera pipeline started.")

    def stop(self):
        self.keep_recording = False
        with streaming_lock:
            if self.pipeline:
                self.stop_shared_pipeline()
                self.pipeline = None
                print("[RealSense] Camera pipeline stopped.")

    def record_loop(self):
        global last_motion_upload_time

        while self.keep_recording:
            now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            base = os.path.join(OUTPUT_DIR, now)
            video_file = base + ".mp4"
            audio_file = base + ".wav"
            stitched_file = base + "_final.mp4"

            out = cv2.VideoWriter(video_file, cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 480))
            start_time = time.time()

            audio_proc = subprocess.Popen([
                "arecord", "-D", "hw:2,0", "-f", "S16_LE",
                "-r", "44100", "-c", "2", "-d", str(RECORD_SECONDS),
                audio_file
            ])

            while time.time() - start_time < RECORD_SECONDS and self.keep_recording:
                with streaming_lock:
                    if self.pipeline:
                        frames = self.pipeline.wait_for_frames()
                        color_frame = frames.get_color_frame()
                        if color_frame:
                            img = np.asanyarray(color_frame.get_data())
                            out.write(img)

            out.release()
            audio_proc.wait()

            if not os.path.exists(video_file) or not os.path.exists(audio_file):
                print("[WARN] Skipping upload – missing video or audio")
                continue

            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", video_file, "-i", audio_file,
                    "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", stitched_file
                ], check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] ffmpeg stitching failed: {e}")
                continue

            upload_bucket = DEFAULT_BUCKET
            if self.motion_check_fn:
                try:
                    is_motion = self.motion_check_fn()
                    now_time = time.time()
                    if is_motion and now_time - last_motion_upload_time >= MOTION_COOLDOWN:
                        last_motion_upload_time = now_time
                        upload_bucket = MOTION_BUCKET
                        print(f"[MOTION DETECTED] Uploading stitched clip to {upload_bucket}")
                except Exception as e:
                    print(f"[WARN] Motion check failed: {e}")

            upload_to_s3(stitched_file, upload_bucket)

            for f in [video_file, audio_file]:
                if os.path.exists(f):
                    os.remove(f)

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

# --- Startup tasks ---
start_audio_polling_thread()

