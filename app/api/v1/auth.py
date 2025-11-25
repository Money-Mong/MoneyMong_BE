"""
인증용 Auth 엔드포인트

OAuth 플로우:
1. 프론트엔드: Google OAuth 인증 시작 → Authorization Code 획득
2. 프론트엔드: POST /auth/google/callback {code, redirect_uri}
3. 백엔드: Code로 Google에 Access Token 요청 → 사용자 정보 획득
4. 백엔드: 사용자 생성/조회 → JWT 토큰 생성 및 반환

FastAPI Docs 테스트:
- /auth/google/login 접속 → Google 인증 → code 획득
- /auth/google/callback에 code 입력하여 JWT 획득
"""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService


router = APIRouter()

# Security Scheme 정의 (Swagger UI의 "Authorize" 버튼 활성화)
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="JWT Access Token을 입력하세요 (Bearer 접두사 불필요)",
)


# ============================================
# Dependencies
# ============================================


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    AuthService 의존성 주입

    각 엔드포인트에서 AuthService를 사용할 때 자동으로 주입됨
    """
    return AuthService(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    JWT 토큰에서 현재 사용자 추출

    Swagger UI에서는 "Authorize" 버튼 클릭 후 토큰 입력
    """
    token = credentials.credentials

    # JWT 토큰 검증
    user_id = auth_service.verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


# ============================================
# OAuth Endpoints
# ============================================


@router.get("/google/login")
async def google_login(auth_service: AuthService = Depends(get_auth_service)):
    """
    Google OAuth 로그인 시작

    FastAPI Docs에서 테스트용:
    1. 이 엔드포인트 호출 → Google 로그인 페이지로 리다이렉트
    2. Google 인증 완료 후 URL에서 'code' 파라미터 복사
    3. /auth/google/callback 엔드포인트에 code 입력

    프론트엔드:
    - 이 URL을 사용하여 Google OAuth 시작
    - redirect_uri는 프론트엔드의 콜백 페이지
    """
    authorization_url = auth_service.get_google_authorization_url()

    return RedirectResponse(url=authorization_url)


@router.post("/google/callback")
async def google_auth_callback(
    code: str = Body(..., description="Google OAuth authorization code"),
    redirect_uri: str = Body(None, description="OAuth redirect URI (optional)"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Google OAuth 콜백 엔드포인트

    프론트엔드가 Google에서 받은 authorization code를 백엔드로 전송
    백엔드는 이 code로 Google Access Token을 교환하고 JWT를 발급

    Request Body:
    {
        "code": "4/0AeanUIaE...",  # Google OAuth code (required)
        "redirect_uri": "http://localhost:3000/auth/callback"  # optional
    }

    Response:
    {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",  # optional
        "token_type": "bearer",
        "user": {
            "id": "...",
            "email": "user@example.com",
            "username": "user",
            ...
        }
    }
    """
    try:
        result = await auth_service.google_oauth_callback(code, redirect_uri)

        return {
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token"),
            "token_type": "bearer",
            "user": result["user"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}",
        )


# ============================================
# User Endpoints
# ============================================


@router.get("/me")
async def get_my_info(current_user: User = Depends(get_current_user)):
    """
    현재 인증된 사용자 정보 조회

    Headers:
    Authorization: Bearer <access_token>
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "profile_image_url": current_user.profile_image_url,
        "oauth_provider": current_user.oauth_provider,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at,
    }


# ============================================
# Token Management
# ============================================


@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh 토큰으로 새로운 Access 토큰 발급

    Request Body:
    {
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }

    Response:
    {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer"
    }
    """
    try:
        new_access_token = auth_service.refresh_access_token(refresh_token)
        return {"access_token": new_access_token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    로그아웃

    클라이언트에서 토큰 삭제 필요
    선택적으로 서버에서 토큰 블랙리스트 처리 가능

    Headers:
    Authorization: Bearer <access_token>
    """
    # TODO: 프론트 만들고 나서 하기, 1차적으론 프론트 레벨에서 대응 가능함
    return {"message": "Logout successful"}


# ============================================
# Account Management
# ============================================


@router.delete("/withdraw")
async def withdraw_account(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    회원 탈퇴 (계정 비활성화)

    계정을 비활성화하고 관련 데이터를 처리

    Headers:
    Authorization: Bearer <access_token>
    """
    try:
        auth_service.deactivate_user(str(current_user.id))
        return {"message": "Account deactivated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
