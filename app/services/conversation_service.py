"""
Conversation Service Layer
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.memory import run_conversation
from app.models.conversation import Conversation, Message


logger = logging.getLogger(__name__)


class ConversationService:
    """Conversation 비즈니스 로직 처리"""

    def __init__(self, db: Session):
        self.db = db

    def get_conversations(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> List[Conversation]:
        """
        사용자의 대화 목록 조회

        Args:
            user_id: 사용자 ID
            skip: 건너뛸 대화 수
            limit: 조회할 대화 수

        Returns:
            대화 목록
        """
        try:
            conversations = (
                self.db.query(Conversation)
                .filter(Conversation.user_id == user_id)
                .order_by(desc(Conversation.updated_at))
                .offset(skip)
                .limit(limit)
                .all()
            )

            logger.info(
                f"Retrieved {len(conversations)} conversations for user {user_id}"
            )
            return conversations

        except Exception as e:
            logger.error(f"Error retrieving conversations for user {user_id}: {str(e)}")
            raise

    def get_conversation_by_id(
        self, conversation_id: UUID, user_id: UUID
    ) -> Optional[Conversation]:
        """
        개별 대화 조회

        Args:
            conversation_id: 대화 ID
            user_id: 사용자 ID

        Returns:
            대화 객체 또는 None
        """
        try:
            conversation = (
                self.db.query(Conversation)
                .filter(
                    Conversation.id == conversation_id, Conversation.user_id == user_id
                )
                .first()
            )

            if conversation:
                logger.info(
                    f"Retrieved conversation {conversation_id} for user {user_id}"
                )
            else:
                logger.warning(
                    f"Conversation {conversation_id} not found for user {user_id}"
                )

            return conversation

        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {str(e)}")
            raise

    def create_conversation(
        self,
        user_id: UUID,
        session_type: str,
        primary_document_id: Optional[UUID] = None,
        title: Optional[str] = None,
    ) -> Conversation:
        """
        새로운 대화 생성

        Args:
            user_id: 사용자 ID
            session_type: 세션 타입 ('general', 'report_based')
            primary_document_id: 문서 ID (선택)
            title: 대화 제목 (선택)

        Returns:
            생성된 대화 객체
        """
        try:
            conversation = Conversation(
                user_id=user_id,
                session_type=session_type,
                primary_document_id=primary_document_id,
                title=title or "새 대화",
            )

            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            return conversation

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating conversation for user {user_id}: {str(e)}")
            raise

    def get_conversation_messages(
        self, conversation_id: UUID, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[Message]:
        """
        대화의 메시지 목록 조회

        Args:
            conversation_id: 대화 ID
            user_id: 사용자 ID
            skip: 건너뛸 메시지 수
            limit: 조회할 메시지 수

        Returns:
            메시지 목록
        """
        try:
            # 대화 소유권 확인
            conversation = self.get_conversation_by_id(conversation_id, user_id)
            if not conversation:
                return []

            # 메시지 조회 (시간순 정렬)
            messages = (
                self.db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
                .offset(skip)
                .limit(limit)
                .all()
            )

            logger.info(
                f"Retrieved {len(messages)} messages for conversation {conversation_id}"
            )
            return messages

        except Exception as e:
            logger.error(
                f"Error retrieving messages for conversation {conversation_id}: {str(e)}"
            )
            raise

    def add_message(
        self, conversation_id: UUID, user_id: UUID, role: str, content: str
    ) -> Optional[Message]:
        """
        대화에 메시지 추가

        Args:
            conversation_id: 대화 ID
            user_id: 사용자 ID
            role: 메시지 역할 (user/assistant)
            content: 메시지 내용

        Returns:
            생성된 메시지 객체 또는 None
        """
        try:
            # 대화 소유권 확인
            conversation = self.get_conversation_by_id(conversation_id, user_id)
            if not conversation:
                logger.warning(
                    f"Cannot add message - conversation {conversation_id} not found"
                )
                return None

            # 메시지 생성
            message = Message(
                conversation_id=conversation_id, role=role, content=content
            )

            self.db.add(message)

            # 대화 업데이트 시간 갱신
            conversation.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(message)

            logger.info(f"Added message to conversation {conversation_id}")
            return message

        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Error adding message to conversation {conversation_id}: {str(e)}"
            )
            raise

    def count_user_conversations(self, user_id: UUID) -> int:
        """
        사용자의 전체 대화 개수 조회

        Args:
            user_id: 사용자 ID

        Returns:
            대화 개수
        """
        try:
            count = (
                self.db.query(Conversation)
                .filter(Conversation.user_id == user_id)
                .count()
            )
            return count

        except Exception as e:
            logger.error(f"Error counting conversations for user {user_id}: {str(e)}")
            raise

    def count_conversation_messages(self, conversation_id: UUID, user_id: UUID) -> int:
        """
        특정 대화의 전체 메시지 개수 조회

        Args:
            conversation_id: 대화 ID
            user_id: 사용자 ID

        Returns:
            메시지 개수
        """
        try:
            # 대화 소유권 확인
            conversation = self.get_conversation_by_id(conversation_id, user_id)
            if not conversation:
                return 0

            count = (
                self.db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .count()
            )
            return count

        except Exception as e:
            logger.error(
                f"Error counting messages for conversation {conversation_id}: {str(e)}"
            )
            raise

    async def process_user_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        content: str,
        user_level: str = "beginner",
    ) -> Message:
        """
        비즈니스 로직: 메시지 처리 및 AI 응답 생성

        Graph가 자동으로:
        - 대화 히스토리 로드 (체크포인트에서)
        - RAG 파이프라인 실행 (검색 → LLM → 후속질문)
        - 새로운 메시지 추가
        - 체크포인트 저장

        Service 책임:
        - 대화 소유권 확인
        - 메시지 저장 (DB용, API 응답용)
        - 트랜잭션 관리
        """
        try:
            # 1. 대화 확인
            conversation = self.get_conversation_by_id(conversation_id, user_id)
            if not conversation:
                raise ValueError("Conversation not found")

            # 2. Graph 실행 (자동으로 히스토리 로드 + RAG + 체크포인트 저장)

            rag_result = await run_conversation(
                conversation_id=conversation_id,
                question=content,
                document_id=conversation.primary_document_id,
                user_level=user_level,
            )

            # 3. 사용자 메시지 저장 (DB용, API 응답)
            user_message = self._save_user_message(conversation_id, content)

            # 4. AI 응답 저장 (DB용, API 응답)
            ai_message = self._save_ai_message(conversation_id, rag_result)

            # 5. 대화 시간 갱신
            self._update_conversation_timestamp(conversation)

            # 6. 커밋
            self.db.commit()
            self.db.refresh(ai_message)

            return ai_message

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error: {str(e)}")
            raise

    def _save_user_message(self, conversation_id: UUID, content: str) -> Message:
        """Private helper: 사용자 메시지 저장"""
        msg = Message(conversation_id=conversation_id, role="user", content=content)
        self.db.add(msg)
        self.db.flush()
        return msg

    def _save_ai_message(self, conversation_id: UUID, rag_result: dict) -> Message:
        """Private helper: AI 메시지 저장"""
        msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=rag_result["answer"],
            cited_chunks=rag_result.get("cited_chunks", []),
            follow_up_questions=rag_result.get("follow_up_questions", []),
            reference_context=rag_result.get("reference_context", {}),
            model_version=rag_result.get("model_version"),
            token_usage=rag_result.get("token_usage", {}),
            latency_ms=rag_result.get("latency_ms"),
        )
        self.db.add(msg)
        self.db.flush()
        return msg

    def _update_conversation_timestamp(self, conversation: Conversation):
        """Private helper: 시간 갱신"""
        conversation.updated_at = datetime.utcnow()
