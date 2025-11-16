"""
API v1 Routes
"""

from fastapi import APIRouter
from app.api.v1 import auth
from app.api.v1 import rag
from app.api.v1 import auth, documents, conversations

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
