import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app import models  # noqa: F401  (makes sure the tables are registered)
from app.config import get_settings
from app.database import Base, engine
from app.metrics import REQUESTS
from app.routers import auth, health, tickets
from app.services.classifier import get_classifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    get_classifier()  # load the model once at startup
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="Support ticket API that sorts tickets using a small ML model.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def count_requests(request: Request, call_next):
    response = await call_next(request)
    route = request.scope.get("route")
    path = route.path if route else "unmatched"
    REQUESTS.labels(method=request.method, path=path, status=response.status_code).inc()
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tickets.router)
