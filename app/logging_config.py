"""
로깅 설정

개발/프로덕션 환경에 따라 로그 레벨과 형식을 관리
"""

import logging
import sys

from app.config import get_settings


settings = get_settings()


def setup_logging():
    """로깅 설정 초기화"""

    # 로그 레벨 설정
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # 로그 포맷 설정
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 기본 로깅 설정
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            # 콘솔 출력
            logging.StreamHandler(sys.stdout),
        ],
    )

    # 민감한 정보를 포함하는 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # 개발 환경에서만 SQLAlchemy 쿼리 로그 출력
    if settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, debug={settings.DEBUG}")
