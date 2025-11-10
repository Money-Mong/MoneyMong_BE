"""
Conversation 및 Message 관련 SQLAlchemy Models
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Conversation(Base):
    """대화 세션"""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("session_type IN ('general', 'report_based')", name="chk_session_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255))  # 대화 제목 (첫 메시지 기반 자동 생성)
    session_type = Column(String(20), default="general")  # 세션 타입 (general, report_based)
    primary_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))  # 주요 참조 문서 (report_based 시)
    is_active = Column(Boolean, default=True, nullable=False)  # 활성 세션 여부

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 최종 수정일

    # 관계
    user = relationship("User", back_populates="conversations")
    primary_document = relationship("Document", foreign_keys=[primary_document_id])
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    history = relationship("ConversationHistory", back_populates="conversation", uselist=False, cascade="all, delete-orphan")


class Message(Base):
    """메시지 내역"""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="chk_role"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(20), nullable=False)  # 메시지 역할 (user, assistant, system)
    content = Column(Text, nullable=False)  # 메시지 내용

    # RAG 컨텍스트 정보
    cited_chunks = Column(ARRAY(UUID(as_uuid=True)), default=list)  # 참조된 청크 ID 리스트
    follow_up_questions = Column(ARRAY(Text), default=list)  # 후속 질문 제안 리스트 (3개)
    reference_context = Column(JSONB, default=dict)  # 후속 질문 생성용 컨텍스트 (응답 + 검색 문서)

    # 메타데이터
    model_version = Column(String(50))  # 사용된 LLM 모델 버전 (assistant만)
    token_usage = Column(JSONB, default=dict)  # 토큰 사용량 {prompt, completion, total}
    latency_ms = Column(Integer)  # 응답 지연 시간 (밀리초)

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일

    # 관계
    conversation = relationship("Conversation", back_populates="messages")


class ConversationHistory(Base):
    """Langchain용 대화 히스토리 (메모리)"""

    __tablename__ = "conversations_history"
    __table_args__ = (
        UniqueConstraint("conversation_id", "session_id", name="uq_conversations_history_session"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)

    session_id = Column(String(255), nullable=False)  # Langchain 세션 ID
    history_data = Column(JSONB, nullable=False, default=dict)  # Langchain 메모리 데이터 (직렬화)

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 최종 수정일

    # 관계
    conversation = relationship("Conversation", back_populates="history")
