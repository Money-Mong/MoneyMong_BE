# app/services/s3_client.py

improt boto3
from app.config import settings

def get_s3_client():
    return boto3.client(
        "s3",
        region_name_settings.AWS_REGION,
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key = settings.AWS_SCRET_ACCESS_KEY,
    )
    