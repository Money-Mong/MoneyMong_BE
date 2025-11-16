"""
Document Service Layer
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, DocumentSummary


logger = logging.getLogger(__name__)


class DocumentService:
    """Document 비즈니스 로직 처리"""

    def __init__(self, db: Session):
        self.db = db

    def get_documents(self, skip: int = 0, limit: int = 20) -> List[Document]:
        """
        전체 문서 목록 조회 (모든 사용자 공통)

        Args:
            skip: 건너뛸 문서 수
            limit: 조회할 문서 수

        Returns:
            문서 목록
        """
        try:
            documents = (
                self.db.query(Document)
                .options(joinedload(Document.summary))  # DocumentSummary 조인
                .filter(Document.processing_status == "completed")
                .order_by(desc(Document.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )

            logger.info(f"Retrieved {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise

    def get_document_by_id(self, document_id: UUID) -> Optional[Document]:
        """
        개별 문서 조회

        Args:
            document_id: 문서 ID

        Returns:
            문서 객체 또는 None
        """
        try:
            document = (
                self.db.query(Document)
                .filter(
                    Document.id == document_id,
                    Document.processing_status == "completed",
                )
                .first()
            )

            if document:
                logger.info(f"Retrieved document {document_id}")
            else:
                logger.warning(f"Document {document_id} not found")

            return document

        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {str(e)}")
            raise

    def get_document_summary(self, document_id: UUID) -> Optional[DocumentSummary]:
        """
        문서 요약 조회

        Args:
            document_id: 문서 ID

        Returns:
            문서 요약 객체 또는 None
        """
        try:
            # 문서 존재 여부 확인
            document = self.get_document_by_id(document_id)
            if not document:
                return None

            # 최신 요약 조회
            summary = (
                self.db.query(DocumentSummary)
                .filter(DocumentSummary.document_id == document_id)
                .order_by(desc(DocumentSummary.created_at))
                .first()
            )

            if summary:
                logger.info(f"Retrieved summary for document {document_id}")
            else:
                logger.warning(f"Summary not found for document {document_id}")

            return summary

        except Exception as e:
            logger.error(
                f"Error retrieving summary for document {document_id}: {str(e)}"
            )
            raise

    def count_documents(self) -> int:
        """
        전체 문서 개수 조회

        Returns:
            문서 개수
        """
        try:
            count = self.db.query(Document).count()
            return count

        except Exception as e:
            logger.error(f"Error counting documents: {str(e)}")
            raise
