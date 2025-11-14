"""
어플리케이션 레벨 설정
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """프로젝트 셋팅"""

    # 프로젝트
    APP_NAME: str = "MoneyMong API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # 데이터베이스
    DATABASE_URL: str

    # 구글 인증
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # JWT 키
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 시간
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7일

    # OpenAI
    OPENAI_API_KEY: str

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # React 프론트엔드
        "http://localhost:8000"   # FastAPI Docs 테스트용
    ]
    
    # LangChain
    LANGCHAIN_TRACING_V2: str = "false"  # 기본값 설정 가능
    LANGCHAIN_API_KEY: str | None = None # 선택적 필드로 설정 가능
    LANGCHAIN_PROJECT: str = "default"
    
    # DB
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432 # 타입 힌트와 기본값 활용
    
    # API
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    RELOAD: bool = True

    # AWS
    AWS_AAWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "ap-northeast-2"
    AWS_S3_BUCKET: str = "moneymong-resources-bucket"


    class Config:
        env_file = ".env"
        case_sensitive = True # 대소문자 주의


@lru_cache()
def get_settings() -> Settings:
    """캐시된 내용이 있다면 리턴해서 싱글톤 방식 처리"""
    return Settings()
