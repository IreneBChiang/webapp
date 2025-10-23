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

router = APIRouter(prefix="/v1/product", tags=["product"])

# check exists, check owner
def _owner_guard(p: Product | None, me: User):
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if p.owner_user_id != me.id:
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
    p = Product(**payload.model_dump(), owner_user_id=me.id)
    db.add(p)
    db.commit()
    # get the product(from db)
    db.refresh(p)
    return p

# get product
# no need to log in
@router.get("/{productId}", response_model=ProductOut)
# ... = required
def get_product(productId: int = Path(..., ge=1), db: Session = Depends(get_db)):
    p = db.get(Product, productId)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return p

# update product
@router.put("/{productId}", status_code=status.HTTP_204_NO_CONTENT)
def put_product(
    payload: ProductCreate,                # PUT = all fields
    productId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Validation failed")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# update part of product
@router.patch("/{productId}", status_code=status.HTTP_204_NO_CONTENT)
def patch_product(
    payload: ProductUpdate,                # PATCH = schema -> all Optional
    productId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Product, productId)
    _owner_guard(p, me)

    changes = payload.model_dump(exclude_unset=True)  # only exist fields
    for k, v in changes.items():
        setattr(p, k, v)

    try:
        db.commit()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Validation failed")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# delete product
@router.delete("/{productId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    productId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Product, productId)
    # check exist and owner
    _owner_guard(p, me)
    db.delete(p)
    db.commit()
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
    p = db.get(Product, productId)
    _owner_guard(p, me)

    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Storage not configured")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    key = make_key(productId, file.filename)
    # boto3 是同步；用 threadpool 包起來避免阻塞
    s3_key = await run_in_threadpool(put_bytes, S3_BUCKET_NAME, key, data, file.content_type)

    img = Image(product_id=productId, file_name=file.filename, s3_bucket_path=s3_key)
    db.add(img)
    db.commit()
    db.refresh(img)
    return img

# 取得某 product 的所有圖片
@router.get("/{productId}/image", response_model=list[ImageOut])
def list_images(
    productId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Product, productId)
    _owner_guard(p, me)

    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Storage not configured")

    return db.query(Image).filter(Image.product_id == productId).order_by(Image.image_id).all()

# 取得單一圖片
@router.get("/{productId}/image/{imageId}", response_model=ImageOut)
def get_image(
    productId: int = Path(..., ge=1),
    imageId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Product, productId)
    _owner_guard(p, me)

    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Storage not configured")

    img = db.query(Image).filter(Image.product_id == productId, Image.image_id == imageId).first()
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return img

# 刪除圖片（S3 + DB）
@router.delete("/{productId}/image/{imageId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    productId: int = Path(..., ge=1),
    imageId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Product, productId)
    _owner_guard(p, me)

    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Storage not configured")

    img = (
        db.query(Image)
        .filter(Image.product_id == productId, Image.image_id == imageId)
        .first()
    )
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # s3_bucket_path 存的就是 key（例如 "3/uuid.jpg"）
    try:
        delete_object(S3_BUCKET_NAME, img.s3_bucket_path)
    finally:
        db.delete(img)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)