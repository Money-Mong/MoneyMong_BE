"""
Crawler API endpoints - "crawler_db.py".
"""

from datetime import date

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
        default="DAILY",
        pattern="^(DAILY|INIT|RANGE)$",
        description="DAILY/INIT 고정 모드 또는 RANGE(날짜 범위 지정)",
    ),
    start_date: date | None = Query(
        default=None,
        description="수집 시작일 (YYYY-MM-DD). 지정 시 end_date도 필수",
    ),
    end_date: date | None = Query(
        default=None,
        description="수집 종료일 (YYYY-MM-DD). 지정 시 start_date도 필수",
    ),
):
    """
    Run the crawler synchronously (delegated to a thread pool).
    """
    if mode.upper() != "RANGE":
        if start_date or end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date/end_date는 RANGE 모드에서만 사용할 수 있습니다.",
            )
        start_arg = None
        end_arg = None
    else:
        if not start_date or not end_date:
            raise HTTPException(
                status_code=400,
                detail="RANGE 모드에는 start_date와 end_date가 모두 필요합니다.",
            )
        start_arg = start_date
        end_arg = end_date

    mode_arg = mode.upper()

    try:
        result = await run_in_threadpool(
            crawler_db.crawl_multi_pages, mode_arg, start_arg, end_arg
        )
        return {
            "status": "completed",
            "mode": result["mode"],
            "cutoff_date": str(result["cutoff_date"]),
            "end_date": str(result["end_date"]),
            "pdf_saved": result["pdf_saved"],
            "db_saved": result["db_saved"],
            "total_saved": result["total_saved"],
            "last_seen_date": str(result["last_seen_date"])
            if result["last_seen_date"]
            else None,
        }
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - simple passthrough
        raise HTTPException(status_code=500, detail=str(exc)) from exc
