"""
LangGraph State Schema 정의

대화 상태를 관리하는 TypedDict 스키마
"""

from typing import Any, Dict, List, Optional, TypedDict
from uuid import UUID

from langchain_core.messages import BaseMessage


class ConversationState(TypedDict, total=False):
    """
    대화 상태 스키마

    LangGraph가 자동으로 체크포인트에 저장/복원
    """

    # === 입력 ===
    question: str  # 사용자 질문
    conversation_id: UUID  # 대화 ID (thread_id)
    document_id: Optional[UUID]  # 문서 ID (report_based 세션용)
    user_level: str  # 사용자 레벨 ("beginner", "intermediate", "advanced")

    # === 대화 히스토리 (자동 관리) ===
    messages: List[BaseMessage]  # [HumanMessage, AIMessage, ...]

    # === RAG 파이프라인 상태 ===
    query_embedding: Optional[List[float]]  # 질문 임베딩
    retrieved_chunks: List[Dict[str, Any]]  # 검색된 청크들
    context: str  # 조합된 컨텍스트
    use_chunks: bool  # 청크 사용 여부
    decision_reason: str  # 청크 사용 결정 이유
    max_similarity: float  # 최대 유사도

    # === LLM 출력 ===
    answer: str  # AI 답변
    model_version: str  # 사용된 모델
    token_usage: Dict[str, int]  # 토큰 사용량

    # === 후속 질문 ===
    follow_up_questions: List[str]  # 추천 후속 질문

    # === 메타데이터 ===
    latency_ms: int  # 처리 시간 (밀리초)
    error: Optional[str]  # 에러 메시지 (있을 경우)
