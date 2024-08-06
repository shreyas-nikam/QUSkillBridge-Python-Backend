import os
import boto3
import tempfile
from botocore.exceptions import NoCredentialsError, ClientError
import logging
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import os

load_dotenv()

class S3FileManager:
    def __init__(self):
        # Initialize AWS credentials and S3 client
        self.aws_access_key_id = os.environ.get("AWS_ACCESS_KEY")
        self.aws_secret_access_key = os.environ.get("AWS_SECRET_KEY")
        self.bucket_name = os.environ.get("AWS_BUCKET_NAME")
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )

    def upload_file(self, file_path, key):
        """
        Upload a file to S3

        Args:
        file_path: str - path to the file to be uploaded
        key: str - key to be used in the S3 bucket
        """
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, key)
            return True
        except FileNotFoundError:
            logging.error("The file was not found")
            return False
        except NoCredentialsError:
            logging.error("Credentials not available")
            return False
        except ClientError as e:
            logging.error(e)
            return False
    
    def list_files(self, key):
        """
        List all files in the S3 bucket with the given key
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=key)
            return response.get("Contents")
        except NoCredentialsError:
            logging.error("Credentials not available")
            return False
        except ClientError as e:
            logging.error(e)
            return False
        
    def download_file(self, key, download_path):
        """
        Download a file from S3

        Args:
        key: str - key of the file in the S3 bucket
        download_path: str - path to download the file
        """
        try:
            with open(download_path, 'wb') as f:
                self.s3_client.download_fileobj(self.bucket_name, key, f)
            return True
        except NoCredentialsError:
            logging.error("Credentials not available")
            return False
        except ClientError as e:
            logging.error(e)
            return False
    
    def delete_file(self, key):
        """
        Delete a file from S3

        Args:
        key: str - key of the file in the S3 bucket
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except NoCredentialsError:
            logging.error("Credentials not available")
            return False
        except ClientError as e:
            logging.error(e)
            return False
        
    def upload_file_from_bytes(self, data, key):
        """
        Upload a file to S3 from bytes

        Args:
        data: bytes - data to be uploaded
        key: str - key to be used in the S3 bucket
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(data)
                temp_file.close()
                self.upload_file(temp_file.name, key)
                os.unlink(temp_file.name)
            return True
        except NoCredentialsError:
            logging.error("Credentials not available")
            return False
        except ClientError as e:
            logging.error(e)
            return False
        
    def download_file_to_bytes(self, key):
        """
        Download a file from S3 to bytes

        Args:
        key: str - key of the file in the S3 bucket
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.close()
                self.download_file(key, temp_file.name)
                with open(temp_file.name, 'rb') as f:
                    data = f.read()
                os.unlink(temp_file.name)
            return data
        except NoCredentialsError:
            logging.error("Credentials not available")
            return False
        except ClientError as e:
            logging.error(e)
            return False
    
    def get_object(self, key):
        """
        Get an object from S3

        Args:
        key: str - key of the object in the S3 bucket
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read()
            return content
        except NoCredentialsError:
            logging.error("Credentials not available")
            return False
        except ClientError as e:
            logging.error(e)
            return False