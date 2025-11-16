# app/api/v1/rag.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.rag import AskRequest, AskResponse
from app.services.rag_service import run_rag_pipeline


router = APIRouter(tags=["RAG"])


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    payload: AskRequest,
    db: Session = Depends(get_db),
):
    """
    RAG 기반 질의응답 엔드포인트.
    - question → embedding
    - pgvector similarity search
    - context 생성
    - LLM 호출
    """
    return run_rag_pipeline(db, payload)
