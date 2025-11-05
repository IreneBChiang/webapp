from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.security import get_db, get_current_user
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut

from fastapi import UploadFile, File
from app.core.config import S3_BUCKET_NAME
from app.core.s3 import ALLOWED_CONTENT_TYPES, make_key, put_bytes, delete_object
from app.models.image import Image
from app.schemas.image import ImageOut
from starlette.concurrency import run_in_threadpool
from app.core.config import S3_BUCKET_NAME
from fastapi import HTTPException, status
import logging
from time import perf_counter
from app.main import stats

log = logging.getLogger("product")
router = APIRouter(prefix="/v1/product", tags=["product"])

# check exists, check owner
def _owner_guard(p: Product | None, me: User):
    if p is None:
        log.warning("Product not found for user_id=%s", me.id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if p.owner_user_id != me.id:
        log.warning("Forbidden access product_id=%s by user_id=%s", p.id, me.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

# create product
@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # payload -> request body verify by Pydantic(ProduxtCreate)
    # **payload.model_dump() tranfer to dict to Product ORM(SQLAlchemy)
    # get a Product ORM instance
    log.info("POST /v1/product - create by user_id=%s payload=%s", me.id, payload.model_dump())
    p = Product(**payload.model_dump(), owner_user_id=me.id)
    db.add(p)
    db.commit()
    # get the product(from db)
    db.refresh(p)
    log.info("POST /v1/product - created product_id=%s user_id=%s", p.id, me.id)
    return p

# get product
# no need to log in
@router.get("/{productId}", response_model=ProductOut)
# ... = required
def get_product(productId: int = Path(..., ge=1), db: Session = Depends(get_db)):
    log.info("GET /v1/product/%s", productId)
    p = db.get(Product, productId)
    if not p:
        log.warning("GET /v1/product/%s - not found", productId)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    log.info("GET /v1/product/%s - ok", productId)
    return p

# update product
@router.put("/{productId}", status_code=status.HTTP_204_NO_CONTENT)
def put_product(
    payload: ProductCreate,                # PUT = all fields
    productId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    log.info("PUT /v1/product/%s - user_id=%s payload=%s", productId, me.id, payload.model_dump())
    p = db.get(Product, productId)
    # check owner
    _owner_guard(p, me)

    # payload -> dict; put on p(product in db)
    for k, v in payload.model_dump().items():
        setattr(p, k, v)

    try:
        db.commit()
    except (IntegrityError, OperationalError):
        db.rollback()
        log.error("PUT /v1/product/%s - DB validation error: %s", productId, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Validation failed")
    log.info("PUT /v1/product/%s - success", productId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# update part of product
@router.patch("/{productId}", status_code=status.HTTP_204_NO_CONTENT)
def patch_product(
    payload: ProductUpdate,                # PATCH = schema -> all Optional
    productId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    log.info("PATCH /v1/product/%s - user_id=%s changes=%s", productId, me.id, payload.model_dump(exclude_unset=True))
    p = db.get(Product, productId)
    _owner_guard(p, me)

    changes = payload.model_dump(exclude_unset=True)  # only exist fields
    for k, v in changes.items():
        setattr(p, k, v)

    try:
        db.commit()
    except (IntegrityError, OperationalError):
        db.rollback()
        log.error("PATCH /v1/product/%s - DB validation error: %s", productId, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Validation failed")
    log.info("PATCH /v1/product/%s - success", productId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# delete product
@router.delete("/{productId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    productId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    log.info("DELETE /v1/product/%s - user_id=%s", productId, me.id)
    p = db.get(Product, productId)
    # check exist and owner
    _owner_guard(p, me)
    db.delete(p)
    db.commit()
    log.info("DELETE /v1/product/%s - success", productId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# 上傳圖片
MAX_BYTES = 5 * 1024 * 1024  # 5MB

@router.post("/{productId}/image", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    productId: int = Path(..., ge=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    log.info("POST /v1/product/%s/image - user_id=%s filename=%s content_type=%s",
             productId, me.id, file.filename, file.content_type)
    p = db.get(Product, productId)
    _owner_guard(p, me)

    if not S3_BUCKET_NAME:
        log.error("Storage not configured for image upload")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Storage not configured")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        log.warning("Unsupported file type: %s", file.content_type)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

    data = await file.read()
    if not data:
        log.warning("Empty file upload attempted")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > MAX_BYTES:
        log.warning("File too large: %s bytes (> %s)", len(data), MAX_BYTES)
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    key = make_key(productId, file.filename)
    # boto3 是同步；用 threadpool 包起來避免阻塞
    try:
        t0 = perf_counter()                                         # 開始計時
        s3_key = await run_in_threadpool(put_bytes, S3_BUCKET_NAME, key, data, file.content_type)
        stats.timing("s3.put_bytes.duration_ms", int((perf_counter() - t0) * 1000))  # 新增：上報 S3 耗時(ms)
    except Exception as e:
        stats.timing("s3.put_bytes.duration_ms", int((perf_counter() - t0) * 1000))  # 失敗時也記耗時
        log.error("S3 put_bytes failed: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upload failed")

    img = Image(product_id=productId, file_name=file.filename, s3_bucket_path=s3_key)
    db.add(img)
    db.commit()
    db.refresh(img)
    log.info("Image uploaded product_id=%s image_id=%s key=%s", productId, img.image_id, s3_key)
    return img

# 取得某 product 的所有圖片
@router.get("/{productId}/image", response_model=list[ImageOut])
def list_images(
    productId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    log.info("GET /v1/product/%s/image - list", productId)
    p = db.get(Product, productId)

    if not S3_BUCKET_NAME:
        log.error("Storage not configured for list images")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Storage not configured")

    imgs = (db.query(Image).filter(Image.product_id == productId).order_by(Image.image_id).all())
    log.info("GET /v1/product/%s/image - %d images", productId, len(imgs))
    return imgs

# 取得單一圖片
@router.get("/{productId}/image/{imageId}", response_model=ImageOut)
def get_image(
    productId: int = Path(..., ge=1),
    imageId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    log.info("GET /v1/product/%s/image/%s", productId, imageId)
    p = db.get(Product, productId)

    if not S3_BUCKET_NAME:
        log.error("Storage not configured for get image")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Storage not configured")

    img = db.query(Image).filter(Image.product_id == productId, Image.image_id == imageId).first()
    if not img:
        log.warning("Image not found product_id=%s image_id=%s", productId, imageId)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    log.info("GET /v1/product/%s/image/%s - ok", productId, imageId)
    return img

# 刪除圖片（S3 + DB）
@router.delete("/{productId}/image/{imageId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    productId: int = Path(..., ge=1),
    imageId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    log.info("DELETE /v1/product/%s/image/%s - user_id=%s", productId, imageId, me.id)
    p = db.get(Product, productId)
    _owner_guard(p, me)

    if not S3_BUCKET_NAME:
        log.error("Storage not configured for delete image")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Storage not configured")

    img = (
        db.query(Image)
        .filter(Image.product_id == productId, Image.image_id == imageId)
        .first()
    )
    if not img:
        log.warning("DELETE image not found product_id=%s image_id=%s", productId, imageId)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # s3_bucket_path 存的就是 key（例如 "3/uuid.jpg"）
    try:
        t1 = perf_counter()                                         # 開始計時
        delete_object(S3_BUCKET_NAME, img.s3_bucket_path)
        stats.timing("s3.delete_object.duration_ms", int((perf_counter() - t1) * 1000))  # 新增
    except Exception as e:
        stats.timing("s3.delete_object.duration_ms", int((perf_counter() - t1) * 1000))  # 失敗時也記耗時
        log.error("S3 delete_object failed: %s (key=%s)", e, img.s3_bucket_path)
    finally:
        db.delete(img)
        db.commit()
    log.info("DELETE /v1/product/%s/image/%s - success", productId, imageId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)