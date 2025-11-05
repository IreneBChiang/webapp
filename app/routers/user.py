from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.security import get_db, hash_password, get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserOut
import logging

# 建立 logger
log = logging.getLogger("user")
router = APIRouter(prefix="/v1/user", tags=["user"])

# create data
@router.post("", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    log.info("POST /v1/user - creating user: %s", payload.username)
    # Ignore any account_created/account_updated values
    exists = db.query(User).filter(User.email == payload.username).first()
    if exists:
        log.warning("POST /v1/user - user already exists: %s", payload.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    user = User(
        email=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log.info("POST /v1/user - user created: id=%s email=%s", user.id, user.email)
    return UserOut(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.email,
        account_created=user.account_created,
        account_updated=user.account_updated,
    )

# get data
@router.get("/{userId}", response_model=UserOut)
def get_me(
    userId: int = Path(..., ge=1),
    # go to check username and password
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log.info("GET /v1/user/%s - authenticated user: %s", userId, me.email)
    if me.id != userId:
        log.warning("GET /v1/user/%s - forbidden for user: %s", userId, me.email)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.refresh(me)
    log.info("GET /v1/user/%s - success", userId)
    return UserOut(
        id=me.id,
        first_name=me.first_name,
        last_name=me.last_name,
        username=me.email,
        account_created=me.account_created,
        account_updated=me.account_updated,
    )

# update data
@router.put("/{userId}", status_code=status.HTTP_204_NO_CONTENT)
def update_me(
    payload: dict,
    userId: int = Path(..., ge=1),
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log.info("PUT /v1/user/%s - request payload keys: %s", userId, list(payload.keys()))
    if me.id != userId:
        log.warning("PUT /v1/user/%s - forbidden for user: %s", userId, me.email)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    allowed = {"first_name", "last_name", "password"}
    extra = set(payload.keys()) - allowed
    if extra:
        # only first_name last_name password can be updated, others -> 400
        log.warning("PUT /v1/user/%s - invalid fields: %s", userId, ", ".join(sorted(extra)))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fields not allowed: {', '.join(sorted(extra))}",
        )

    if "first_name" in payload:
        me.first_name = payload["first_name"]
    if "last_name" in payload:
        me.last_name = payload["last_name"]
    if "password" in payload:
        me.password_hash = hash_password(payload["password"])

    db.add(me)
    db.commit()
    log.info("PUT /v1/user/%s - update success", userId)
    return
