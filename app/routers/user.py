from fastapi import APIRouter, Depends, HTTPException, Path, status, Query
from sqlalchemy.orm import Session

from app.core.security import get_db, hash_password, get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserOut
import logging
import boto3
from botocore.exceptions import ClientError
from uuid import uuid4
from datetime import datetime, timedelta
import json

from app.core import config

sns_client = boto3.client("sns", region_name=config.AWS_REGION)

# 建立 logger
log = logging.getLogger("webapp.user")
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

    # 確認有設定 SNS Topic，沒設定就 500
    if not config.USER_SIGNUP_TOPIC_ARN:
        log.error("USER_SIGNUP_TOPIC_ARN is not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup not available",
        )

    # A09：產生驗證 token + 過期時間（例如 2 分鐘）
    verification_token = uuid4().hex
    verification_expiry = datetime.utcnow() + timedelta(minutes=1)

    # 建立 user：is_verified 預設 False，帶入 token + expiry
    user = User(
        email=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=hash_password(payload.password),
        is_verified=False,
        verification_token=verification_token,
        verification_expiry=verification_expiry,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # 準備要丟到 SNS 的訊息（JSON 字串）
    message = {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "token": verification_token,
        "verification_expiry": verification_expiry.isoformat(),
    }

    try:
        sns_client.publish(
            TopicArn=config.USER_SIGNUP_TOPIC_ARN,
            Message=json.dumps(message),
            Subject="User Signup",
        )
        log.info("Published signup message to SNS for user %s", user.email)
    except ClientError as e:
        log.error("Failed to publish signup message to SNS: %s", e)
        # 視作業要求：通常會 rollback 新 user
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

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

@router.get("/verify")
def verify_user(
    email: str = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # 找 user：必須 email + token 同時符合
    user = db.query(User).filter(
        User.email == email,
        User.verification_token == token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token"
        )

    # token 過期 (規定：1 minute)
    if not user.verification_expiry or user.verification_expiry < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token expired"
        )

    # 已驗證過不得再驗證
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already verified"
        )

    # 更新 user：移除 token、設為 verified
    user.is_verified = True
    user.verification_token = None
    user.verification_expiry = None
    user.account_updated = datetime.now(timezone.utc)

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User verified successfully"}