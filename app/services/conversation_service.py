"""
Conversation Service Layer
"""

import logging
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.conversation import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationService:
    """Conversation 비즈니스 로직 처리"""

    def __init__(self, db: Session):
        self.db = db

    def get_conversations(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
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

            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations

        except Exception as e:
            logger.error(f"Error retrieving conversations for user {user_id}: {str(e)}")
            raise

    def get_conversation_by_id(
        self,
        conversation_id: UUID,
        user_id: UUID
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
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
                .first()
            )

            if conversation:
                logger.info(f"Retrieved conversation {conversation_id} for user {user_id}")
            else:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")

            return conversation

        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {str(e)}")
            raise

    def create_conversation(
        self,
        user_id: UUID,
        document_id: Optional[UUID] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """
        새로운 대화 생성

        Args:
            user_id: 사용자 ID
            document_id: 문서 ID (선택)
            title: 대화 제목 (선택)

        Returns:
            생성된 대화 객체
        """
        try:
            conversation = Conversation(
                user_id=user_id,
                document_id=document_id,
                title=title or "새 대화"
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
        self,
        conversation_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
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

            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving messages for conversation {conversation_id}: {str(e)}")
            raise

    def add_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        role: str,
        content: str
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
                logger.warning(f"Cannot add message - conversation {conversation_id} not found")
                return None

            # 메시지 생성
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content
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
            logger.error(f"Error adding message to conversation {conversation_id}: {str(e)}")
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
