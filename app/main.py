from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
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
import logging, os
from app.core.logging_config import configure_logging
from app.middleware.error_logging import unhandled_exception_handler
# from app.routers.health import router as health_router
from statsd import StatsClient
from time import perf_counter
import logging
stats = StatsClient(host="127.0.0.1", port=8125, prefix="api")

# configure_logging()  # 讓所有 logger 都用 JSON 格式dk
# LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# logging.getLogger().setLevel(LOG_LEVEL)
log = logging.getLogger("webapp")

app = FastAPI()

# app.include_router(health_router)
app.add_exception_handler(Exception, unhandled_exception_handler)

@app.on_event("startup")
def auto_migrate():
    cfg = alembicConfig("alembic.ini")   # get alembic.ini
    command.upgrade(cfg, "head")   # auto run: alembic upgrade head
    # logger.info("app started")
    log.info("Application started and database migrated successfully")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 既有的 INFO/ERROR logging 保留
    key = f"{request.method}_{request.url.path.strip('/').replace('/', '_') or 'root'}"
    stats.incr(f"{key}.count")                         # 新增：API 次數

    t0 = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        stats.timing(f"{key}.duration_ms", int((perf_counter()-t0)*1000))  # 新增：即便錯也記耗時
        raise
    stats.timing(f"{key}.duration_ms", int((perf_counter()-t0)*1000))      # 新增：API 耗時(ms)
    return response

# make sure that /healthz not be cache
NO_CACHE = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
}

# add routers
app.include_router(user_router)
app.include_router(product_router)

# no 500
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    log.warning("VALUE ERROR on %s %s - %s", request.method, request.url.path, str(exc))
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# Only GET：other methods -> 405, no body
@app.api_route("/healthz", methods=["POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def method_not_allowed():
    log.warning("METHOD NOT ALLOWED on /healthz")
    return Response(status_code=HTTP_405_METHOD_NOT_ALLOWED, headers=NO_CACHE)

@app.get("/healthz")
async def healthz(req: Request):
    # GET: no request body, if there is body -> 400
    body = await req.body()
    if body:
        log.warning("GET /healthz - Request contains body")
        return Response(status_code=HTTP_400_BAD_REQUEST, headers=NO_CACHE)
    
    #  No parameters like /healthz?id=1 -> 400
    if req.query_params:
        log.warning("GET /healthz - Request contains query params: %s", req.query_params)                      
        return Response(status_code=HTTP_400_BAD_REQUEST, headers=NO_CACHE)

    db = SessionLocal()
    try:
        db.add(HealthCheck())   # insert a HealthCheck record
        db.commit()
        log.info("GET /healthz - DB insert success, returning 200")
        return Response(status_code=HTTP_200_OK, headers=NO_CACHE)
    except Exception:
        db.rollback()
        log.error("GET /healthz - DB insert failed: %s", e)
        return Response(status_code=HTTP_503_SERVICE_UNAVAILABLE, headers=NO_CACHE)
    finally:
        db.close()
