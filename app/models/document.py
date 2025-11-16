"""
Document 관련 SQLAlchemy Models
"""

from sqlalchemy import Column, String, Text, Integer, BigInteger, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.database import Base


class Document(Base):
    """문서 메타데이터 (PDF, URL 등)"""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("source_type IN ('pdf', 'url', 'text', 'md')", name="chk_source_type"),
        CheckConstraint("processing_status IN ('pending', 'processing', 'completed', 'failed')", name="chk_processing_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 소스 정보
    source_type = Column(String(20), nullable=False)  # 문서 소스 타입 (pdf, url, text, md)
    source_url = Column(Text, nullable=False)  # 원본 URL (크롤링 소스)
    source_nid = Column(Text, nullable=False)  # 소스 고유 식별자 (nid)
    file_url = Column(Text)  # 파일 다운로드 URL
    file_id = Column(Text)  # 파일 고유 ID

    # 문서 메타데이터
    title = Column(String(500), nullable=False)  # 문서 제목
    author = Column(String(255))  # 저자 또는 기관명
    published_date = Column(Date)  # 발행일

    # 파일 정보
    file_path = Column(Text)  # 저장된 파일 경로
    file_size = Column(BigInteger)  # 파일 크기 (bytes)
    total_pages = Column(Integer)  # 총 페이지 수 (PDF)
    language = Column(String(10), default="ko")  # 문서 언어 (ko, en 등)

    # 추가 정보
    doc_metadata = Column("metadata", JSONB, default=dict)  # 추가 메타데이터 (자유 형식 JSONB)
    processing_status = Column(String(20), default="pending")  # 처리 상태 (pending, processing, completed, failed)

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 최종 수정일

    # 관계
    layout = relationship("DocumentLayout", back_populates="document", cascade="all, delete-orphan")
    assets = relationship("DocumentAsset", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    summary = relationship("DocumentSummary", back_populates="document", uselist=False, cascade="all, delete-orphan")
    history = relationship("DocumentHistory", back_populates="document", cascade="all, delete-orphan")


class DocumentLayout(Base):
    """PDF 레이아웃 분석 결과 (페이지별)"""

    __tablename__ = "document_layout"
    __table_args__ = (
        CheckConstraint("element_type IN ('background', 'caption', 'footnote', 'formula', 'list-item', 'page-footer', 'page-header', 'picture', 'section-header', 'table', 'text', 'title')", name="chk_element_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    page_number = Column(Integer, nullable=False)  # 페이지 번호
    element_type = Column(String(50), nullable=False)  # 요소 타입 ('background', 'caption', 'footnote', 'formula', 'list-item', 'page-footer', 'page-header', 'picture', 'section-header', 'table', 'text', 'title')
    element_order = Column(Integer, nullable=False)  # 페이지 내 요소 순서
    bbox = Column(JSONB, nullable=False)  # Bounding Box 좌표 {x1, y1, x2, y2}
    content = Column(Text)  # 텍스트 내용 (text 타입인 경우)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("document_asset.id", ondelete="SET NULL"))  # 관련 에셋 ID
    layout_metadata = Column("metadata", JSONB, default=dict)  # 추가 메타데이터 (폰트, 색상 등)

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일

    # 관계
    document = relationship("Document", back_populates="layout")
    asset = relationship("DocumentAsset", foreign_keys=[asset_id])


class DocumentAsset(Base):
    """문서 내 이미지, 표 등 에셋"""

    __tablename__ = "document_asset"
    __table_args__ = (
        CheckConstraint("asset_type IN ('image', 'table', 'chart')", name="chk_asset_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    asset_type = Column(String(20), nullable=False)  # 에셋 타입 (image, table, chart)
    page_number = Column(Integer, nullable=False)  # 페이지 번호
    file_path = Column(Text)  # 저장된 파일 경로
    raw_data = Column(Text)  # 원본 데이터
    description = Column(Text)  # LLM 생성 설명 (이미지 캡션 등)
    extracted_text = Column(Text)  # OCR 추출 텍스트 (이미지 내 텍스트)
    asset_metadata = Column("metadata", JSONB, default=dict)  # 추가 메타데이터

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일

    # 관계
    document = relationship("Document", back_populates="assets")


class DocumentChunk(Base):
    """벡터 임베딩을 위한 청크 데이터"""

    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint("content_type IN ('text', 'table_summary', 'image_caption')", name="chk_content_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    # 청크 데이터
    chunk_index = Column(Integer, nullable=False)  # 청크 순서
    content = Column(Text, nullable=False)  # 청크 텍스트 내용
    content_type = Column(String(20), default="text")  # 콘텐츠 타입 (text, table_summary, image_caption)
    page_numbers = Column(ARRAY(Integer), nullable=False)  # 관련 페이지 번호들 배열

    # 벡터 임베딩 (OpenAI 1536차원)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI 임베딩 벡터

    # 검색 최적화
    keywords = Column(ARRAY(String), default=list)  # 추출된 핵심 키워드 리스트 (키워드 검색용)

    # 메타데이터
    chunk_metadata = Column("metadata", JSONB, default=dict)  # 추가 메타데이터
    token_count = Column(Integer, nullable=False)  # 토큰 수

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일

    # 관계
    document = relationship("Document", back_populates="chunks")


class DocumentSummary(Base):
    """문서 전체 요약 (LLM 생성)"""

    __tablename__ = "document_summary"
    __table_args__ = (
        CheckConstraint("sentiment IN ('positive', 'neutral', 'negative')", name="chk_sentiment"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False)

    # 요약 컨텐츠
    summary_short = Column(Text, nullable=False)  # 짧은 요약 (200자 이내)
    summary_long = Column(Text, nullable=False)  # 긴 요약 (1000자 이내)
    key_points = Column(ARRAY(Text), default=list)  # 핵심 포인트 리스트
    entities = Column(JSONB, default=dict)  # NER 추출 엔티티 (회사명, 인명, 수치 등)

    # 처리 메타데이터
    model_version = Column(String(50), nullable=False)  # 사용된 LLM 모델 버전

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 최종 수정일

    # 관계
    document = relationship("Document", back_populates="summary")


class DocumentHistory(Base):
    """문서 처리 이력 (크롤링, 파싱, 임베딩 등)"""

    __tablename__ = "document_history"
    __table_args__ = (
        CheckConstraint("action IN ('crawled', 'parsed', 'embedded', 'summarized', 'updated')", name="chk_action"),
        CheckConstraint("status IN ('started', 'completed', 'failed')", name="chk_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    action = Column(String(50), nullable=False)  # 작업 유형 (crawled, parsed, embedded, summarized, updated)
    status = Column(String(20), nullable=False)  # 작업 상태 (started, completed, failed)
    details = Column(JSONB, default=dict)  # 작업 상세 정보 (처리 시간, 에러 메시지 등)

    started_at = Column(DateTime(timezone=True), nullable=False)  # 작업 시작 시간
    completed_at = Column(DateTime(timezone=True))  # 작업 완료 시간

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일

    # 관계
    document = relationship("Document", back_populates="history")
