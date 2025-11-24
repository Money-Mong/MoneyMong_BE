# app/core/metriever.py
import json
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def retrieve_chunks(db: Session, embedding, top_k: int = 3):
    # 문자열이면 JSON 파싱
    if isinstance(embedding, str):
        embedding = json.loads(embedding)

    print(f"DEBUG: embedding type = {type(embedding)}")

    sql = text("""
        SELECT
            id,
            document_id,
            chunk_index,
            content,
            content_type,
            page_numbers,
            1 - (embedding <=> (:query_embedding)::vector) AS similarity
        FROM document_chunks
        ORDER BY embedding <=> (:query_embedding)::vector
        LIMIT :top_k;
    """)

    params = {
        "query_embedding": embedding,  # 리스트 그대로 전달
        "top_k": top_k,
    }

    print(f"DEBUG: params = OK (embedding length={len(embedding)})")

    rows = db.execute(sql, params).fetchall()
    return rows


def retrieve_chunks_for_document(
    db: Session, embedding, document_id: Optional[UUID] = None, top_k: int = 3
):
    """
    문서 ID로 필터링된 청크 검색
    """

    # 문자열이면 JSON 파싱
    if isinstance(embedding, str):
        embedding = json.loads(embedding)

    print(f"DEBUG: embedding type = {type(embedding)}")

    # document_id 필터 추가
    where_clause = ""
    if document_id:
        where_clause = "WHERE document_id = :document_id"

    sql = text(f"""
        SELECT
            id,
            document_id,
            chunk_index,
            content,
            content_type,
            page_numbers,
            1 - (embedding <=> (:query_embedding)::vector) AS similarity
        FROM document_chunks
        {where_clause}
        ORDER BY embedding <=> (:query_embedding)::vector
        LIMIT :top_k;
        """)

    params = {
        "query_embedding": embedding,  # 리스트 그대로 전달
        "top_k": top_k,
    }

    if document_id:
        params["document_id"] = str(document_id)

    print(f"DEBUG: params = OK (embedding length={len(embedding)})")

    rows = db.execute(sql, params).fetchall()
    return rows


def should_use_chunks(
    document_id: Optional[str],
    chunks: list,
    similarity_threshold: float = 0.7,
) -> Dict[str, any]:
    """
    청크 사용 여부 판단

    Args:
        document_id: 문서 ID (있으면 문서 기반 대화)
        chunks: 검색된 청크 리스트 (similarity 포함)
        similarity_threshold: 유사도 임계값 (기본: 0.7)

    Returns:
        {
            "use_chunks": bool,
            "max_similarity": float,
            "reason": str
        }
    """

    # 1. document_id가 있으면 무조건 청크 사용
    if document_id:
        max_sim = max([c.similarity for c in chunks]) if chunks else 0.0
        return {
            "use_chunks": True,
            "max_similarity": max_sim,
            "reason": "document_based_conversation",
        }

    # 2. 청크가 없으면 일반 대화
    if not chunks:
        return {
            "use_chunks": False,
            "max_similarity": 0.0,
            "reason": "no_relevant_chunks",
        }

    # 3. 유사도 기반 판단
    max_similarity = max([c.similarity for c in chunks])

    if max_similarity >= similarity_threshold:
        return {
            "use_chunks": True,
            "max_similarity": max_similarity,
            "reason": "relevant_chunks_found",
        }
    else:
        return {
            "use_chunks": False,
            "max_similarity": max_similarity,
            "reason": "low_similarity",
        }
