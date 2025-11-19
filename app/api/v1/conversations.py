"""
Conversation API Endpoints
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas import (
    ConversationDetailResponse,
    ConversationListItem,
    ConversationListResponse,
    CreateConversationRequest,
    MessageBase,
    MessageCreateResponse,
    MessageListResponse,
    PrimaryDocumentInfo,
    SendMessageRequest,
)
from app.services.conversation_service import ConversationService


router = APIRouter()


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """ConversationService 의존성 주입"""
    return ConversationService(db)


@router.get("", summary="대화 목록 조회", response_model=ConversationListResponse)
async def get_conversations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    사용자의 대화 목록 조회

    Parameters:
    - skip: 건너뛸 대화 수
    - limit: 조회할 대화 수

    Returns:
    - ConversationListResponse: 대화 목록 (total, items)
    """
    conversations = conversation_service.get_conversations(current_user.id, skip, limit)
    total = conversation_service.count_user_conversations(current_user.id)

    items = [
        ConversationListItem(
            id=str(conv.id),
            user_id=str(conv.user_id),
            title=conv.title,
            session_type=conv.session_type,
            primary_document_id=str(conv.primary_document_id)
            if conv.primary_document_id
            else None,
            is_active=conv.is_active,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            primary_document=None,  # 일단 보류, 아직은 필요하지 않음
        )
        for conv in conversations
    ]

    return ConversationListResponse(total=total, items=items)


@router.get(
    "/{conversation_id}",
    summary="개별 대화 조회",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    개별 대화 조회

    Parameters:
    - conversation_id: 대화 ID

    Returns:
    - ConversationDetailResponse: 대화 상세 정보
    """
    conversation = conversation_service.get_conversation_by_id(
        conversation_id, current_user.id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetailResponse(
        id=str(conversation.id),
        user_id=str(conversation.user_id),
        title=conversation.title,
        session_type=conversation.session_type,
        primary_document_id=str(conversation.primary_document_id)
        if conversation.primary_document_id
        else None,
        is_active=conversation.is_active,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        primary_document=PrimaryDocumentInfo(
            id=str(conversation.primary_document.id),
            title=conversation.primary_document.title,
        )
        if conversation.primary_document
        else None,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="신규 대화 생성",
    response_model=ConversationDetailResponse,
)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    신규 대화 생성

    Request Body:
    - session_type: 'general' | 'report_based' (필수)
    - primary_document_id: document UUID (session_type='report_based'일 때 필수)
    - title: 대화 제목 (선택, 나중에 AI로 생성할 것 같음)

    Returns:
    - ConversationDetailResponse: 생성된 대화 정보
    """
    # session_type='report_based'일 때 primary_document_id 필수 검증
    if request.session_type == "report_based" and not request.primary_document_id:
        raise HTTPException(
            status_code=400,
            detail="primary_document_id is required for report_based sessions",
        )

    # 대화 생성
    conversation = conversation_service.create_conversation(
        user_id=current_user.id,
        session_type=request.session_type,
        primary_document_id=UUID(request.primary_document_id)
        if request.primary_document_id
        else None,
        title=request.title,
    )

    return ConversationDetailResponse(
        id=str(conversation.id),
        user_id=str(conversation.user_id),
        title=conversation.title,
        session_type=conversation.session_type,
        primary_document_id=str(conversation.primary_document_id)
        if conversation.primary_document_id
        else None,
        is_active=conversation.is_active,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        primary_document=PrimaryDocumentInfo(
            id=str(conversation.primary_document.id),
            title=conversation.primary_document.title,
        )
        if conversation.primary_document
        else None,
    )


@router.get(
    "/{conversation_id}/messages",
    summary="개별 대화 메시지 목록 조회",
    response_model=MessageListResponse,
)
async def get_conversation_messages(
    conversation_id: UUID,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    개별 대화 메시지 목록 조회

    Parameters:
    - conversation_id: 대화 ID
    - skip: 건너뛸 메시지 수 (기본값: 0)
    - limit: 조회할 메시지 수 (기본값: 20)

    Returns:
    - MessageListResponse: 메시지 목록 (total, items)
    """
    messages = conversation_service.get_conversation_messages(
        conversation_id=conversation_id, user_id=current_user.id, skip=skip, limit=limit
    )

    total = conversation_service.count_conversation_messages(
        conversation_id=conversation_id, user_id=current_user.id
    )

    items = [
        MessageBase(
            id=str(msg.id),
            conversation_id=str(msg.conversation_id),
            role=msg.role,
            content=msg.content,
            cited_chunks=[str(chunk_id) for chunk_id in msg.cited_chunks]
            if msg.cited_chunks
            else [],
            follow_up_questions=msg.follow_up_questions,
            created_at=msg.created_at,
        )
        for msg in messages
    ]

    return MessageListResponse(total=total, items=items)


@router.post(
    "/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
    summary="메시지 전송 및 AI 응답",
    response_model=MessageCreateResponse,
)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    사용자 메시지 전송 + AI 응답 생성

    Request Body:
    - content: 사용자 질문 (필수)

    Returns:
    - MessageCreateResponse: 생성된 AI 응답 메시지

    **TODO 구현 필요 사항**:
    1. 스트리밍 지원 (SSE)
    2. session_type 체크로 청크 사용여부 분기
    """
    try:
        ai_message = await conversation_service.process_user_message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            content=request.content,
        )

        # SQLAlchemy 모델을 Pydantic 모델로 수동 변환
        return MessageCreateResponse(
            id=str(ai_message.id),
            conversation_id=str(ai_message.conversation_id),
            role=ai_message.role,
            content=ai_message.content,
            cited_chunks=[str(chunk_id) for chunk_id in ai_message.cited_chunks],
            follow_up_questions=ai_message.follow_up_questions,
            reference_context=ai_message.reference_context,
            model_version=ai_message.model_version,
            token_usage=ai_message.token_usage,
            latency_ms=ai_message.latency_ms,
            created_at=ai_message.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # 로깅을 추가하여 서버 오류를 추적하는 것이 좋습니다.
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
