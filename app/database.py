"""
Database 관리
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings

settings = get_settings()

# SQLAlchemy 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG, # 디버그 설정 따라가게 선언
)

# 세션 생성용, 전역적으로 하나만 두기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()


def get_db() -> Session:
    """
    의존성 주입용 제너레이터 함수
    FastAPI에서 권장되는 의존성 주입 방식
    요청 단위로 세션 주입용

    사용예제:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db # 비즈니스 로직이 실행되는 동안 세션 유지
    finally:
        db.close()
