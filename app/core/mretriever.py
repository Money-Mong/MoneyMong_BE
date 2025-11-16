# app/core/metriever.py
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

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
        "top_k": top_k
    }

    print(f"DEBUG: params = OK (embedding length={len(embedding)})")

    rows = db.execute(sql, params).fetchall()
    return rows
