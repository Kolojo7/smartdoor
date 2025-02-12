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

try:
    while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        color_image = np.asanyarray(color_frame.get_data())

        # Convert to JPEG format
        _, buffer = cv2.imencode(".jpg", color_image)

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S%f")[:-3]  # Include milliseconds
        filename = f"frame_{timestamp}.jpg"

        # Upload to S3
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=buffer.tobytes(), ContentType="image/jpeg")
        print(f"Uploaded {filename} to S3")

        # Display the live feed
        cv2.imshow("RealSense D455 Live Feed", color_image)

        # Sleep for 0.5 seconds for near real-time streaming (adjustable)
        time.sleep(0.5)

        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
