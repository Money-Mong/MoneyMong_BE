"""
인증 서비스 레이어

TODO: 인증 로직 구현 필요:
1. Google OAuth 토큰 교환
2. JWT 토큰 생성 및 검증
3. 사용자 생성 및 조회
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import httpx

from app.models.user import User, UserProfile
from app.config import get_settings

settings = get_settings()


class AuthService:
    """인증 작업을 위한 서비스"""

    def __init__(self, db: Session):
        self.db = db

    async def google_oauth_callback(self, code: str, redirect_uri: str) -> dict:
        """
        Google OAuth 코드를 사용자 정보로 교환하고 사용자 생성/업데이트
        FE랑 연동 방식을 고민중
        """
        # TODO: OAuth 플로우 구현
        raise NotImplementedError("TODO: Google OAuth 콜백 구현 필요")

    def create_access_token(self, user_id: str) -> str:
        """
        JWT 액세스 토큰 생성
        """
        # TODO: JWT 토큰 생성 구현
        raise NotImplementedError("TODO: JWT 토큰 생성 구현 필요")

    def verify_access_token(self, token: str) -> Optional[str]:
        """
        JWT 토큰 검증 및 user_id 반환
        """
        # TODO: JWT 토큰 검증 구현
        raise NotImplementedError("TODO: JWT 토큰 검증 구현 필요")

    def get_or_create_user(self, oauth_provider: str, oauth_id: str, email: str, name: str, profile_image_url: str = None) -> User:
        """
        기존 사용자 조회 또는 새 사용자 생성
        조회랑 생성이랑 분리하는게 맞지만, google이 회원가입 로그인 통합되어있으니 일단 통합
        """
        # TODO: 사용자 생성/조회 구현
        raise NotImplementedError("TODO: get_or_create_user 구현 필요")

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """ID로 사용자 조회"""
        return self.db.query(User).filter(User.id == user_id).first()
