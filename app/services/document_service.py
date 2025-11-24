"""
Document Service Layer
"""

import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, DocumentSummary


logger = logging.getLogger(__name__)


class DocumentService:
    """Document 비즈니스 로직 처리"""

    def __init__(self, db: Session):
        self.db = db

    def get_documents(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        sort: str = "published_date",
        order: str = "desc",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Document]:
        """
        전체 문서 목록 조회 (모든 사용자 공통)

        Args:
            skip: 건너뛸 문서 수
            limit: 조회할 문서 수
            search: 검색어 (제목, 요약 등)
            sort: 정렬 기준 필드
            order: 정렬 방향 (asc, desc)
            start_date: published_date 시작일
            end_date: published_date 종료일

        Returns:
            문서 목록
        """
        try:
            # 기본 쿼리: 완료된 문서만 조회
            query = (
                self.db.query(Document)
                .options(joinedload(Document.summary))  # 결과 로딩용 eager join
                .filter(Document.processing_status == "completed")
            )

            # 1. 발행일 범위 필터
            if start_date:
                query = query.filter(Document.published_date >= start_date)
            if end_date:
                query = query.filter(Document.published_date <= end_date)

            # 2. 검색어 필터링 (제목, 요약, 엔터티)
            if search:
                search_term = f"%{search}%"

                # 요약(summary_long)을 WHERE 절에서 쓰기 위해 실제로 조인
                query = query.outerjoin(
                    DocumentSummary,
                    DocumentSummary.document_id == Document.id,
                )

                query = query.filter(
                    or_(
                        Document.title.ilike(search_term),
                        DocumentSummary.summary_long.ilike(search_term),
                        DocumentSummary.entities["main_company"].astext.ilike(
                            search_term
                        ),
                        DocumentSummary.entities["main_ticker"].astext.ilike(
                            search_term
                        ),
                    )
                )

            # 3. 정렬
            sort_map = {
                "published_date": Document.published_date,
                "title": Document.title,
            }
            sort_column = sort_map.get(sort, Document.published_date)

            if order == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

            # 4. 페이지네이션
            documents = query.offset(skip).limit(limit).all()

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

    def count_documents(
        self,
        search: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """
        전체 문서 개수 조회

        Args:
            search: 검색어 (get_documents와 동일한 조건)
            start_date, end_date: published_date 범위

        Returns:
            문서 개수
        """
        try:
            # 기본 쿼리: 완료된 문서만 기준
            query = self.db.query(Document).filter(
                Document.processing_status == "completed"
            )

            # get_documents와 동일한 조건 적용
            if start_date:
                query = query.filter(Document.published_date >= start_date)
            if end_date:
                query = query.filter(Document.published_date <= end_date)

            if search:
                search_term = f"%{search}%"

                query = query.outerjoin(
                    DocumentSummary,
                    DocumentSummary.document_id == Document.id,
                )

                query = query.filter(
                    or_(
                        Document.title.ilike(search_term),
                        DocumentSummary.summary_long.ilike(search_term),
                        DocumentSummary.entities["main_company"].astext.ilike(
                            search_term
                        ),
                        DocumentSummary.entities["main_ticker"].astext.ilike(
                            search_term
                        ),
                    )
                )

            count = query.count()
            return count

        except Exception as e:
            logger.error(f"Error counting documents: {str(e)}")
            raise
