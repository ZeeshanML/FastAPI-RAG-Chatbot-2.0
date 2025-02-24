import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

class S3Client:
    def __init__(self):
        logger.info("Initializing S3 client")
        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=os.environ.get("CUSTOM_AWS_ACCESS_KEY"),
                aws_secret_access_key=os.environ.get("CUSTOM_AWS_SECRET_KEY"),
                region_name=os.environ.get("CUSTOM_AWS_REGION")
            )
            self.bucket_name = os.environ.get("AWS_BUCKET_NAME")
            logger.info(f"S3 client initialized with bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}", exc_info=True)
            raise

    async def upload_file(self, file_path: str, filename: str) -> str:
        """Upload a file to S3 bucket and return its URL"""
        try:
            logger.info(f"Uploading file to S3: {filename}")
            self.s3_client.upload_file(file_path, self.bucket_name, filename)
            url = f"https://{self.bucket_name}.s3.{AWS_REGION}.amazonaws.com/{filename}"
            logger.info(f"Successfully uploaded file to S3: {url}")
            return url
        except ClientError as e:
            logger.error(f"S3 upload error for file {filename}: {str(e)}", exc_info=True)
            raise

    async def delete_file(self, filename: str) -> bool:
        """Delete a file from S3 bucket"""
        try:
            logger.info(f"Deleting file from S3: {filename}")
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            logger.info(f"Successfully deleted file from S3: {filename}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file {filename} from S3: {str(e)}", exc_info=True)
            raise