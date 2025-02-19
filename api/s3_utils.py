import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

class S3Client:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id = AWS_ACCESS_KEY_ID,
            aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
            region_name = AWS_REGION
        )
        self.bucket_name = AWS_BUCKET_NAME

    async def upload_file(self, file_path: str, filename: str) -> str:
        """Upload a file to S3 bucket and return its URL"""
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, filename)
            url = f"https://{self.bucket_name}.s3.{AWS_REGION}.amazonaws.com/{filename}"
            return url
        except ClientError as e:
            print(f"Failed to upload file to S3: {e}")
            raise

    async def delete_file(self, filename: str) -> bool:
        """Delete a file from S3 bucket"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            return True
        except ClientError as e:
            print(f"Error deleting from S3: {e}")
            raise