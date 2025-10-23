from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, func, CheckConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class Product(Base):
    __tablename__ = "products"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(2000), nullable=True)
    sku = Column(String(100), nullable=False)
    manufacturer = Column(String(200), nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    date_added = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    date_last_updated = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Product can use .owner to get User
    owner = relationship("User")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_products_quantity_nonneg"),
        CheckConstraint("quantity <= 100", name="ck_products_quantity_max"),
    )
