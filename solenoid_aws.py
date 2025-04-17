import RPi.GPIO as GPIO
import time
import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError
from botocore.config import Config

# GPIO Pin for the relay
RELAY_PIN = 17

# AWS S3 Configuration
S3_BUCKET_NAME = "doorinfo"
OVERRIDE_FILE = "door_override.json"
STATUS_FILE = "door_status.json"
LOG_FILE = "door_log.txt"

# S3 Client (with config to reduce caching issues)
s3_client = boto3.client("s3", config=Config(signature_version='s3v4'))

def upload_log_and_status(action, lock_status):
    """
    Uploads a log entry and lock status to S3.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - {action}\n"

    print(f"[DEBUG] Preparing to upload to S3")
    print(f"[DEBUG] Action: {action}")
    print(f"[DEBUG] Lock status: {lock_status}")
    print(f"[DEBUG] Timestamp: {timestamp}")

    # Fetch current log
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=LOG_FILE)
        existing_logs = response["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        existing_logs = ""

    updated_logs = existing_logs + log_message

    try:
        s3_client.put_object(Body=updated_logs.encode("utf-8"), Bucket=S3_BUCKET_NAME, Key=LOG_FILE)
        print(f"[DEBUG] Log updated successfully in {LOG_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to upload log: {e}")

    # Update status file
    status_data = {
        "timestamp": timestamp,
        "lock_status": lock_status
    }

    try:
        s3_client.put_object(
            Body=json.dumps(status_data).encode("utf-8"),
            Bucket=S3_BUCKET_NAME,
            Key=STATUS_FILE
        )
        print(f"[DEBUG] door_status.json updated: {status_data}")
    except Exception as e:
        print(f"[ERROR] Failed to update door_status.json: {e}")

def fetch_override_status():
    """
    Fetches the override boolean from S3.
    Returns True (lock ON) or False (lock OFF). Defaults to True if error.
    """
    try:
        print(f"[DEBUG] Fetching override file from S3 at {datetime.now()}")
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=OVERRIDE_FILE)
        content = response["Body"].read().decode("utf-8")
        print(f"[DEBUG] Raw override file content: {content}")

        override_data = json.loads(content)
        override_value = override_data.get("override", True)
        print(f"[DEBUG] Parsed override value: {override_value} (type: {type(override_value)})")
        return bool(override_value)
    except (ClientError, json.JSONDecodeError) as e:
        print(f"[ERROR] Failed to fetch or parse override file: {e}")
        return True  # Safe default to locked

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

try:
    last_state = None

    while True:
        override_status = fetch_override_status()
        print(f"[INFO] Override from file: {override_status}")
        print(f"[DEBUG] Last known state: {last_state}")
        print(f"[DEBUG] Comparison result: override_status={override_status} (type: {type(override_status)}), last_state={last_state} (type: {type(last_state)})")

        # Always set relay based on override status
        GPIO.output(RELAY_PIN, GPIO.HIGH if override_status else GPIO.LOW)
        pin_state = GPIO.input(RELAY_PIN)
        print(f"[DEBUG] Relay GPIO pin state: {pin_state} (1=LOCKED, 0=UNLOCKED)")

        # Update log/status only if state changed
        if override_status is True and last_state is not True:
            print("[ACTION] Locking the door...")
            upload_log_and_status("Lock ON", True)
            last_state = True
        elif override_status is False and last_state is not False:
            print("[ACTION] Unlocking the door...")
            upload_log_and_status("Lock OFF", False)
            last_state = False
        else:
            print("[DEBUG] No state change. No update needed.")

        print("[INFO] --- End of cycle ---\n")
        time.sleep(3)

except KeyboardInterrupt:
    print("Exiting program.")
    GPIO.cleanup()
