import face_recognition
import cv2
import numpy as np
import pyrealsense2 as rs
import time
import pickle
import csv
import os
import boto3
from datetime import datetime
# from gpiozero import LED
import mediapipe as mp

# ------------------ Configuration ------------------
AUTHORIZED_NAMES = ["kolade"]
CSV_LOG = "access_log.csv"
CONFIRM_TIME = 3
DEPTH_VARIATION = 0.03
LANDMARKS = [1, 234, 454, 152]
S3_BUCKET_FAILED = "smartdoor-events"
S3_FOLDER_FAILED = "Error Logs"
S3_BUCKET_RECOGNIZED = "smartdoorpictures"
S3_FOLDER_ACCEPTED = "accepted"
S3_FOLDER_REJECTED = "rejected"
LOCAL_TMP_DIR = "tmp_failed"
os.makedirs(LOCAL_TMP_DIR, exist_ok=True)
s3 = boto3.client("s3")
# ---------------------------------------------------

print("[INFO] Loading face encodings...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())
known_encodings = data["encodings"]
known_names = data["names"]

# GPIO (optional)
# output = LED(14)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 1280, 800, rs.format.bgr8, 30)
pipeline.start(config)
align = rs.align(rs.stream.color)

if not os.path.exists(CSV_LOG):
    with open(CSV_LOG, "w", newline="") as f:
        csv.writer(f).writerow(["Name", "Timestamp", "Status"])

def get_depth(depth_frame, x, y):
    try:
        return depth_frame.get_distance(int(x), int(y))
    except:
        return 0.0

def is_real_face(depth_frame, landmarks, w, h):
    depths = [get_depth(depth_frame, int(lm.x * w), int(lm.y * h)) for lm in [landmarks[i] for i in LANDMARKS]]
    return max(depths) - min(depths) > DEPTH_VARIATION

def recognize_faces(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locs = face_recognition.face_locations(rgb)
    encs = face_recognition.face_encodings(rgb, locs)
    names = []
    for enc in encs:
        matches = face_recognition.compare_faces(known_encodings, enc)
        name = "Unknown"
        distances = face_recognition.face_distance(known_encodings, enc)
        if len(distances) > 0:
            best_match = np.argmin(distances)
            if matches[best_match]:
                name = known_names[best_match]
        names.append(name)
    return locs, names

def draw_faces(frame, locs, names):
    for (top, right, bottom, left), name in zip(locs, names):
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
        cv2.rectangle(frame, (left, top - 35), (right, top), (0, 0, 255), cv2.FILLED)
        cv2.putText(frame, name, (left + 6, top - 10), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
        if name in AUTHORIZED_NAMES:
            cv2.putText(frame, "Authorized", (left + 6, bottom + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    return frame

def log(name, status):
    timestamp = time.strftime("%Y-%m-%d %I:%M:%S %p")
    with open(CSV_LOG, "a", newline="") as f:
        csv.writer(f).writerow([name, timestamp, status])
    print(f"[LOG] {name} @ {timestamp} | {status}")

confirm_start = None
face_ready = False

try:
    while True:
        frames = pipeline.wait_for_frames()
        frames = align.process(frames)
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)
        display = frame.copy()

        if result.multi_face_landmarks:
            lm = result.multi_face_landmarks[0].landmark
            h, w, _ = frame.shape
            if is_real_face(depth_frame, lm, w, h):
                if confirm_start is None:
                    confirm_start = time.time()
                elif time.time() - confirm_start >= CONFIRM_TIME:
                    face_ready = True
            else:
                confirm_start = None
        else:
            confirm_start = None

        if face_ready:
            print("[INFO] ✅ Real face confirmed, capturing new frame...")
            for _ in range(3):
                pipeline.wait_for_frames()
            fresh = align.process(pipeline.wait_for_frames()).get_color_frame()
            if fresh:
                fresh_img = np.asanyarray(fresh.get_data())
                locs, names = recognize_faces(fresh_img)

                if not locs:
                    gray = cv2.cvtColor(fresh_img, cv2.COLOR_BGR2GRAY)
                    brightness = np.mean(gray)
                    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                    print(f"[DEBUG] Brightness: {brightness:.2f}")
                    print(f"[DEBUG] Laplacian variance: {sharpness:.2f}")

                    if brightness < 60:
                        reason = "Too dark"
                    elif brightness > 200:
                        reason = "Too bright"
                    elif sharpness < 100:
                        reason = "Too blurry"
                    else:
                        reason = "Unclear cause"

                    filename = f"{datetime.now().strftime('%Y-%m-%d_%I-%M-%S_%p')}_{reason.replace(' ', '_')}.jpg"
                    local_path = os.path.join(LOCAL_TMP_DIR, filename)
                    cv2.imwrite(local_path, fresh_img)

                    try:
                        s3.upload_file(local_path, S3_BUCKET_FAILED, f"{S3_FOLDER_FAILED}/{filename}")
                        print(f"[UPLOAD] Sent {filename} to S3 → s3://{S3_BUCKET_FAILED}/{S3_FOLDER_FAILED}/")
                    except Exception as e:
                        print(f"[ERROR] Failed to upload to S3: {e}")

                    cv2.putText(display, f"Detection Failed: {reason}", (20, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    display = draw_faces(fresh_img, locs, names)
                    for name in names:
                        timestamp = datetime.now().strftime('%Y-%m-%d_%I-%M-%S_%p')
                        upload_name = f"{timestamp}_{name}.jpg"
                        is_authorized = name in AUTHORIZED_NAMES

                        _, buffer = cv2.imencode(".jpg", fresh_img)
                        try:
                            s3.put_object(Bucket=S3_BUCKET_RECOGNIZED,
                                          Key=f"{S3_FOLDER_ACCEPTED if is_authorized else S3_FOLDER_REJECTED}/{upload_name}",
                                          Body=buffer.tobytes(),
                                          ContentType='image/jpeg')
                            print(f"[UPLOAD] Sent to s3://{S3_BUCKET_RECOGNIZED}/{'accepted' if is_authorized else 'rejected'}/{upload_name}")
                        except Exception as e:
                            print(f"[ERROR] Upload to S3 failed: {e}")

                        log(name, "Authorized" if is_authorized else "Unknown")
                        cv2.putText(display,
                                    "Access Granted" if is_authorized else "Access Denied",
                                    (20, 70),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    1,
                                    (0, 255, 0) if is_authorized else (0, 0, 255),
                                    2)

            print("[INFO] Face logged. Shutting down...")
            break

        elif confirm_start:
            elapsed = time.time() - confirm_start
            cv2.putText(display, f"Authenticating... {elapsed:.1f}s", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Face Recognition", display)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    # output.off()