from sqlalchemy import Column, Integer, String, DateTime, func, UniqueConstraint
from sqlalchemy.orm import validates
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timezone

from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    email = Column(String(320), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    account_created = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    account_updated = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # unique email
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    # check email format -> @domain.com
    @validates("email")
    def _validate_email(self, key, address):
        try:
            # email format
            valid = validate_email(address, check_deliverability=False).email

            # end with .com or .edu
            lower_email = valid.lower()
            if not (lower_email.endswith(".com") or lower_email.endswith(".edu")):
                raise ValueError("Email domain must end with .com or .edu")

            return valid
        except EmailNotValidError as e:
            raise ValueError(str(e))
