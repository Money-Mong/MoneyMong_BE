"""
MoneyMong Backend - FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import get_settings
from app.core.memory import close_checkpoint_system, init_checkpoint_system
from app.logging_config import setup_logging


# 로깅 설정 초기화
setup_logging()

settings = get_settings()


# ===================================
# Lifecycle Management
# ===================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    앱 생명주기 관리

    Startup:
        - LangGraph checkpoint 시스템 초기화

    Shutdown:
        - Checkpoint 연결 풀 종료
    """
    # Startup
    await init_checkpoint_system()
    yield
    # Shutdown
    await close_checkpoint_system()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,  # Lifecycle hook 추가
    swagger_ui_parameters={
        "persistAuthorization": True  # 인증 정보 유지
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MoneyMong API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="localhost", port=8000, reload=settings.DEBUG)
