from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.security import get_db, get_current_user
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut

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
