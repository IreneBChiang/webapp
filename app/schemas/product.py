from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# shared rules -> inherited by create/update
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    sku: str = Field(..., min_length=1, max_length=100)
    manufacturer: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., ge=0, le=100)  # between 0–100

# for post /product
class ProductCreate(ProductBase):
    pass

# for patch -> optional
class ProductUpdate(ProductBase):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=200)
    quantity: Optional[int] = Field(None, ge=0, le=100)

class ProductOut(ProductBase):
    id: int
    date_added: datetime
    date_last_updated: datetime
    owner_user_id: int

    class Config:
        from_attributes = True
