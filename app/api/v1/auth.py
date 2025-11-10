"""
인증용 Auth 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/google/callback")
async def google_auth_callback(
    auth_data,
    db: Session = Depends(get_db)
):
    """
    Google OAuth 콜백 엔드포인트
    """
    auth_service = AuthService(db)

    # TODO: Google OAuth 플로우 구현
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TODO: Google OAuth 인증 구현 필요"
    )


@router.get("/me")
async def get_current_user(
    db: Session = Depends(get_db),
    # TODO: JWT 토큰 검증을 위한 의존성 추가
    # current_user: User = Depends(get_current_user_from_token)
):
    """
    현재 인증된 사용자 정보 조회
    """
    # TODO: 현재 사용자 조회 구현
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TODO: JWT 인증 구현 필요"
    )
