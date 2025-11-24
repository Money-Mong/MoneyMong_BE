"""
Document API Schemas
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ===================================
# Document Schemas
# ===================================


class DocumentBase(BaseModel):
    """문서 기본 정보"""

    id: str
    source_type: str  # 'pdf' | 'url' | 'text' | 'md'
    source_url: str
    title: str
    author: Optional[str] = None
    published_date: Optional[date] = None

    # 파일 정보
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    total_pages: Optional[int] = None
    language: str = "ko"

    # 메타데이터 및 상태
    metadata: Optional[Dict[str, Any]] = None
    processing_status: str  # 'pending' | 'processing' | 'completed' | 'failed'

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentSummaryBase(BaseModel):
    """문서 요약 정보"""

    id: str
    document_id: str
    summary_short: str  # 200자 이내
    summary_long: str  # 1000자 이내
    key_points: List[str]
    entities: Optional[Dict[str, Any]] = None  # NER 추출 엔티티(쓸지는 모르겠음)
    model_version: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentWithSummary(DocumentBase):
    """요약 포함 문서"""

    summary: Optional[DocumentSummaryBase] = None


# ===================================
# API Response Schemas
# ===================================


class DocumentListResponse(BaseModel):
    """문서 목록 응답 (페이지네이션)"""

    total: int
    items: List[DocumentWithSummary]


class DocumentDetailResponse(DocumentBase):
    """문서 상세 응답"""

    pass


class DocumentSummaryResponse(DocumentSummaryBase):
    """문서 요약 응답"""

    pass
