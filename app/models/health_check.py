from sqlalchemy import BigInteger, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class HealthCheck(Base):
    __tablename__ = "health_checks"

    check_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    check_datetime: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),  # timezone-aware
        nullable=False,
        server_default=func.utc_timestamp()  # use UTC timezone
    )

# use index to faster searching speed
Index("idx_check_datetime", HealthCheck.check_datetime)
