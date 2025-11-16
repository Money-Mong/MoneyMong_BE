"""
Lightweight helper to obtain a configured boto3 S3 client.
"""

import boto3

from app.config import get_settings


def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
