"""
Document API Endpoints
"""

from datetime import date
from typing import List, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas import (
    DocumentBase,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentSummaryBase,
    DocumentSummaryResponse,
    DocumentWithSummary,
)
from app.services.document_service import DocumentService


router = APIRouter()


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """DocumentService 의존성 주입"""
    return DocumentService(db)


@router.get("", summary="문서 목록 조회", response_model=DocumentListResponse)
async def get_documents(
    search: str = "",
    page: int = 1,
    page_size: int = 20,
    sort: Literal["published_date", "title"] = "published_date",
    order: Literal["asc", "desc"] = "desc",
    start_date: date | None = Query(None, description="발행일 검색 시작 (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="발행일 검색 종료 (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    문서 목록 조회 (모든 사용자 공통)

    Parameters:
    - search: 제목 검색어
    - page: 페이지 번호 (1부터 시작)
    - page_size: 페이지당 문서 수
    - sort: 정렬 기준 (published_date, title)
    - order: 정렬 방향 (asc, desc)
    - start_date, end_date: 발행일 범위 필터 (published_date 기준)

    Returns:
    - DocumentListResponse: 문서 목록 (total, items)
    """

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1

    skip = (page - 1) * page_size
    limit = page_size

    documents = document_service.get_documents(
        skip=skip,
        limit=limit,
        search=search,
        sort=sort,
        order=order,
        start_date=start_date,
        end_date=end_date,
    )
    total = document_service.count_documents(
        search=search,
        start_date=start_date,
        end_date=end_date,
    )

    items: List[DocumentWithSummary] = []
    for doc in documents:
        summary_schema: DocumentSummaryBase | None = None
        if doc.summary:
            summary_schema = DocumentSummaryBase(
                id=str(doc.summary.id),
                document_id=str(doc.summary.document_id),
                summary_short=doc.summary.summary_short,
                summary_long=doc.summary.summary_long,
                key_points=doc.summary.key_points or [],
                entities=doc.summary.entities,
                model_version=doc.summary.model_version,
                created_at=doc.summary.created_at,
                updated_at=doc.summary.updated_at,
            )

        items.append(
            DocumentWithSummary(
                id=str(doc.id),
                source_type=doc.source_type,
                source_url=doc.source_url,
                title=doc.title,
                author=doc.author,
                published_date=doc.published_date,
                file_path=doc.file_path,
                file_size=doc.file_size,
                total_pages=doc.total_pages,
                language=doc.language,
                metadata=doc.doc_metadata,
                processing_status=doc.processing_status,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                summary=summary_schema,
            )
        )

    return DocumentListResponse(total=total, items=items)


@router.get(
    "/{document_id}", summary="개별 문서 조회", response_model=DocumentDetailResponse
)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    개별 문서 조회

    Parameters:
    - document_id: 문서 ID

    Returns:
    - DocumentDetailResponse: 문서 상세 정보
    """
    document = document_service.get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailResponse(
        id=str(document.id),
        source_type=document.source_type,
        source_url=document.source_url,
        title=document.title,
        author=document.author,
        published_date=document.published_date,
        file_path=document.file_path,
        file_size=document.file_size,
        total_pages=document.total_pages,
        language=document.language,
        metadata=document.doc_metadata,
        processing_status=document.processing_status,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get(
    "/{document_id}/summary",
    summary="개별 문서 요약 조회",
    response_model=DocumentSummaryResponse,
)
async def get_document_summary(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    개별 문서 요약 조회

    Parameters:
    - document_id: 문서 ID

    Returns:
    - DocumentSummaryResponse: 문서 요약 정보
    """
    summary = document_service.get_document_summary(document_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Document summary not found")

    return DocumentSummaryResponse(
        id=str(summary.id),
        document_id=str(summary.document_id),
        summary_short=summary.summary_short,
        summary_long=summary.summary_long,
        key_points=summary.key_points,
        entities=summary.entities,
        model_version=summary.model_version,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )
