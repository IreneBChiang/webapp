from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.db.session import SessionLocal
from app.models.user import User

# Authorization: Basic header
security = HTTPBasic()
# bcrypt always uses salt, automatically generates a random salt
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# get the session, yield would automatically finally when finish
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# raw password -> bcrypt
def hash_password(raw: str) -> str:
    return pwd_ctx.hash(raw)

# check raw password is correct or not
def verify_password(raw: str, hashed: str) -> bool:
    return pwd_ctx.verify(raw, hashed)

# check username and password
def get_current_user(
    # HTTP Basic, credentials.username credentials.password
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.email == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        # return 401 and WWW-Authenticate: Basic
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user
