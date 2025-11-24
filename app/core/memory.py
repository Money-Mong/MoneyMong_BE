"""
LangGraph StateGraph 기반 대화 메모리 시스템
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


# ===================================
# Singleton Instances
# ===================================

_pool: Optional[AsyncConnectionPool] = None
_checkpointer: Optional[AsyncPostgresSaver] = None
_conversation_graph = None  # Graph 인스턴스


async def init_checkpoint_system():
    """
    LangGraph 시스템 초기화 (앱 시작 시 호출)

    Creates:
        - Async connection pool
        - PostgresSaver (checkpointer)
        - Conversation graph (compiled)
        - DB tables (checkpoints, checkpoint_writes)
    """
    global _pool, _checkpointer, _conversation_graph

    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=settings.DATABASE_URL,
            min_size=5,
            max_size=20,
            timeout=30,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        logger.info("Checkpoint connection pool created")

    if _checkpointer is None:
        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()  # 테이블 자동 생성
        logger.info("LangGraph checkpoint tables initialized")

    if _conversation_graph is None:
        from app.core.conversation_graph import create_conversation_graph

        _conversation_graph = create_conversation_graph(_checkpointer)
        logger.info("Conversation graph compiled")


async def get_checkpointer() -> AsyncPostgresSaver:
    """체크포인터 가져오기"""
    if _checkpointer is None:
        await init_checkpoint_system()
    return _checkpointer


def get_conversation_graph():
    """
    컴파일된 대화 그래프 가져오기

    Returns:
        Compiled StateGraph with checkpointer
    """
    global _conversation_graph

    if _conversation_graph is None:
        raise RuntimeError(
            "Graph not initialized. Call init_checkpoint_system() first."
        )

    return _conversation_graph


async def close_checkpoint_system():
    """LangGraph 시스템 종료 (앱 종료 시 호출)"""
    global _pool, _checkpointer, _conversation_graph

    if _pool:
        await _pool.close()
        _pool = None
        _checkpointer = None
        _conversation_graph = None
        logger.info("LangGraph system closed")


# ===================================
# Graph 기반 대화 실행 (자동 체크포인트)
# ===================================


async def run_conversation(
    conversation_id: UUID,
    question: str,
    document_id: Optional[UUID] = None,
    user_level: str = "beginner",
) -> Dict[str, Any]:
    """
    대화 그래프 실행 (자동 체크포인트 저장)

    Graph가 자동으로:
    1. 이전 대화 히스토리 로드 (체크포인트에서)
    2. RAG 파이프라인 실행
    3. 새로운 메시지 추가
    4. 체크포인트에 저장

    Args:
        conversation_id: 대화 ID (thread_id)
        question: 사용자 질문
        document_id: 문서 ID (optional)
        user_level: 사용자 레벨

    Returns:
        {
            "answer": str,
            "follow_up_questions": List[str],
            "cited_chunks": List[str],
            "reference_context": Dict,
            "model_version": str,
            "token_usage": Dict,
        }
    """
    graph = get_conversation_graph()
    thread_id = str(conversation_id)

    # Graph 실행 (자동으로 히스토리 로드 + 체크포인트 저장)
    result = await graph.ainvoke(
        {
            "question": question,
            "conversation_id": conversation_id,
            "document_id": document_id,
            "user_level": user_level,
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    logger.info(f"Conversation executed: {conversation_id}")

    # 서비스 계층 호환 포맷으로 변환
    return {
        "answer": result["answer"],
        "follow_up_questions": result.get("follow_up_questions", []),
        "cited_chunks": [chunk["id"] for chunk in result.get("retrieved_chunks", [])],
        "reference_context": {
            "chunks_used": len(result.get("retrieved_chunks", [])),
            "document_id": str(document_id) if document_id else None,
            "max_similarity": result.get("max_similarity", 0),
            "decision_reason": result.get("decision_reason", ""),
            "user_level": user_level,
        },
        "model_version": result.get("model_version", "solar-pro2"),
        "token_usage": result.get("token_usage", {}),
    }


# ===================================
# 유틸리티 함수 (히스토리 조회, 관리)
# ===================================


async def load_messages(
    conversation_id: UUID,
    limit: int = 5,
) -> List[BaseMessage]:
    """
    체크포인트에서 메시지 로드

    Args:
        conversation_id: 대화 ID
        limit: 최근 N개 (0이면 전체)

    Returns:
        [HumanMessage, AIMessage, ...]
    """
    checkpointer = await get_checkpointer()
    thread_id = str(conversation_id)
    config = {"configurable": {"thread_id": thread_id}}

    checkpoint_tuple = await checkpointer.aget_tuple(config)

    if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
        return []

    messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])

    if limit > 0:
        return messages[-limit:]

    return messages


async def clear_conversation(conversation_id: UUID) -> None:
    """
    대화 메모리 초기화

    Args:
        conversation_id: 대화 ID
    """
    checkpointer = await get_checkpointer()
    thread_id = str(conversation_id)
    config = {"configurable": {"thread_id": thread_id}}

    # 빈 체크포인트로 덮어쓰기
    await checkpointer.aput(
        config,
        {
            "v": 1,
            "ts": "",
            "id": "",
            "channel_values": {"messages": []},
            "channel_versions": {"messages": 1},
            "versions_seen": {},
            "pending_sends": [],
        },
        {"source": "clear", "step": 0, "writes": {}},
        {},
    )

    logger.info(f"Conversation cleared: {conversation_id}")


async def get_message_count(conversation_id: UUID) -> int:
    """
    대화 메시지 개수 조회

    Args:
        conversation_id: 대화 ID

    Returns:
        메시지 개수
    """
    messages = await load_messages(conversation_id, limit=0)
    return len(messages)
