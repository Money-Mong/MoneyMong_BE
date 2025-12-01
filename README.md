# MoneyMong BE (머니몽 백엔드)
> 초보 투자자 맞춤 AI 튜터 머니몽 백엔드 API

**MoneyMong BE**는 금융 문서 기반 대화형 AI 서비스를 제공하는 백엔드 API입니다. RAG(Retrieval-Augmented Generation) 기술과 LangGraph를 활용하여 사용자 레벨에 맞는 맞춤형 금융 정보를 제공합니다.

## 목차

- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [시스템 아키텍처](#시스템-아키텍처)
- [설치 및 실행](#설치-및-실행)
- [API 엔드포인트](#api-엔드포인트)
- [핵심 로직](#핵심-로직)

## 주요 기능

### 1. RAG 기반 대화형 AI
- **유사도 검색**: pgvector 기반 문서 청크 검색 (코사인 유사도)
- **컨텍스트 기반 답변**: 검색된 문서를 기반으로 정확한 답변 생성
- **대화 메모리**: LangGraph checkpoint를 활용한 대화 히스토리 관리
- **후속 질문 제안**: 사용자 이해를 돕는 자동 질문 생성

### 2. 사용자 맞춤형 서비스
- **레벨별 응답**: 초급(쉬운 해설), 중급(핵심 요약), 고급(전문 분석)
- **OAuth 2.0 인증**: Google 소셜 로그인
- **세션 관리**: 일반 대화 및 문서 기반 대화 구분

### 3. 문서 관리 API
- **문서 조회**: 목록, 상세, 요약 정보 제공
- **벡터 검색**: 1536차원 임베딩 기반 유사도 검색
- **메타데이터 관리**: 문서 정보 및 처리 상태 관리

## 기술 스택

### Backend
- **FastAPI** 0.121.3 - 비동기 웹 프레임워크
- **Uvicorn** 0.38.0 - ASGI 서버
- **SQLAlchemy** 2.0.44 - ORM

### AI & LLM
- **LangChain** 1.0.8 - LLM 애플리케이션 프레임워크
- **LangGraph** - 대화 상태 관리 및 체크포인트
- **Upstage Solar-Pro2** - 한국어 특화 LLM
- **Sentence Transformers** - 임베딩 모델 (1536차원)

### Database
- **PostgreSQL** - 메인 데이터베이스
- **pgvector** - 벡터 유사도 검색

### Authentication
- **Google OAuth 2.0** - 소셜 로그인
- **JWT** - 토큰 기반 인증

## 시스템 아키텍처
![Image](https://github.com/user-attachments/assets/eabd067b-99e2-4760-be74-3f2724529400)


## 설치 및 실행

### 사전 요구사항
- Python 3.11+
- PostgreSQL 14+ (pgvector 확장)
- Upstage API 키
- Google OAuth 클라이언트 ID/Secret

### 환경 변수 설정
```bash
cp .env.example .env
# UPSTAGE_API_KEY, DATABASE_URL, GOOGLE_CLIENT_ID/SECRET, JWT_SECRET_KEY 설정
```

### PostgreSQL 설정
```sql
CREATE EXTENSION vector;
CREATE DATABASE moneymong;
```

### 로컬 실행
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Docker 실행
```bash
docker-compose up -d
```

### API 문서
- Swagger: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API 엔드포인트

### 인증 (Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/auth/login` | Google OAuth 로그인 |
| GET | `/api/v1/auth/callback` | Google OAuth 콜백 |
| POST | `/api/v1/auth/refresh` | JWT 토큰 갱신 |
| GET | `/api/v1/auth/me` | 현재 사용자 정보 |

### 문서 (Documents)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/documents` | 문서 목록 조회 (검색, 페이징, 정렬) |
| GET | `/api/v1/documents/{document_id}` | 문서 상세 조회 |
| GET | `/api/v1/documents/{document_id}/summary` | 문서 요약 조회 |

### 대화 (Conversations)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/conversations` | 신규 대화 생성 |
| GET | `/api/v1/conversations` | 대화 목록 조회 |
| GET | `/api/v1/conversations/{id}` | 대화 상세 조회 |
| GET | `/api/v1/conversations/{id}/messages` | 메시지 목록 조회 |
| POST | `/api/v1/conversations/{id}/messages` | 메시지 전송 및 AI 응답 |

### RAG (질의응답)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/rag/ask` | RAG 기반 질의응답 |

## 핵심 로직

### RAG 파이프라인 (LangGraph)

LangGraph StateGraph를 사용한 3단계 처리:

```
START → rag_retrieve → llm_generate → followup → END
```

#### 1. rag_retrieve (검색)
- 질문 임베딩 생성 (1536차원)
- pgvector 코사인 유사도 검색 (임계값 0.7)
- document_id 기반 문서 내 검색 또는 전체 검색
- 관련 청크 추출 및 컨텍스트 조합

#### 2. llm_generate (답변 생성)
- 사용자 레벨별 프롬프트 선택 (beginner/intermediate/advanced)
- Upstage Solar-Pro2 LLM 호출
- 대화 히스토리 포함 답변 생성

#### 3. followup (후속 질문)
- 사용자 레벨에 맞는 후속 질문 3개 생성
- 질문 + 답변 + 컨텍스트 기반

### 벡터 검색

**임베딩**: Sentence Transformers (sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja)
**검색**: pgvector 코사인 거리 연산 (<=> 연산자)
**전략**: 유사도 0.7 이상 → 청크 사용, 미만 → 일반 대화

### 대화 메모리

LangGraph PostgresSaver로 체크포인트 자동 관리:
- conversation_id를 thread_id로 사용
- 대화 상태 스냅샷 자동 저장/복원

### 레벨별 프롬프트

- **Beginner**: 쉬운 해설, 전문 용어 풀어서 설명, 비유 활용
- **Intermediate**: 핵심 요약, 구조화된 정보
- **Advanced**: 전문 분석, 심층 인사이트, 시장 맥락

---

**MoneyMong Backend** - 금융 지식의 민주화를 위한 AI 어시스턴트
