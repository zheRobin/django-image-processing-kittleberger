from django.core.files.storage import default_storage
from rest_framework import status
import boto3
from botocore.config import Config
from botocore.exceptions import NoCredentialsError
from rest_framework.response import Response
import environ
env = environ.Env()
environ.Env.read_env()
def success(data):
    response = {
        "data": data,
        "status" : "success",
        "code": status.HTTP_200_OK
    }
    return response

def created(self, data):
    response = {
        "data": data,
        "status": "success",
        "code": status.HTTP_201_CREATED
    }
    return response

def updated(self, data):
    response = {
        "data": data,
        "status": "success",
        "code": status.HTTP_200_OK
    }
    return response

def deleted(self):
    response = {
        "data": {},
        "status": "success",
        "code": status.HTTP_204_NO_CONTENT
    }
    return response

def error(data):
    response = {
        "data": data,
        "status": "failed",
        "code"   : status.HTTP_400_BAD_REQUEST
    }
    return response

def unauthorized(self):
    response = {
        "data": {"error": "Unauthorized access"},
        "status": "failed",
        "code": status.HTTP_401_UNAUTHORIZED
    }
    return response

def forbidden(self, message="Forbidden"):
    response = {
        "data": {"error": message},
        "status": "failed",
        "code": status.HTTP_403_FORBIDDEN
    }
    return response

def not_found(self, message="Resource Not Found"):
    response = {
        "data": {"error": message},
        "status": "failed",
        "code": status.HTTP_404_NOT_FOUND
    }
    return response
def server_error( message="Unkown Error"):
    response = {
        "data": {"error": message},
        "status": "failed",
        "code": status.HTTP_501_NOT_IMPLEMENTED
    }
    return response
def get_s3_config():
    session = boto3.Session(
        aws_access_key_id=env('S3_ACCESS_KEY_ID'),
        aws_secret_access_key=env('S3_SECRET_ACCESS_KEY'),
        region_name=env('S3_REGION_NAME')
    )
    s3_client = session.client('s3')
    return s3_client

def s3_upload(file, path):
    s3_client, s3_bucket, s3_endpoint = get_s3_config(), env('S3_BUCKET_NAME'), env('S3_ENDPOINT_URL')
    try:
        s3_client.upload_fileobj(file, s3_bucket, path, ExtraArgs={'ACL':'public-read'})
    except NoCredentialsError:
        return Response(error("No AWS credentials found"))
    return s3_endpoint + path
def handle_uploaded_file(f):
    default_storage.save( f.name, f)