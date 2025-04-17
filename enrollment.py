import os
import cv2
import time
import json
import boto3
import shutil
import numpy as np
import pyrealsense2 as rs
from datetime import datetime
import random
import pickle
from imutils import paths
import face_recognition

PHOTO_MIN = 5
PHOTO_MAX = 10
PAUSE_TIME = 1  # seconds between each photo

def get_current_username():
    s3 = boto3.client('s3')
    bucket = 'smartdooraccounts'
    key = 'currentUser/currentUser.json'
    local_path = 'currentUser.json'

    print("[INFO] Downloading currentUser.json from S3...")
    s3.download_file(bucket, key, local_path)

    with open(local_path, 'r') as f:
        data = json.load(f)

    username = data.get("username")
    if not username:
        raise ValueError("[ERROR] 'username' not found in currentUser.json")

    print(f"[INFO] Loaded username: {username}")
    return username

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

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 1280, 800, rs.format.bgr8, 30)
    
    print("[INFO] Starting RealSense camera...")
    pipeline.start(config)
    time.sleep(2)

    photo_count = 0
    total_photos = random.randint(PHOTO_MIN, PHOTO_MAX)
    print(f"[INFO] Capturing {total_photos} face-verified photos for {name}...")

    try:
        while photo_count < total_photos:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            color_image = np.asanyarray(color_frame.get_data())

            # Check if a face is present
            rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb)

            if len(locs) == 0:
                print("[SKIP] No face detected in frame.")
                time.sleep(PAUSE_TIME)
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(folder, f"{name}_{timestamp}.jpg")
            cv2.imwrite(filepath, color_image)
            print(f"[CAPTURED] {photo_count + 1}/{total_photos}: {filepath}")
            photo_count += 1

            time.sleep(PAUSE_TIME)
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
        print("[INFO] Done capturing.")

def auto_enroll_person(name):
    folder_path = os.path.join("dataset", name)
    if not os.path.exists(folder_path):
        print(f"[ERROR] Folder not found for {name}")
        return

    print(f"[INFO] Enrolling faces for: {name}")
    imagePaths = list(paths.list_images(folder_path))
    knownEncodings = []
    knownNames = []

    for (i, imagePath) in enumerate(imagePaths):
        print(f"[INFO] Processing image {i + 1}/{len(imagePaths)}")

        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        boxes = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, boxes)

        for encoding in encodings:
            knownEncodings.append(encoding)
            knownNames.append(name)

    if not knownEncodings:
        print(f"[WARNING] No faces detected for {name}")
        return

    output_file = f"encodings_{name}.pickle"
    print(f"[INFO] Saving to {output_file}...")
    with open(output_file, "wb") as f:
        f.write(pickle.dumps({"encodings": knownEncodings, "names": knownNames}))
    print(f"[INFO] ✅ Enrollment complete")

    # Clean up folder
    print(f"[INFO] Deleting photo folder: {folder_path}")
    shutil.rmtree(folder_path, ignore_errors=True)

# --- Execute all steps immediately ---
username = get_current_username()
capture_photos(username)
auto_enroll_person(username)
