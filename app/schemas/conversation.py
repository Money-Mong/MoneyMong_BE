"""
API 스키마
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ===================================
# Message Schemas
# ===================================


class TokenUsage(BaseModel):
    """토큰 사용량"""

    prompt: int
    completion: int
    total: int


class MessageBase(BaseModel):
    """메시지 기본 정보"""

    id: UUID
    conversation_id: UUID
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    cited_chunks: Optional[List[str]] = None  # 참조된 청크 ID
    follow_up_questions: Optional[List[str]] = None  # 후속 질문 제안 (3개)
    reference_context: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = None
    token_usage: Optional[TokenUsage] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator("token_usage", mode="before")
    @classmethod
    def empty_dict_to_none(cls, v):
        """
        DB에서 오는 빈 JSONB 필드 `{}`를 None으로 변환하여
        선택적(Optional) Pydantic 모델 유효성 검사를 통과시킵니다.
        """
        if v == {}:
            return None
        return v


# ===================================
# Conversation Schemas
# ===================================


class ConversationBase(BaseModel):
    """대화 기본 정보"""

    id: str
    user_id: str
    title: Optional[str] = None
    session_type: str  # 'general' | 'report_based'
    primary_document_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PrimaryDocumentInfo(BaseModel):
    """대화 목록용 간소화된 문서 정보"""

    id: str
    title: str


class ConversationListItem(ConversationBase):
    """대화 목록 아이템 (최적화)"""

    primary_document: Optional[PrimaryDocumentInfo] = None
    # MVP: last_message, message_count는 추후 추가 가능


class ConversationWithMessages(ConversationBase):
    """메시지 포함 대화"""

    messages: List[MessageBase]


# ===================================
# API Request Schemas
# ===================================


class CreateConversationRequest(BaseModel):
    """새 대화 생성 요청"""

    session_type: str  # 'general' | 'report_based'
    primary_document_id: Optional[str] = None
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    """메시지 전송 요청"""

    content: str
    user_level: Optional[str] = "beginner"  # 'beginner' | 'intermediate' | 'advanced'


# ===================================
# API Response Schemas
# ===================================


class ConversationListResponse(BaseModel):
    """대화 목록 응답 (페이지네이션)"""

    total: int
    items: List[ConversationListItem]


class ConversationDetailResponse(ConversationBase):
    """대화 상세 응답"""

    primary_document: Optional[PrimaryDocumentInfo] = None


class MessageListResponse(BaseModel):
    """메시지 목록 응답 (페이지네이션)"""

    total: int
    items: List[MessageBase]


class MessageCreateResponse(MessageBase):
    """메시지 생성 응답"""

    pass
