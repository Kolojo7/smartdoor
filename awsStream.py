import asyncio
import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
import subprocess

class VideoStreamTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)  # USB cam; use 0 or 1 depending on Pi camera setup

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Camera capture failed.")
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return VideoFrame.from_ndarray(frame_rgb, format="rgb24").rebuild(pts=pts, time_base=time_base)

def start_webrtc_stream():
    signaling = TcpSocketSignaling("your-aws-signaling-server.com", 1234)  #Server address to be set
    pc = RTCPeerConnection()

    #Video stream
    pc.addTrack(VideoStreamTrack())

    #Audio stream
    audio_cmd = ["arecord", "-f", "cd", "-t", "raw"]
    audio_process = subprocess.Popen(audio_cmd, stdout=subprocess.PIPE)
    audio_player = MediaPlayer(audio_process.stdout, format="s16le", channels=1, rate=44100)
    pc.addTrack(audio_player.audio)

    async def run():
        await signaling.connect()
        offer = await signaling.receive()
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await signaling.send(pc.localDescription)

        await pc.waitClosed()

    asyncio.run(run())
