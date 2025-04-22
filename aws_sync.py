import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError
from botocore.config import Config

S3_BUCKET_NAME = "doorinfo"
OVERRIDE_FILE = "door_override.json"
STATUS_FILE = "door_status.json"
LOG_FILE = "door_log.txt"

s3_client = boto3.client("s3", config=Config(signature_version='s3v4'))

def upload_log_and_status(action, lock_status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - {action}\n"

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=LOG_FILE)
        existing_logs = response["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        existing_logs = ""

    updated_logs = existing_logs + log_message
    s3_client.put_object(Body=updated_logs.encode("utf-8"), Bucket=S3_BUCKET_NAME, Key=LOG_FILE)

    # Only update status file if we have a valid lock_status
    if lock_status is not None:
        status_data = {"timestamp": timestamp, "lock_status": lock_status}
        s3_client.put_object(Body=json.dumps(status_data).encode("utf-8"), Bucket=S3_BUCKET_NAME, Key=STATUS_FILE)


def fetch_override_status():
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=OVERRIDE_FILE)
        content = response["Body"].read().decode("utf-8")
        override_data = json.loads(content)
        return bool(override_data.get("door_override", None))
    except (ClientError, json.JSONDecodeError) as e:
        print(f"[WARN] Could not fetch override file: {e}")
        return None
