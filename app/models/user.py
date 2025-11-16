"""
User 및 UserProfile SQLAlchemy Models
"""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """사용자 기본 정보 및 OAuth 인증"""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_id", name="uq_users_oauth"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oauth_provider = Column(
        String(50), nullable=False
    )  # OAuth 제공자 (google, naver, kakao)
    oauth_id = Column(String(255), nullable=False)  # OAuth 제공자의 사용자 ID
    email = Column(String(255), unique=True, nullable=False, index=True)  # 이메일 주소
    username = Column(String(100), nullable=False)  # 사용자 이름
    profile_image_url = Column(String)  # 프로필 이미지 URL
    is_active = Column(Boolean, default=True, nullable=False)  # 계정 활성화 여부
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # 계정 생성일
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 최종 수정일
    last_login_at = Column(DateTime(timezone=True))  # 마지막 로그인 시간

    # 관계
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    conversations = relationship("Conversation", back_populates="user")


class UserProfile(Base):
    """사용자 프로필 및 학습 수준 정보"""

    __tablename__ = "user_profile"
    __table_args__ = (
        CheckConstraint(
            "finance_level IN ('beginner', 'intermediate', 'advanced')",
            name="chk_finance_level",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # 금융 지식 수준 (beginner: 해설 모드, intermediate: 요약 모드, advanced: 심화 모드)
    finance_level = Column(String(20), default="beginner")
    interests = Column(
        ARRAY(String), default=list
    )  # 관심 분야 태그 배열 (산업, 섹터 등)

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 최종 수정일

    # 관계
    user = relationship("User", back_populates="profile")
