"""
Crawler API endpoints - "crawler_db.py".

crawler_db.crawl_multi_pages를 FastAPI와 연결
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.services import crawler_db

router = APIRouter(
    prefix="/crawler",
    tags=["crawler"],
)


@router.get(
    "/naver/reports",
    summary="Trigger naver analysts reports crawler",
    description="crawler_db.crawl_multi_pages 함수 돌림",
)
async def run_naver_report_crawler(
    mode: str = Query(
        default=crawler_db.MODE,
        pattern="^(DAILY|INIT)$",
        description="DAILY (기본) 또는 INIT(1년치 풀 수집)",
    )
):
    """
    Run the legacy crawler synchronously (delegated to a thread pool).
    """
    try:
        result = await run_in_threadpool(
            crawler_db.crawl_multi_pages, mode
        )
        return {
            "status": "completed",
            "mode": result["mode"],
            "cutoff_date": str(result["cutoff_date"]),
             "pdf_saved": result["pdf_saved"],
             "db_saved": result["db_saved"],
            "total_saved": result["total_saved"],
            "last_seen_date": str(result["last_seen_date"]) if result["last_seen_date"] else None,
        }
    except Exception as exc:  # pragma: no cover - simple passthrough
        raise HTTPException(status_code=500, detail=str(exc)) from exc
