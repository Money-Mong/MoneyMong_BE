"""
Document API Endpoints
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.services.document_service import DocumentService
from app.schemas import (
    DocumentBase,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentSummaryResponse,
)

router = APIRouter()


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """DocumentService 의존성 주입"""
    return DocumentService(db)


@router.get("", summary="문서 목록 조회", response_model=DocumentListResponse)
async def get_documents(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    문서 목록 조회 (모든 사용자 공통)

    Parameters:
    - skip: 건너뛸 문서 수 (기본값: 0)
    - limit: 조회할 문서 수 (기본값: 20)

    Returns:
    - DocumentListResponse: 문서 목록 (total, items)
    """
    documents = document_service.get_documents(skip=skip, limit=limit)
    total = document_service.count_documents()

    items = [
        DocumentBase(
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
            updated_at=doc.updated_at
        )
        for doc in documents
    ]

    return DocumentListResponse(total=total, items=items)


@router.get("/{document_id}", summary="개별 문서 조회", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
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
        updated_at=document.updated_at
    )


@router.get("/{document_id}/summary", summary="개별 문서 요약 조회", response_model=DocumentSummaryResponse)
async def get_document_summary(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
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
        updated_at=summary.updated_at
    )

