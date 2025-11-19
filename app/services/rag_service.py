# app/services/rag_service.py

from time import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context_builder import build_context
from app.core.embedding import get_query_embedding
from app.core.llm import (
    generate_answer,
    generate_conversation_answer,
    generate_follow_up_questions,
)
from app.core.mretriever import (
    retrieve_chunks,
    retrieve_chunks_for_document,
    should_use_chunks,
)
from app.core.prompts import UserLevel
from app.schemas.rag import AskRequest, AskResponse


def run_rag_pipeline(db: Session, payload: AskRequest) -> AskResponse:
    question = payload.question

    # 1) 사용자 질문 임베딩 생성
    query_vector = get_query_embedding(question)

    # 2) pgvector similarity search
    chunks = retrieve_chunks(db, query_vector, top_k=3)

    # 3) context 생성
    context_text = build_context(chunks)

    # 4) LLM 호출
    answer = generate_answer(question, context_text)

    return AskResponse(answer=answer)


class RAGService:
    """RAG 비즈니스 로직 처리"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_conversation_response(
        self,
        question: str,
        document_id: Optional[UUID] = None,
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = 3,
        user_level: str = "beginner",
    ) -> Dict[str, Any]:
        """
        RAG 파이프라인 실행

        RAG Service 책임:
        - Embedding 생성
        - Vector 검색
        - 청크 사용 여부 판단 (유사도 기반)
        - Context 조합
        - LLM 호출 (user_level 반영)
        """

        start_time = time()

        # 1. Embedding
        query_vector = get_query_embedding(question)

        # 2. Vector 검색
        chunks = retrieve_chunks_for_document(
            db=self.db, embedding=query_vector, document_id=document_id, top_k=top_k
        )

        # 3. 청크 사용 여부 판단
        decision = should_use_chunks(
            document_id=str(document_id) if document_id else None,
            chunks=chunks,
            similarity_threshold=0.7,
        )

        # 4. LLM 호출 (청크 유무에 따라 context 설정)
        context_text = build_context(chunks) if decision["use_chunks"] else ""

        # UserLevel enum 변환
        try:
            level = UserLevel(user_level.lower())
        except ValueError:
            level = UserLevel.BEGINNER

        llm_response = generate_conversation_answer(
            document_id=document_id,
            question=question,
            context=context_text,
            history=conversation_history,
            user_level=level,
        )

        # 5. 후속 질문 생성
        follow_ups = generate_follow_up_questions(
            question=question,
            answer=llm_response["answer"],
            context=context_text,
            user_level=level,
        )

        # 6. 응답 구성
        end_time = time()

        return {
            "answer": llm_response["answer"],
            "cited_chunks": [chunk.id for chunk in chunks]
            if decision["use_chunks"]
            else [],
            "follow_up_questions": follow_ups,
            "reference_context": {
                "chunks_used": len(chunks) if decision["use_chunks"] else 0,
                "document_id": str(document_id) if document_id else None,
                "max_similarity": decision["max_similarity"],
                "decision_reason": decision["reason"],
                "user_level": user_level,
            },
            "model_version": llm_response.get("model", "solar-pro2"),
            "token_usage": llm_response.get("token_usage", {}),
            "latency_ms": int((end_time - start_time) * 1000),
        }
