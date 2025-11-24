"""
LangGraph Nodes 구현

각 Node는 State를 입력받아 처리 후 State를 반환
"""

import logging
from time import time
from typing import Dict

from langchain_core.messages import AIMessage, HumanMessage

from app.core.context_builder import build_context
from app.core.embedding import get_query_embedding
from app.core.graph_state import ConversationState
from app.core.llm import generate_follow_up_questions, llm
from app.core.mretriever import retrieve_chunks_for_document, should_use_chunks
from app.core.prompts import (
    UserLevel,
    get_conversation_prompt,
)


logger = logging.getLogger(__name__)


# ===================================
# Node 1: RAG Retrieval
# ===================================


async def rag_retrieve_node(state: ConversationState) -> Dict:
    """
    RAG 검색 노드

    1. 질문 임베딩 생성
    2. Vector 검색
    3. 청크 사용 여부 판단
    4. 컨텍스트 조합

    Returns:
        State 업데이트 (query_embedding, retrieved_chunks, context, use_chunks)
    """
    start = time()

    question = state["question"]
    document_id = state.get("document_id")

    # 1. Embedding 생성
    query_embedding = get_query_embedding(question)

    # 2. Vector 검색 (임시로 None 체크)
    if document_id:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            chunks = retrieve_chunks_for_document(
                db=db,
                embedding=query_embedding,
                document_id=document_id,
                top_k=3,
            )
        finally:
            db.close()
    else:
        chunks = []

    # 3. 청크 사용 여부 판단
    decision = should_use_chunks(
        document_id=str(document_id) if document_id else None,
        chunks=chunks,
        similarity_threshold=0.7,
    )

    # 4. 컨텍스트 조합
    context = build_context(chunks) if decision["use_chunks"] else ""

    elapsed = int((time() - start) * 1000)
    logger.info(
        f"🔍 RAG Retrieve: {elapsed}ms, chunks={len(chunks)}, use={decision['use_chunks']}"
    )

    return {
        "query_embedding": query_embedding,
        "retrieved_chunks": [
            {
                "id": str(chunk.id),
                "content": chunk.content[:200],
                "similarity": chunk.similarity if hasattr(chunk, "similarity") else 0,
            }
            for chunk in chunks
        ],
        "context": context,
        "use_chunks": decision["use_chunks"],
        "decision_reason": decision["reason"],
        "max_similarity": decision["max_similarity"],
    }


# ===================================
# Node 2: LLM Generation
# ===================================


async def llm_generate_node(state: ConversationState) -> Dict:
    """
    LLM 답변 생성 노드

    1. 프롬프트 선택
    2. 사용자 메시지 구성
    3. LLM 체인 실행
    4. 메시지 상태 업데이트

    Returns:
        State 업데이트 (answer, messages, model_version, token_usage)
    """
    start = time()

    question = state["question"]
    context = state.get("context", "")
    document_id = state.get("document_id")
    user_level = state.get("user_level", "beginner")
    messages = state.get("messages", [])

    # 1. UserLevel enum 변환
    try:
        level = UserLevel(user_level.lower())
    except ValueError:
        level = UserLevel.BEGINNER

    # 2. 시나리오에 맞는 프롬프트 템플릿 선택
    prompt = get_conversation_prompt(
        user_level=level,
        document_id=str(document_id) if document_id else None,
        context_exists=bool(context and context.strip()),
    )

    # 3. LLM 체인 구성
    chain = prompt | llm

    # 4. 사용자 메시지 구성 (컨텍스트 포함)
    if context and context.strip():
        user_message_content = f"""[검색된 문서 정보]
{context}

[현재 질문]
{question}"""
    else:
        user_message_content = question

    # 5. LLM 호출
    result = await chain.ainvoke(
        {"messages": messages + [HumanMessage(content=user_message_content)]}
    )
    answer = result.content.strip()

    # 6. 토큰 사용량 추출
    token_usage = {}
    if hasattr(result, "response_metadata"):
        metadata = result.response_metadata
        token_usage = {
            "prompt": metadata.get("prompt_tokens", 0),
            "completion": metadata.get("completion_tokens", 0),
            "total": metadata.get("total_tokens", 0),
        }

    # 7. 메시지 업데이트 (Human + AI)
    # HumanMessage는 컨텍스트 없이 원본 질문만 저장하여 히스토리 UI에 표시
    updated_messages = messages + [
        HumanMessage(content=question),
        AIMessage(content=answer),
    ]

    elapsed = int((time() - start) * 1000)
    logger.info(f"🤖 LLM Generate: {elapsed}ms, tokens={token_usage.get('total', 0)}")

    return {
        "answer": answer,
        "messages": updated_messages,
        "model_version": "solar-pro2",
        "token_usage": token_usage,
    }


# ===================================
# Node 3: Follow-up Questions
# ===================================


async def followup_node(state: ConversationState) -> Dict:
    """
    후속 질문 생성 노드

    Returns:
        State 업데이트 (follow_up_questions)
    """
    start = time()

    question = state["question"]
    answer = state["answer"]
    context = state.get("context", "")
    user_level = state.get("user_level", "beginner")

    # UserLevel enum 변환
    try:
        level = UserLevel(user_level.lower())
    except ValueError:
        level = UserLevel.BEGINNER

    # 후속 질문 생성
    follow_ups = generate_follow_up_questions(
        question=question,
        answer=answer,
        context=context,
        user_level=level,
        num_questions=3,
    )

    elapsed = int((time() - start) * 1000)
    logger.info(f"💡 Followup: {elapsed}ms, count={len(follow_ups)}")

    return {
        "follow_up_questions": follow_ups,
    }
