import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.seed import seed_data
from app.db.session import SessionLocal, engine, get_db
from app.schemas.schemas import HealthOut, ReadinessOut

configure_logging()
logger = logging.getLogger("centralops.startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema creation belongs to Alembic. Startup only seeds an already-migrated database.
    try:
        with SessionLocal() as db:
            seed_data(db)
    except SQLAlchemyError:
        logger.warning("database_not_migrated; run alembic upgrade head before serving traffic")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-assisted employee service request triage, human approval workflows, "
        "grounded policy assistance, operational analytics, and automation monitoring."
    ),
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }


@app.get("/health", response_model=HealthOut, tags=["Operations"])
def health() -> HealthOut:
    database_status = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    return HealthOut(
        status="ok" if database_status == "ok" else "degraded",
        database=database_status,
        llm_provider=settings.llm_provider,
        version=settings.app_version,
    )


@app.get("/ready", response_model=ReadinessOut, tags=["Operations"])
def ready(db: Session = Depends(get_db)) -> ReadinessOut:
    try:
        db.execute(text("SELECT 1 FROM users LIMIT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        ) from exc
    return ReadinessOut(status="ready", database="ok", version=settings.app_version)
