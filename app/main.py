import logging
import time

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.logging_conf import configure_logging, new_request_id, request_id_ctx
from app.routers import actions, vehicles

configure_logging()
logger = logging.getLogger("inventory.app")

app = FastAPI(
    title="Intelligent Inventory Dashboard API",
    description=(
        "REST API for dealership vehicle inventory management: filterable inventory listing, "
        "aging stock (>90 days) identification, and per-vehicle action logging."
    ),
    version="1.0.0",
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", new_request_id())
    token = request_id_ctx.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path, "method": request.method},
        )
        raise
    finally:
        request_id_ctx.reset(token)

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(vehicles.router)
app.include_router(actions.router)


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "environment": settings.environment}
