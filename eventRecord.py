import cv2
import threading
import time
import pyaudio
import wave
import boto3
import os
import subprocess

# AWS config
S3_BUCKET = "smartdoor-events"
S3_REGION = "us-east-1"

# File paths
VIDEO_FILENAME = "/home/pi/smartdoor/latest_video.avi"
AUDIO_FILENAME = "/home/pi/smartdoor/latest_audio.wav"
FINAL_FILENAME = "/home/pi/smartdoor/final_output.mp4"

# Audio config
RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16

def record_audio(duration, stop_flag):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)
    frames = []

    print("🎙️ Recording audio...")
    for _ in range(0, int(RATE / CHUNK * duration)):
        if stop_flag.is_set():
            break
        frames.append(stream.read(CHUNK, exception_on_overflow=False))

    print("🛑 Audio recording finished.")
    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(AUDIO_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def record_video(duration, stop_flag):
    cap = cv2.VideoCapture(0)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(VIDEO_FILENAME, fourcc, 20.0, (640, 480))

    print("🎥 Recording video...")
    start = time.time()
    while time.time() - start < duration:
        if stop_flag.is_set():
            break
        ret, frame = cap.read()
        if ret:
            out.write(frame)

    print("🛑 Video recording finished.")
    cap.release()
    out.release()

def merge_audio_video():
    print("🎞️ Merging audio and video with ffmpeg...")
    cmd = [
        'ffmpeg',
        '-y',
        '-i', VIDEO_FILENAME,
        '-i', AUDIO_FILENAME,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        FINAL_FILENAME
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Merged file created:", FINAL_FILENAME)

def upload_to_s3():
    print("☁️ Uploading merged video to S3...")
    s3 = boto3.client('s3', region_name=S3_REGION)
    s3.upload_file(FINAL_FILENAME, S3_BUCKET, "recordings/smartdoor_capture.mp4")
    print("✅ Upload complete!")

def start_recording(duration=10):
    stop_flag = threading.Event()

    audio_thread = threading.Thread(target=record_audio, args=(duration, stop_flag))
    video_thread = threading.Thread(target=record_video, args=(duration, stop_flag))

    audio_thread.start()
    video_thread.start()

    audio_thread.join()
    video_thread.join()

    merge_audio_video()
    upload_to_s3()

def stop_recording():
    stop_flag.set()
