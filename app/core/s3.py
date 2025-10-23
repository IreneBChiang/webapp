import uuid
import boto3

s3 = boto3.client("s3")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

def make_key(product_id: int, filename: str) -> str:
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    return f"{product_id}/{uuid.uuid4().hex}{ext}"

def put_bytes(bucket: str, key: str, data: bytes, content_type: str) -> str:
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )
    return key  # 只存 key（不是 s3://...）

def delete_object(bucket: str, key: str) -> None:
    s3.delete_object(Bucket=bucket, Key=key)
