# app/schemas/image.py
from pydantic import BaseModel
from datetime import datetime

class ImageOut(BaseModel):
    image_id: int
    product_id: int
    file_name: str
    date_created: datetime
    s3_bucket_path: str

    class Config:
        from_attributes = True  # (pydantic v2)
