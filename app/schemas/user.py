from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

# shared rules -> inherited by create/update
class UserBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    username: EmailStr  # email -> username

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# for output
class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    username: EmailStr
    account_created: datetime
    account_updated: datetime

    class Config:
        from_attributes = True
