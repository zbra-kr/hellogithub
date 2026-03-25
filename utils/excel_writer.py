# utils/excel_writer.py - 패션 브랜드 모니터링 엑셀 저장 모듈

import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from config import OUTPUT_DIR


# ─────────────────────────────────────────
# 색상 정의 (다크/미니멀 패션 브랜드 톤)
# ─────────────────────────────────────────
C_HEADER_BG = "1C1C1C"       # 거의 검정 - 헤더 배경
C_HEADER_FG = "F5F5F5"       # 거의 흰색 - 헤더 텍스트
C_TITLE_BG = "2D2D2D"        # 다크 그레이 - 시트 타이틀
C_ACCENT = "E8C56D"          # 골드 - 강조색
C_ROW_EVEN = "F7F7F7"        # 연한 그레이 - 짝수행
C_ROW_ODD = "FFFFFF"         # 흰색 - 홀수행
C_UNANSWERED = "FFE0E0"      # 연한 빨강 - 미답변 강조
C_SUMMARY_BG = "141414"      # 요약 시트 배경


def _hf(bold=True, size=10, color=C_HEADER_FG):
    return Font(name="맑은 고딕", bold=bold, size=size, color=color)


def _bf(size=9, color="333333"):
    return Font(name="맑은 고딕", size=size, color=color)


def _border():
    s = Side(style="thin", color="DDDDDD")
    return Border(left=s, right=s, top=s, bottom=s)


def _center(wrap=True):
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)


def _left(wrap=True):
    return Alignment(horizontal="left", vertical="center", wrap_text=wrap)


def _fill(hex_color: str) -> PatternFill:
    return PatternFill(fill_type="solid", fgColor=hex_color)


def _write_header(ws, row: int, headers: list[str], widths: list[float], bg=C_HEADER_BG):
    for col, (h, w) in enumerate(zip(headers, widths), start=1):
        cell = ws.cell(row=row, column=col, value=h)
        cell.font = _hf()
        cell.fill = _fill(bg)
        cell.alignment = _center()
        cell.border = _border()
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.row_dimensions[row].height = 20


def _write_row(ws, row: int, values: list, even: bool, row_height=18, highlight_color=None):
    bg = highlight_color if highlight_color else (C_ROW_EVEN if even else C_ROW_ODD)
    for col, val in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.font = _bf()
        cell.fill = _fill(bg)
        cell.alignment = _left() if col > 2 else _center()
        cell.border = _border()
    ws.row_dimensions[row].height = row_height


def _sheet_title(ws, title: str, col_count: int, row=1):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_count)
    cell = ws.cell(row=row, column=1, value=title)
    cell.font = Font(name="맑은 고딕", bold=True, size=13, color=C_ACCENT)
    cell.fill = _fill(C_TITLE_BG)
    cell.alignment = _center()
    cell.border = _border()
    ws.row_dimensions[row].height = 28


# ─────────────────────────────────────────
# 개별 시트 작성 함수
# ─────────────────────────────────────────

def _write_summary_sheet(ws, now: datetime, counts: dict):
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20

    _sheet_title(ws, f"패션 브랜드 모니터링 RPA  |  {now.strftime('%Y년 %m월 %d일 %H:%M')} 기준", 2)
    ws.append([""])
    _write_header(ws, 3, ["수집 항목", "수집 건수"], [30, 20])
    items = [
        ("베스트셀러", counts.get("bestseller", 0)),
        ("트렌드 해시태그", counts.get("sns_trend", 0)),
        ("해외 패션 뉴스", counts.get("global_fashion", 0)),
        ("경쟁사 신상품", counts.get("competitor_new", 0)),
        ("가격 비교", counts.get("price_compare", 0)),
        ("프로모션", counts.get("promotions", 0)),
        ("리뷰/별점", counts.get("reviews", 0)),
        ("SNS 멘션", counts.get("sns_mention", 0)),
        ("고객 문의", counts.get("inquiries", 0)),
    ]
    for i, (label, count) in enumerate(items, start=4):
        ws.cell(row=i, column=1, value=label).font = _bf(size=10)
        ws.cell(row=i, column=1).fill = _fill(C_ROW_EVEN if i % 2 == 0 else C_ROW_ODD)
        ws.cell(row=i, column=1).border = _border()
        ws.cell(row=i, column=1).alignment = _left()
        ws.cell(row=i, column=2, value=f"{count}건").font = _bf(size=10)
        ws.cell(row=i, column=2).fill = _fill(C_ROW_EVEN if i % 2 == 0 else C_ROW_ODD)
        ws.cell(row=i, column=2).border = _border()
        ws.cell(row=i, column=2).alignment = _center()
        ws.row_dimensions[i].height = 20


