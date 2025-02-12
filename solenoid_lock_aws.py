import RPi.GPIO as GPIO
import time
import boto3
import json
from datetime import datetime

# GPIO Pin where the relay IN is connected
RELAY_PIN = 17

# AWS S3 Configuration
S3_BUCKET_NAME = "doorinfo"
s3_client = boto3.client("s3")

def upload_log_to_s3(action, lock_status):
    """
    Uploads a log entry to the S3 bucket and updates a JSON file with lock status.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - {action}\n"

    # Define file names
    log_file_name = "door_log.txt"
    json_file_name = "door_status.json"

    try:
        # Get existing log file from S3 (if it exists)
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=log_file_name)
        existing_logs = response["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        existing_logs = ""

    # Append the new log entry
    updated_logs = existing_logs + log_message

    # Upload the updated log file
    s3_client.put_object(Body=updated_logs.encode("utf-8"), Bucket=S3_BUCKET_NAME, Key=log_file_name)
    print(f"Log uploaded to S3: {log_message.strip()}")

    # Create JSON file with the latest lock status
    lock_data = {
        "timestamp": timestamp,
        "lock_status": lock_status  # True = Locked, False = Unlocked
    }

    # Upload JSON file to S3
    s3_client.put_object(Body=json.dumps(lock_data), Bucket=S3_BUCKET_NAME, Key=json_file_name)
    print(f"Lock status updated in S3: {lock_data}")

# GPIO Setup
GPIO.setmode(GPIO.BCM)  # Use BCM numbering
GPIO.setup(RELAY_PIN, GPIO.OUT)  # Set the relay pin as an output

try:
    while True:
        # Turn the solenoid lock ON
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        print("Lock ON")
        upload_log_to_s3("Lock ON", True)  # Send signal with True (locked)
        time.sleep(5)  # Keep the lock ON for 5 seconds

        # Turn the solenoid lock OFF
        GPIO.output(RELAY_PIN, GPIO.LOW)
        print("Lock OFF")
        upload_log_to_s3("Lock OFF", False)  # Send signal with False (unlocked)
        time.sleep(5)  # Keep the lock OFF for 5 seconds

except KeyboardInterrupt:
    print("Exiting program.")
    GPIO.cleanup()  # Reset GPIO settings
