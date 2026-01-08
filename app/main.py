import json
import logging
import sys
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from .endpoints.public import router as public_router
from .endpoints.admin import router as admin_router
from .endpoints.balance import router as balance_router
from .endpoints.order import router as order_router
from .endpoints.reports import router as reports_router


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in log:
                continue
            if key in (
                "args", "msg", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text",
                "stack_info", "lineno", "funcName", "created",
                "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "name"
            ):
                continue
            log[key] = value

        return json.dumps(log, ensure_ascii=False)


logging.getLogger("uvicorn.access").disabled = True
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())

root_logger.handlers.clear()
root_logger.addHandler(handler)


app = FastAPI(debug=True)


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = int((time.time() - start_time) * 1000)

        status_code = response.status_code if response else 500
        level = logging.INFO
        if 400 <= status_code < 500:
            level = logging.WARNING
        elif status_code >= 500:
            level = logging.ERROR

        root_logger.log(
            level,
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
            },
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    level = logging.WARNING if exc.status_code < 500 else logging.ERROR

    root_logger.log(
        level,
        "http_exception",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": exc.status_code,
            "detail": exc.detail,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    root_logger.error(
        "unhandled_exception",
        extra={
            "method": request.method,
            "path": request.url.path,
            "error": str(exc),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(order_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1/public")
app.include_router(admin_router, prefix="/api/v1/admin")
app.include_router(balance_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "API работает!"}
