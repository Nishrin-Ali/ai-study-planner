"""Routers package exports."""
from app.routers.catalog import router as catalog_router
from app.routers.papers import router as papers_router
from app.routers.notes import router as notes_router
from app.routers.plans import router as plans_router
from app.routers.chat import router as chat_router

__all__ = [
    "catalog_router",
    "papers_router",
    "notes_router",
    "plans_router",
    "chat_router",
]
