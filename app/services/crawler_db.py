# -*- coding: utf-8 -*-
"""
Naver Finance 기업리포트
- 오늘(Asia/Seoul) 기준 하루치(오늘-1일 이후)만 저장
- 상세 페이지에서 a.con_link[href$=".pdf"] 추출
- 발행월(YYYY-MM) 폴더로 저장

- MODE = "INIT" -> 1년치 전체 수집
- MODE = "DAILY" -> 오늘 -1 이후만
- MODE = "RANGE" -> YYYY-MM-DD로 시작일 종료일 설정
    - 매일 자동 실행용
- 문서 단위 트랜잭션, DB 중복 확인

DB 연결에서 기입 필요
- DB_CONFIG

"""

import datetime as dt
import os
import re
import time
from io import BytesIO
from urllib.parse import parse_qs, urljoin, urlparse

import psycopg2
import requests
from bs4 import BeautifulSoup

from app.config import get_settings
from app.services.s3_client import get_s3_client


# ------------------- 설정 -------------------
MODE = "DAILY"  # 'INIT' or 'DAILY'
BASE = "https://finance.naver.com"
LIST_TPL = (
    "https://finance.naver.com/research/company_list.naver?page={page}"  # 풀페이지
)
OUT_DIR = "raw-documents"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
REFERER = "https://finance.naver.com/research/company_list.naver"
TIMEOUT = 30
SLEEP = 0.6
DEBUG_ONE = False  # True : 첫 문서에서 종료

# 하루치(오늘 - 1일 이후)
KST = dt.timezone(dt.timedelta(hours=9))

# -------------------DB 연결-----------------------
settings = get_settings()
s3_client = get_s3_client()
DB_CONFIG = {
    "host": settings.POSTGRES_HOST,
    "port": settings.POSTGRES_PORT,
    "dbname": settings.POSTGRES_DB,
    "user": settings.POSTGRES_USER,
    "password": settings.POSTGRES_PASSWORD,
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def resolve_crawl_window(run_mode: str, today: dt.date):
    """
    Return (start_date, end_date, max_page) for the requested mode.
    """
    run_mode = run_mode.upper()
    if run_mode == "INIT":
        return today - dt.timedelta(days=365), today, 2000
    if run_mode == "DAILY":
        return today - dt.timedelta(days=1), today, 500
    raise ValueError(f"Unsupported mode: {run_mode}")


def ensure_date(value, field: str):
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"{field} must be YYYY-MM-DD formatted") from exc
    raise ValueError(f"{field} must be a date or ISO date string")


def build_crawl_result(
    run_mode, today, cutoff_date, end_date, pdf_saved, db_saved, last_seen_date
):
    return {
        "mode": run_mode,
        "today": today,
        "cutoff_date": cutoff_date,
        "end_date": end_date,
        "pdf_saved": pdf_saved,
        "db_saved": db_saved,
        "total_saved": db_saved,  # backwards compatibility
        "last_seen_date": last_seen_date,
    }


