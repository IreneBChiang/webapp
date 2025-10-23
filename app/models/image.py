# app/models/image.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class Image(Base):
    __tablename__ = "images"

    image_id       = Column(Integer, primary_key=True, autoincrement=True, index=True)
    product_id     = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name      = Column(String(255), nullable=False)
    date_created   = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    s3_bucket_path = Column(String(1024), nullable=False)

    # optional：需要的話可反向關聯
    product = relationship("Product", backref="images")
