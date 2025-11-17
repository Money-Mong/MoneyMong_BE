# app/core/metriever.py
import json
from typing import Optional
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
