import RPi.GPIO as GPIO
import time
import boto3
from datetime import datetime

# GPIO Pin where the relay IN is connected
RELAY_PIN = 17

# AWS S3 Configuration
S3_BUCKET_NAME = "doorinfo"
s3_client = boto3.client("s3")

def upload_log_to_s3(action):
    """Uploads a log entry to the S3 bucket when the lock opens or closes."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - {action}\n"

    # Define file name and content
    file_name = "door_log.txt"

    try:
        # Get existing log file from S3
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=file_name)
        existing_logs = response["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        existing_logs = ""

    # Append the new log entry
    updated_logs = existing_logs + log_message

    # Upload the updated log file
    s3_client.put_object(Body=updated_logs.encode("utf-8"), Bucket=S3_BUCKET_NAME, Key=file_name)
    print(f"Log uploaded to S3: {log_message.strip()}")

# GPIO Setup
GPIO.setmode(GPIO.BCM)  # Use BCM numbering
GPIO.setup(RELAY_PIN, GPIO.OUT)  # Set the relay pin as an output

try:
    while True:
        # Turn the solenoid lock ON
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        print("Lock ON")
        upload_log_to_s3("Lock ON")  # Send signal to S3
        time.sleep(5)  # Keep the lock ON for 5 seconds

        # Turn the solenoid lock OFF
        GPIO.output(RELAY_PIN, GPIO.LOW)
        print("Lock OFF")
        upload_log_to_s3("Lock OFF")  # Send signal to S3
        time.sleep(5)  # Keep the lock OFF for 5 seconds

except KeyboardInterrupt:
    print("Exiting program.")
    GPIO.cleanup()  # Reset GPIO settings
