"""
API v1 Routes
"""

from fastapi import APIRouter
from app.api.v1 import auth, crawler

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(crawler.router, prefix="/crawler", tags=["crawler"])
