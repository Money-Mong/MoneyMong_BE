# app/services/rag_service.py

from sqlalchemy.orm import Session
from app.schemas.rag import AskRequest, AskResponse

from app.core.embedding import get_query_embedding
from app.core.mretriever import retrieve_chunks
from app.core.context_builder import build_context
from app.core.llm import generate_answer

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
