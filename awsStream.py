# --- awsStream.py ---
import asyncio
import cv2
import aiohttp
import json
import pyaudio
import numpy as np
import RPi.GPIO as GPIO
from av import AudioFrame, VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack

SIGNALING_SERVER = "http://54.151.64.7:8000"
BUTTON_GPIO_PIN = 17  # Adjust as needed

stream_instance = None  # Global reference to the stream

def setup_stream_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

class PiVideoStream(MediaStreamTrack):
    kind = "video"
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        self.paused = False

    def pause(self):
        self.paused = True
        self.cap.release()  # 🔥 releases the lock on the camera

    def resume(self):
       self.cap = cv2.VideoCapture(0)  # 🔁 reacquire camera
       self.paused = False


    async def recv(self):
        if self.paused:
            await asyncio.sleep(0.04)
            return None

        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

class PushToTalkAudio(MediaStreamTrack):
    kind = "audio"
    def __init__(self):
        super().__init__()
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=320)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        if GPIO.input(BUTTON_GPIO_PIN) == GPIO.LOW:
            audio_data = self.stream.read(320, exception_on_overflow=False)
        else:
            audio_data = (np.zeros(320, dtype=np.int16)).tobytes()

        frame = AudioFrame.from_ndarray(np.frombuffer(audio_data, dtype=np.int16), layout="mono", format="s16")
        frame.pts = pts
        frame.time_base = time_base
        return frame

async def start_stream():
    global stream_instance
    stream_instance = PiVideoStream()

    pc = RTCPeerConnection()
    pc.addTrack(stream_instance)
    pc.addTrack(PushToTalkAudio())

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    async with aiohttp.ClientSession() as session:
        await session.post(f"{SIGNALING_SERVER}/offer", json={
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })

        while True:
            async with session.get(f"{SIGNALING_SERVER}/answer") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "sdp" in data:
                        answer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                        await pc.setRemoteDescription(answer)
                        print("✅ WebRTC connection established!")
                        break
            await asyncio.sleep(1)

    while True:
        await asyncio.sleep(1)
