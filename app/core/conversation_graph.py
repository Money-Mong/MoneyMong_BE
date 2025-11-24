"""
LangGraph 대화 그래프 정의

RAG 파이프라인을 StateGraph로 구성
자동 체크포인트 저장/복원
"""

import logging
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph

from app.core.graph_nodes import followup_node, llm_generate_node, rag_retrieve_node
from app.core.graph_state import ConversationState


logger = logging.getLogger(__name__)


# ===================================
# Global Graph Instance
# ===================================

_conversation_graph = None


def create_conversation_graph(checkpointer: Optional[AsyncPostgresSaver] = None):
    """
    대화 그래프 생성

    Graph Structure:
        START → rag_retrieve → llm_generate → followup → END

    Args:
        checkpointer: PostgresSaver 인스턴스 (자동 체크포인트)

    Returns:
        Compiled graph
    """
    # StateGraph 생성
    graph = StateGraph(ConversationState)

    # Nodes 추가
    graph.add_node("rag_retrieve", rag_retrieve_node)
    graph.add_node("llm_generate", llm_generate_node)
    graph.add_node("followup", followup_node)

    # Edges 정의
    graph.set_entry_point("rag_retrieve")
    graph.add_edge("rag_retrieve", "llm_generate")
    graph.add_edge("llm_generate", "followup")
    graph.add_edge("followup", END)

    # 체크포인터와 함께 컴파일
    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("Conversation graph compiled")
    return compiled


def get_conversation_graph(checkpointer: AsyncPostgresSaver):
    """
    대화 그래프 가져오기 (Singleton)

    Args:
        checkpointer: PostgresSaver 인스턴스

    Returns:
        Compiled graph
    """
    global _conversation_graph

    if _conversation_graph is None:
        _conversation_graph = create_conversation_graph(checkpointer)

    return _conversation_graph


# ===================================
# Multi-Agent 확장 포인트
# ===================================


def create_multi_agent_graph(checkpointer: Optional[AsyncPostgresSaver] = None):
    """
    Multi-Agent 그래프 (향후 확장용)
    """
    # TODO: Multi-Agent 구현
    pass