# ------------------- 유틸 -------------------
def parse_date(text: str, today):
    text = (text or "").strip()
    for fmt in ("%y.%m.%d", "%y-%m-%d", "%y/%m/%d"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


# ------------------- 메인 로직 -------------------
def crawl_multi_pages(mode: str | None = None, start_date=None, end_date=None):
    today = dt.datetime.now(KST).date()
    run_mode = (mode or MODE).upper()

    if run_mode == "RANGE":
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required for RANGE mode")
        cutoff_date = ensure_date(start_date, "start_date")
        end_limit = ensure_date(end_date, "end_date")
        if cutoff_date > end_limit:
            raise ValueError("start_date cannot be later than end_date")
        max_page = 2000
        run_mode_label = f"RANGE:{cutoff_date}->{end_limit}"
    else:
        cutoff_date, end_limit, max_page = resolve_crawl_window(run_mode, today)
        run_mode_label = run_mode

    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": REFERER})
    pdf_saved = 0
    db_saved = 0
    page = 1
    last_seen_date = None

    while True:
        list_url = LIST_TPL.format(page=page)
        print(f"[INFO] 목록 요청: {list_url}")

        r = sess.get(list_url, timeout=TIMEOUT)
        if r.status_code != 200:
            print(f"[WARN] 페이지 응답 오류: {r.status_code}")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        box = soup.select_one("div.box_type_m") or soup
        rows = box.select("tr")

        if not rows:
            print("[INFO] 더 이상 행 없음. 종료")
            break

        # 이 페이지에 '수집 대상(=CUTOFF_DATE 이후)'이 있는지 표시
        page_has_target = False

        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            # 날짜
            date_td = tr.select_one("td.date")
            date_text = (
                date_td.get_text(strip=True)
                if date_td
                else tds[-1].get_text(strip=True)
            )
            pub_date = parse_date(
                date_text, today
            )  # ← 2자리 연도/월.일까지 처리하는 parse_date로
            if not pub_date:
                continue
            last_seen_date = pub_date

            # 컷오프 필터
            if pub_date > end_limit:
                continue
            if pub_date < cutoff_date:
                continue  # 이 행은 패스, 다른 행 확인(페이지 전체 종료 판단은 아래에서)
            page_has_target = True

            # 개별 리포트 글 링크(게시판 목록 상)
            report_post = tr.select_one('a[href*="company_read"]')
            if not report_post or not report_post.has_attr("href"):
                continue

            report_url = urljoin(
                r.url, report_post["href"].strip()
            )  # detail_url 예: ...company_read.naver?nid=87906&page=1
            parsed = urlparse(report_url)
            qs = parse_qs(parsed.query)
            nid = qs.get("nid", [None])[0]
            if not nid:
                print(f"[WARNING] nid 없음: {report_url}")
                continue
            title = report_post.get_text(strip=True)  # 리포트 제목

            # 개별 리포트 페이지 요청
            try:
                dr = sess.get(report_url, timeout=TIMEOUT)
                dr.raise_for_status()
            except Exception as e:
                print(f"[WARN] 개별 리포트 접근 실패: {report_url} | {e}")
                continue

            dsoup = BeautifulSoup(dr.text, "html.parser")

            ## 발행기관 이름 추출
            broker = None
            src = dsoup.select_one("p.source")
            if src:
                txt = src.get_text(strip=True)
                # 여러 구분자 제거: "대신증권|2025.11.12|조회 117" → "대신증권"
                broker = txt.split("|")[0].strip()
                # 증권으로 끝나는 발행기관 추출
                if not re.search(r"증권$", broker):
                    print(f"[SKIP] 증권사 아님: {broker}")
                    continue
            else:
                print(f"[INFO] source 없음: {report_url}")
                continue

            # DB 중복 확인
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM documents WHERE file_id=%s", (nid,))
                    exists = cur.fetchone()
                    if exists:
                        print(f"[SKIP] 이미 DB에 존재: {nid}")
                        continue

            ## pdf 링크 추출
            report_pdf = None
            # (1) .pdf 포함된 링크만 찾기 (.pdf가 query param 안에 있어도 통과)
            pdf_link = dsoup.find("a", href=lambda x: x and ".pdf" in x.lower())

            # (2) "원문" / "다운" 등의 텍스트 포함된 링크 찾기 (텍스트 직접 노드에 한정)
            text_link = None
            for a in dsoup.find_all("a"):
                text = a.get_text(strip=True)
                if any(k in text for k in ["원문", "다운", "리포트", "보기"]):
                    text_link = a
                    break

            # (3) 실제 최종 후보 결정 (.pdf 링크 우선)
            for candidate in [pdf_link, text_link]:
                if (
                    candidate
                    and candidate.has_attr("href")
                    and ".pdf" in candidate["href"].lower()
                ):
                    report_pdf = candidate
                    break

            if not report_pdf:
                print(
                    f"[INFO] PDF 없음: \n 제목: {title} \n 증권사: {broker} \n {report_url}"
                )
                continue

            pdf_url = urljoin(report_url, report_pdf["href"].strip())

            # pdf 링크 뒤의 숫자 id 추출
            m = re.search(r"(\d+)\.pdf", pdf_url)
            pdf_id = m.group(1) if m else "noid"  # pdf 링크 뒤의 숫자

            # if os.path.exists(out_path):
            #     print(f"[SKIP] 이미 존재: {out_path}")
            #     continue

            # PDF 다운로드
            ## 저장 경로 및 파일명 구성
            fname = f"{pub_date:%Y%m%d}_{nid}.pdf"
            s3_key = f"{OUT_DIR}/{fname}"
            s3_uri = f"s3://{settings.AWS_S3_BUCKET}/{s3_key}"

            try:
                with BytesIO() as pdf_buffer:
                    with sess.get(pdf_url, timeout=TIMEOUT, stream=True) as pr:
                        pr.raise_for_status()
                        for chunk in pr.iter_content(1024 * 64):
                            if chunk:
                                pdf_buffer.write(chunk)

                    file_size = pdf_buffer.tell()
                    pdf_buffer.seek(0)
                    s3_client.upload_fileobj(
                        pdf_buffer,
                        settings.AWS_S3_BUCKET,
                        s3_key,
                        ExtraArgs={"ContentType": "application/pdf"},
                    )
                pdf_saved += 1
                print(f"[S3 UPLOAD] {s3_uri}")
            except Exception as e:
                print(f"[WARN] PDF 실패: {pdf_url} | {e}")
                continue

            # DB 저장
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO documents(
                            source_type, source_url, source_nid, file_url, file_id, title, author, published_date,
                            file_path, file_size, total_pages
                         )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            "pdf",
                            report_url,
                            nid,
                            pdf_url,
                            nid,
                            title,
                            broker,
                            pub_date,
                            s3_uri,
                            file_size,
                            None,
                        ),
                    )
                conn.commit()
            print(f"DB 저장 완료 -> {nid}")
            db_saved += 1

            # 디버그용: 하나만 가져오고 종료
            if DEBUG_ONE:
                print("[INFO] DEBUG_ONE=True → 첫 문서까지만 처리 후 종료")
                return build_crawl_result(
                    run_mode_label,
                    today,
                    cutoff_date,
                    end_limit,
                    pdf_saved,
                    db_saved,
                    last_seen_date,
                )

            time.sleep(SLEEP)

        # 이 페이지에 대상이 하나도 없었다면(모두 cutoff 이전),
        # 이후 페이지는 더 오래된 글이므로 종료
        if not page_has_target:
            print("[INFO] 이 페이지에 신규 대상 없음(모두 컷오프 이전). 종료")
            break

        page += 1
        if page > max_page:  # 안전 가드
            print(f"[INFO] page>{max_page} 가드로 종료")
            break

    print(
        f"[DONE] 모드={run_mode_label} / 기준: {cutoff_date}~{end_limit} / "
        f"PDF 저장={pdf_saved}건 / DB 저장={db_saved}건"
    )
    return build_crawl_result(
        run_mode_label,
        today,
        cutoff_date,
        end_limit,
        pdf_saved,
        db_saved,
        last_seen_date,
    )


# if __name__ == "__main__":
#     print(f'[INFO] 수집 기준: {CUTOFF_DATE} ~ {TODAY}')
#     crawl_multi_pages()


# print(f"[INFO] 테스트 모드: 1페이지, 하루치만 수집 (기준: {CUTOFF_DATE} ~ {TODAY})")
# crawl_one_page_one_day()
