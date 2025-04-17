
import os
import cv2
import time
import numpy as np
import pyrealsense2 as rs
from datetime import datetime

PERSON_NAME = "kolade"

def create_folder(name):
    dataset_folder = "dataset"
    if not os.path.exists(dataset_folder):
        os.makedirs(dataset_folder)
    
    person_folder = os.path.join(dataset_folder, name)
    if not os.path.exists(person_folder):
        os.makedirs(person_folder)
    return person_folder

def capture_photos(name):
    folder = create_folder(name)

    # Configure RealSense pipeline
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 1280, 800, rs.format.bgr8, 30)
    
    print("[INFO] Starting RealSense camera...")
    pipeline.start(config)
    time.sleep(2)  # Warm-up time

    photo_count = 0
    print(f"[INFO] Taking photos for {name}. Press SPACE to capture, 'q' to quit.")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            color_image = np.asanyarray(color_frame.get_data())
            cv2.imshow("RealSense Capture", color_image)

            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(folder, f"{name}_{timestamp}.jpg")
                cv2.imwrite(filepath, color_image)
                print(f"[CAPTURED] Saved image: {filepath}")
                photo_count += 1
            elif key == ord('q'):
                print("[EXIT] Quitting capture.")
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_photos(PERSON_NAME)