def _write_bestseller_sheet(ws, data: list[dict]):
    headers = ["순위", "플랫폼", "브랜드", "상품명", "가격", "할인율", "링크", "수집시각"]
    widths =  [8,      16,      16,      40,      14,    10,     40,    18]
    _sheet_title(ws, "베스트셀러 순위", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        vals = [
            row.get("순위", "-"), row.get("플랫폼", "-"), row.get("브랜드", "-"),
            row.get("상품명", "-"), row.get("가격", "-"), row.get("할인율", "-"),
            row.get("링크", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


def _write_sns_trend_sheet(ws, data: list[dict]):
    headers = ["플랫폼", "해시태그", "게시물수", "조회수", "메모", "수집시각"]
    widths =  [14,      20,         18,         18,    30,     18]
    _sheet_title(ws, "트렌드 해시태그", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        vals = [
            row.get("플랫폼", "-"), row.get("해시태그", "-"),
            row.get("게시물수", "-"), row.get("조회수", "-"),
            row.get("메모", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


def _write_global_fashion_sheet(ws, data: list[dict]):
    headers = ["출처", "제목", "링크", "발행일", "요약", "수집시각"]
    widths =  [14,    44,     40,     18,    60,     18]
    _sheet_title(ws, "해외 패션 뉴스", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        vals = [
            row.get("출처", "-"), row.get("제목", "-"), row.get("링크", "-"),
            row.get("발행일", "-"), row.get("요약", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0, row_height=40)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


def _write_competitor_new_sheet(ws, data: list[dict]):
    headers = ["브랜드", "상품명", "가격", "등록일", "링크", "수집시각"]
    widths =  [16,      40,      14,    14,    40,    18]
    _sheet_title(ws, "경쟁사 신상품", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        vals = [
            row.get("브랜드", "-"), row.get("상품명", "-"), row.get("가격", "-"),
            row.get("등록일", "-"), row.get("링크", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


def _write_price_compare_sheet(ws, data: list[dict]):
    headers = ["복종", "브랜드", "브랜드유형", "평균가", "최저가", "최고가", "상품수", "수집시각"]
    widths =  [14,    18,       12,           14,     14,     14,     10,     18]
    _sheet_title(ws, "가격 비교 (복종별)", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        vals = [
            row.get("복종", "-"), row.get("브랜드", "-"), row.get("브랜드유형", "-"),
            row.get("평균가", "-"), row.get("최저가", "-"), row.get("최고가", "-"),
            row.get("상품수", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


def _write_promotions_sheet(ws, data: list[dict]):
    headers = ["이벤트명", "할인율", "시작일", "종료일", "관련브랜드", "링크", "수집시각"]
    widths =  [40,        12,      14,     14,    24,       40,   18]
    _sheet_title(ws, "할인 프로모션", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        vals = [
            row.get("이벤트명", "-"), row.get("할인율", "-"),
            row.get("시작일", "-"), row.get("종료일", "-"),
            row.get("관련브랜드", "-"), row.get("링크", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


def _write_reviews_sheet(ws, data: list[dict]):
    headers = ["플랫폼", "브랜드", "상품명", "별점", "리뷰내용", "작성일", "수집시각"]
    widths =  [14,      16,      36,      8,    60,      14,    18]
    _sheet_title(ws, "리뷰/별점 분석", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        vals = [
            row.get("플랫폼", "-"), row.get("브랜드", "-"), row.get("상품명", "-"),
            row.get("별점", "-"), row.get("리뷰내용", "-"),
            row.get("작성일", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0, row_height=40)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


def _write_sns_mention_sheet(ws, data: list[dict]):
    headers = ["브랜드", "해시태그", "총게시물수", "최근24h추정", "메모", "수집시각"]
    widths =  [16,      24,         18,            16,         30,   18]
    _sheet_title(ws, "SNS 멘션", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        vals = [
            row.get("브랜드", "-"), row.get("해시태그", "-"),
            row.get("총게시물수", "-"), row.get("최근24h추정", "-"),
            row.get("메모", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


def _write_inquiries_sheet(ws, data: list[dict]):
    headers = ["플랫폼", "브랜드", "상품명", "질문", "답변여부", "답변내용", "작성일", "수집시각"]
    widths =  [14,      16,      30,     50,   10,       50,     14,    18]
    _sheet_title(ws, "고객 문의 (Q&A)", len(headers))
    _write_header(ws, 2, headers, widths)
    for i, row in enumerate(data, start=3):
        answered = row.get("답변여부", "") == "답변완료"
        highlight = None if answered else C_UNANSWERED
        vals = [
            row.get("플랫폼", "-"), row.get("브랜드", "-"), row.get("상품명", "-"),
            row.get("질문", "-"), row.get("답변여부", "-"), row.get("답변내용", "-"),
            row.get("작성일", "-"), row.get("수집시각", "-"),
        ]
        _write_row(ws, i, vals, i % 2 == 0, row_height=40, highlight_color=highlight)
    if not data:
        ws.cell(row=3, column=1, value="수집된 데이터 없음").font = _bf()


# ─────────────────────────────────────────
# 메인 저장 함수
# ─────────────────────────────────────────

def save_to_excel(
    bestseller: list[dict] = None,
    sns_trend: list[dict] = None,
    global_fashion: list[dict] = None,
    competitor_new: list[dict] = None,
    price_compare: list[dict] = None,
    promotions: list[dict] = None,
    reviews: list[dict] = None,
    sns_mention: list[dict] = None,
    inquiries: list[dict] = None,
    log_callback=None,
) -> str:
    """
    8개 수집 데이터를 각각 별도 시트로 저장하는 엑셀 파일 생성.

    Returns:
        str: 저장된 파일 경로
    """
    bestseller = bestseller or []
    sns_trend = sns_trend or []
    global_fashion = global_fashion or []
    competitor_new = competitor_new or []
    price_compare = price_compare or []
    promotions = promotions or []
    reviews = reviews or []
    sns_mention = sns_mention or []
    inquiries = inquiries or []

    now = datetime.now()
    filename = f"패션모니터링_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(OUTPUT_DIR, filename)

    wb = Workbook()

    # 시트 순서대로 생성
    sheet_defs = [
        ("요약",        None),
        ("베스트셀러",  bestseller),
        ("트렌드해시태그", sns_trend),
        ("해외패션뉴스", global_fashion),
        ("경쟁사신상품", competitor_new),
        ("가격비교",    price_compare),
        ("프로모션",    promotions),
        ("리뷰분석",    reviews),
        ("SNS멘션",     sns_mention),
        ("고객문의",    inquiries),
    ]

    ws_summary = wb.active
    ws_summary.title = "요약"

    extra_sheets = []
    for title, _ in sheet_defs[1:]:
        ws = wb.create_sheet(title=title)
        extra_sheets.append(ws)

    counts = {
        "bestseller": len(bestseller),
        "sns_trend": len(sns_trend),
        "global_fashion": len(global_fashion),
        "competitor_new": len(competitor_new),
        "price_compare": len(price_compare),
        "promotions": len(promotions),
        "reviews": len(reviews),
        "sns_mention": len(sns_mention),
        "inquiries": len(inquiries),
    }

    _write_summary_sheet(ws_summary, now, counts)
    _write_bestseller_sheet(extra_sheets[0], bestseller)
    _write_sns_trend_sheet(extra_sheets[1], sns_trend)
    _write_global_fashion_sheet(extra_sheets[2], global_fashion)
    _write_competitor_new_sheet(extra_sheets[3], competitor_new)
    _write_price_compare_sheet(extra_sheets[4], price_compare)
    _write_promotions_sheet(extra_sheets[5], promotions)
    _write_reviews_sheet(extra_sheets[6], reviews)
    _write_sns_mention_sheet(extra_sheets[7], sns_mention)
    _write_inquiries_sheet(extra_sheets[8], inquiries)

    wb.save(filepath)

    if log_callback:
        log_callback(f"[저장] 엑셀 파일 저장 완료: {filepath}")

    return filepath
