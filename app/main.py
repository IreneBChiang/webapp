from fastapi import FastAPI, Request, Response
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_503_SERVICE_UNAVAILABLE,
)
from app.db.session import SessionLocal, Base, engine
from app.models.health_check import HealthCheck
from alembic import command
from alembic.config import Config as alembicConfig

from app.models.user import User
from app.models.product import Product
from app.routers.user import router as user_router
from app.routers.product import router as product_router

app = FastAPI()

@app.on_event("startup")
def auto_migrate():
    cfg = alembicConfig("alembic.ini")   # get alembic.ini
    command.upgrade(cfg, "head")   # auto run: alembic upgrade head

# make sure that /healthz not be cache
NO_CACHE = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
}

# add routers
app.include_router(user_router)
app.include_router(product_router)

# Only GET：other methods -> 405, no body
@app.api_route("/healthz", methods=["POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def method_not_allowed():
    return Response(status_code=HTTP_405_METHOD_NOT_ALLOWED, headers=NO_CACHE)

@app.get("/healthz")
async def healthz(req: Request):
    # GET: no request body, if there is body -> 400
    body = await req.body()
    if body:
        return Response(status_code=HTTP_400_BAD_REQUEST, headers=NO_CACHE)
    
    #  No parameters like /healthz?id=1 -> 400
    if req.query_params:                      
        return Response(status_code=HTTP_400_BAD_REQUEST, headers=NO_CACHE)

    db = SessionLocal()
    try:
        db.add(HealthCheck())   # insert a HealthCheck record
        db.commit()
        return Response(status_code=HTTP_200_OK, headers=NO_CACHE)
    except Exception:
        db.rollback()
        return Response(status_code=HTTP_503_SERVICE_UNAVAILABLE, headers=NO_CACHE)
    finally:
        db.close()
