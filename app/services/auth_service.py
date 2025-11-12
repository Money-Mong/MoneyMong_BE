"""
인증 서비스 레이어

Google OAuth와 JWT 토큰 관리를 담당
"""

import logging
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import httpx
import jwt

from app.models.user import User, UserProfile
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AuthService:
    """인증 작업을 위한 서비스"""

    def __init__(self, db: Session):
        self.db = db

    # ============================================
    # Google OAuth Methods
    # ============================================

    def get_google_authorization_url(self) -> str:
        """
        Google OAuth 인증 URL 생성

        FastAPI Docs 테스트 또는 프론트엔드에서 사용
        """
        from urllib.parse import urlencode

        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",  # Refresh token 획득
            "prompt": "consent"  # 항상 동의 화면 표시
        }

        return f"{base_url}?{urlencode(params)}"

    async def google_oauth_callback(self, code: str, redirect_uri: Optional[str] = None) -> Dict:
        """
        Google OAuth 코드를 사용자 정보로 교환하고 JWT 발급

        Args:
            code: Google OAuth authorization code
            redirect_uri: OAuth redirect URI (optional)

        Returns:
            {
                "access_token": "JWT access token",
                "refresh_token": "JWT refresh token (optional)",
                "user": {user_data}
            }

        Raises:
            ValueError: 사용자 친화적 에러 메시지와 함께 (내부 에러는 로그에만 기록)
        """
        try:
            # 1. Code로 Google Access Token 교환
            google_token = await self._exchange_code_for_token(code, redirect_uri)

            # 2. Google User Info 조회
            user_info = await self._get_google_user_info(google_token)

            # 3. 사용자 생성/조회
            user = self.get_or_create_user(
                oauth_provider="google",
                oauth_id=user_info["id"],
                email=user_info["email"],
                name=user_info.get("name", user_info["email"]),
                profile_image_url=user_info.get("picture")
            )

            # 4. 마지막 로그인 시간 업데이트
            self.update_last_login(str(user.id))

            # 5. JWT 생성
            access_token = self.create_access_token(str(user.id))
            refresh_token = self.create_refresh_token(str(user.id))

            logger.info(f"OAuth login successful for user: {user.email}")

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "profile_image_url": user.profile_image_url,
                    "oauth_provider": user.oauth_provider
                }
            }
        except ValueError as e:
            # ValueError는 이미 사용자 친화적 메시지 (Google OAuth 에러)
            logger.error(f"OAuth callback failed: {str(e)}")
            raise
        except Exception as e:
            # 예상치 못한 에러: 상세 로그 기록, 안전한 메시지 반환
            logger.error(f"Unexpected error in OAuth callback: {str(e)}", exc_info=True)
            raise ValueError("Authentication failed. Please try again later.")

    async def _exchange_code_for_token(self, code: str, redirect_uri: Optional[str]) -> str:
        """
        Authorization code를 Google Access Token으로 교환

        Args:
            code: Google OAuth authorization code
            redirect_uri: OAuth redirect URI

        Returns:
            Google access token

        Raises:
            ValueError: 토큰 교환 실패 시
        """
        from urllib.parse import unquote

        # URL 인코딩된 code를 디코딩 (예: %2F -> /)
        decoded_code = unquote(code)

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": decoded_code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri or settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                # 상세 에러는 로그에만 기록
                logger.error(f"Google token exchange failed: {response.status_code} - {response.text}")
                # 클라이언트에는 안전한 메시지만 전달
                raise ValueError("Failed to authenticate with Google. Please try again.")

            token_data = response.json()
            return token_data["access_token"]

    async def _get_google_user_info(self, access_token: str) -> Dict:
        """
        Google Access Token으로 사용자 정보 조회

        Args:
            access_token: Google access token

        Returns:
            {
                "id": "google_user_id",
                "email": "user@example.com",
                "name": "User Name",
                "picture": "https://..."
            }

        Raises:
            ValueError: 사용자 정보 조회 실패 시
        """
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(userinfo_url, headers=headers)

            if response.status_code != 200:
                # 상세 에러는 로그에만 기록
                logger.error(f"Google user info fetch failed: {response.status_code} - {response.text}")
                # 클라이언트에는 안전한 메시지만 전달
                raise ValueError("Failed to retrieve user information from Google.")

            return response.json()

    # ============================================
    # JWT Token Methods
    # ============================================

    def create_access_token(self, user_id: str) -> str:
        """
        JWT 액세스 토큰 생성

        Args:
            user_id: 사용자 ID

        Returns:
            JWT access token (유효기간: 15분)
        """
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        }
        encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, user_id: str) -> str:
        """
        JWT 리프레시 토큰 생성

        Args:
            user_id: 사용자 ID

        Returns:
            JWT refresh token (유효기간: 7일)
        """
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        }
        encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    def verify_access_token(self, token: str) -> Optional[str]:
        """
        JWT 토큰 검증 및 user_id 반환

        Args:
            token: JWT access token

        Returns:
            user_id 또는 None (검증 실패 시)
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")

            # Token type 확인
            if user_id is None or token_type != "access":
                return None

            return user_id
        except jwt.InvalidTokenError:
            # 토큰이 만료되었거나 유효하지 않음
            return None

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Refresh 토큰으로 새로운 Access 토큰 발급

        Args:
            refresh_token: JWT refresh token

        Returns:
            새로운 JWT access token

        Raises:
            ValueError: Refresh 토큰이 유효하지 않거나 사용자가 비활성화된 경우
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")

            # Token type 확인
            if user_id is None or token_type != "refresh":
                raise ValueError("Invalid refresh token type")

            # 사용자 존재 및 활성화 확인
            user = self.get_user_by_id(user_id)
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")

            # 새로운 Access 토큰 생성
            return self.create_access_token(user_id)

        except jwt.InvalidTokenError:
            raise ValueError("Invalid or expired refresh token")

    # ============================================
    # User Management Methods
    # ============================================

    def get_or_create_user(
        self,
        oauth_provider: str,
        oauth_id: str,
        email: str,
        name: str,
        profile_image_url: Optional[str] = None
    ) -> User:
        """
        기존 사용자 조회 또는 새 사용자 생성

        Google OAuth는 회원가입/로그인이 통합되어 있어 하나의 메서드로 처리

        Args:
            oauth_provider: OAuth 제공자 (google)
            oauth_id: OAuth 제공자의 사용자 ID
            email: 이메일
            name: 사용자 이름
            profile_image_url: 프로필 이미지 URL (optional)

        Returns:
            User 객체
        """
        # 1. OAuth provider + OAuth ID로 기존 사용자 조회
        user = self.db.query(User).filter(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id
        ).first()

        if user:
            # 2. 기존 사용자: 정보 업데이트 (이름, 프로필 이미지)
            user.username = name
            user.profile_image_url = profile_image_url
            user.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(user)
            return user

        # 3. 신규 사용자 생성
        new_user = User(
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            email=email,
            username=name,
            profile_image_url=profile_image_url,
            is_active=True
        )
        self.db.add(new_user)
        self.db.flush()  # user.id 생성을 위해 flush

        # 4. UserProfile도 함께 생성
        new_profile = UserProfile(
            user_id=new_user.id,
            finance_level="beginner",  # 기본값
            interests=[]  # 빈 배열
        )
        self.db.add(new_profile)
        self.db.commit()
        self.db.refresh(new_user)

        return new_user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """ID로 사용자 조회"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        return self.db.query(User).filter(User.email == email).first()

    def update_last_login(self, user_id: str) -> None:
        """
        마지막 로그인 시간 업데이트

        Args:
            user_id: 사용자 ID
        """
        user = self.get_user_by_id(user_id)
        if user:
            user.last_login_at = datetime.now()
            self.db.commit()

    def deactivate_user(self, user_id: str) -> bool:
        """
        사용자 비활성화 (회원 탈퇴)

        Args:
            user_id: 사용자 ID

        Returns:
            성공 여부

        Raises:
            ValueError: 사용자를 찾을 수 없는 경우
        """
        # 1. 사용자 조회
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # 2. is_active = False 설정
        user.is_active = False
        user.updated_at = datetime.now()
        self.db.commit()
        return True
