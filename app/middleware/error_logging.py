import logging
from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("webapp")

async def unhandled_exception_handler(request: Request, exc: Exception):
    # 任何未處理例外都會進來這裡：記 ERROR + 堆疊
    log.error("UNHANDLED %s %s - %s", request.method, request.url.path, repr(exc), exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})