import pyrealsense2 as rs
import numpy as np
import cv2
import boto3
import time
from datetime import datetime

# AWS S3 Configuration
S3_BUCKET_NAME = "smartdoorlivefeed"

# Initialize S3 client
s3_client = boto3.client("s3")

# Configure RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

# Define video parameters
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4
fps = 30
frame_size = (640, 480)

# Start recording
video_filename = "live_feed.mp4"
out = cv2.VideoWriter(video_filename, fourcc, fps, frame_size)

# Upload interval (in seconds)
upload_interval = 30  
last_upload_time = time.time()

try:
    while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        color_image = np.asanyarray(color_frame.get_data())
        out.write(color_image)  # Write frame to video file

        # Display live feed (optional)
        cv2.imshow("RealSense D455 Live Feed", color_image)

        # Check if it's time to upload the video
        if time.time() - last_upload_time > upload_interval:
            out.release()  # Save the video file before upload
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            s3_filename = f"live_feed_{timestamp}.mp4"

            # Upload the recorded video
            with open(video_filename, "rb") as video_file:
                s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=s3_filename, Body=video_file, ContentType="video/mp4")
                print(f"Uploaded {s3_filename} to S3")

            # Reset for new recording
            out = cv2.VideoWriter(video_filename, fourcc, fps, frame_size)
            last_upload_time = time.time()

        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    out.release()
    pipeline.stop()
    cv2.destroyAllWindows()
