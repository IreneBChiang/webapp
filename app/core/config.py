import os
from dotenv import load_dotenv
from pathlib import Path

# load the .env file
load_dotenv(Path("/etc/myapp/.env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env")

# if PORT not set in .env -> default 8080
PORT = int(os.getenv("PORT", "8080"))

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
# if not S3_BUCKET_NAME:
#     raise ValueError("S3_BUCKET_NAME not set — check your .env or Terraform user_data")