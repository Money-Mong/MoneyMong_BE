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
from app.core.mretriever import retrieve_chunks, retrieve_chunks_for_document
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
    ) -> Dict[str, Any]:
        """
        RAG 파이프라인 실행

        RAG Service 책임:
        - Embedding 생성
        - Vector 검색
        - Context 조합
        - LLM 호출
        """

        start_time = time()  # 레이턴시 체크용

        # 1. Embedding
        query_vector = get_query_embedding(question)

        # 2. Vector 검색 (document_id 필터)
        chunks = retrieve_chunks_for_document(
            db=self.db, embedding=query_vector, document_id=document_id, top_k=top_k
        )
        # TODO 청크 사용 여부에 따른 분기 처리 필요
        if not chunks:
            return self._build_no_context_response(question)

        # 3. Context 조합
        context_text = build_context(chunks)

        # 4. LLM 호출 (히스토리 포함)
        llm_response = generate_conversation_answer(
            question=question, context=context_text, history=conversation_history
        )

        # 5. 후속 질문 생성
        follow_ups = generate_follow_up_questions(
            question=question, answer=llm_response["answer"], context=context_text
        )

        # 6. 시간계산
        end_time = time()

        return {
            "answer": llm_response["answer"],
            "cited_chunks": [chunk.id for chunk in chunks],
            "follow_up_questions": follow_ups,
            "reference_context": {
                "chunks_used": len(chunks),
                "context_length": len(context_text),
                "document_id": str(document_id) if document_id else None,
            },
            "model_version": llm_response.get(
                "model", "solar-pro2"
            ),  # 일반 Solar 모델로 정의
            "token_usage": llm_response.get("token_usage", {}),
            "latency_ms": int((end_time - start_time) * 1000),
        }

    def _build_no_context_response(self, question: str) -> Dict[str, Any]:
        """Fallback 응답"""
        return {
            "answer": "죄송합니다. 관련된 정보를 찾을 수 없습니다.",
            "cited_chunks": [],
            "follow_up_questions": [],
            "reference_context": {"error": "no_chunks_found"},
            "model_version": "fallback",
            "token_usage": {},
            "latency_ms": 0,
        }
