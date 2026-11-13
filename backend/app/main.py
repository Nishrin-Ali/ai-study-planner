import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
import app.models  # Ensure all SQLAlchemy models are registered
from app.routers import catalog_router, notes_router, plans_router, papers_router, chat_router
from app.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vtu_planner")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager: handles startup and shutdown."""
    logger.info("Initializing VTU Study Planner database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

    if not settings.has_gemini:
        logger.warning(
            "GEMINI_API_KEY is not set. The backend will operate gracefully using curriculum fallbacks."
        )
    if not settings.has_tavily:
        logger.warning(
            "TAVILY_API_KEY is not set. Web question paper search will operate in offline/mock mode."
        )

    yield

    logger.info("Shutting down VTU Study Planner backend...")


app = FastAPI(
    title="VTU Study Planner & Reminder Assistant API",
    description="Backend API for syllabus catalog, question paper analysis, note ingestion, and AI study plan generation.",
    version="1.0.0",
    lifespan=lifespan,
)

# Attach SlowAPI rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration allowing frontend clients (e.g. Vite on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add defense-in-depth HTTP security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Mount API Routers
app.include_router(catalog_router)
app.include_router(papers_router)
app.include_router(notes_router)
app.include_router(plans_router)
app.include_router(chat_router)


@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint reporting API status and configuration state.
    """
    return {
        "status": "ok",
        "university": "Visvesvaraya Technological University (VTU)",
        "database": "sqlite",
        "gemini_configured": settings.has_gemini,
        "tavily_configured": settings.has_tavily,
        "gemini_model": settings.GEMINI_MODEL,
        "message": (
            "Service operational with full AI capabilities."
            if settings.has_gemini
            else "Service operational in graceful mode (GEMINI_API_KEY not configured)."
        ),
    }
