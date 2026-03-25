# utils/excel_writer.py - 엑셀 저장 모듈

import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter
from config import OUTPUT_DIR


# 색상 정의
COLOR_HEADER_AI_NEWS = "1F4E79"      # 진한 파랑 - AI뉴스 헤더
COLOR_HEADER_WEATHER = "1E6B3C"      # 진한 초록 - 날씨 헤더
COLOR_HEADER_WORLD = "7B2D00"        # 진한 갈색 - 세계뉴스 헤더
COLOR_SECTION_TITLE = "2E75B6"       # 섹션 제목 파랑
COLOR_ROW_EVEN = "EBF3FB"            # 짝수행 배경
COLOR_ROW_ODD = "FFFFFF"             # 홀수행 배경 (흰색)
COLOR_WEATHER_ROW_EVEN = "E8F5E9"    # 날씨 짝수행
COLOR_WORLD_ROW_EVEN = "FFF3E0"      # 세계뉴스 짝수행


def _header_font(color="FFFFFF"):
    return Font(name="맑은 고딕", bold=True, color=color, size=10)


def _body_font():
    return Font(name="맑은 고딕", size=9)


def _thin_border():
    thin = Side(style="thin", color="CCCCCC")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _center():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)


def _left():
    return Alignment(horizontal="left", vertical="center", wrap_text=True)


def _set_header_row(ws, row, headers, col_widths, bg_color):
    """헤더 행 스타일 적용"""
    fill = PatternFill(fill_type="solid", fgColor=bg_color)
    for col_idx, (header, width) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.font = _header_font()
        cell.fill = fill
        cell.alignment = _center()
        cell.border = _thin_border()
        ws.column_dimensions[get_column_letter(col_idx)].width = width


def _section_title(ws, row, col, title, merge_to_col, color=COLOR_SECTION_TITLE):
    """섹션 타이틀 행"""
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=merge_to_col)
    cell = ws.cell(row=row, column=col, value=title)
    cell.font = Font(name="맑은 고딕", bold=True, color="FFFFFF", size=11)
    cell.fill = PatternFill(fill_type="solid", fgColor=color)
    cell.alignment = _center()
    cell.border = _thin_border()
    ws.row_dimensions[row].height = 22


def save_to_excel(
    korean_news: list[dict],
    weather_data: list[dict],
    world_news: list[dict],
    log_callback=None
) -> str:
    """
    수집된 데이터를 엑셀 파일로 저장합니다.

    Returns:
        str: 저장된 파일 경로
    """
    now = datetime.now()
    filename = f"일일리포트_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(OUTPUT_DIR, filename)

    wb = Workbook()
    ws = wb.active
    ws.title = "일일 리포트"

    # 페이지 여백 설정
    ws.sheet_view.showGridLines = True
    ws.column_dimensions["A"].width = 6

    current_row = 1

    # ─────────────────────────────────────────
    # 최상단 리포트 타이틀
    # ─────────────────────────────────────────
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
    title_cell = ws.cell(row=current_row, column=1,
                         value=f"📋 일일 AI·날씨·뉴스 리포트  |  {now.strftime('%Y년 %m월 %d일 %H:%M')} 기준")
    title_cell.font = Font(name="맑은 고딕", bold=True, color="FFFFFF", size=14)
    title_cell.fill = PatternFill(fill_type="solid", fgColor="1A1A2E")
    title_cell.alignment = _center()
    ws.row_dimensions[current_row].height = 30
    current_row += 2

    # ─────────────────────────────────────────
    # 섹션 1: 날씨
    # ─────────────────────────────────────────
    _section_title(ws, current_row, 1, "🌤 오늘의 날씨", 6, COLOR_HEADER_WEATHER)
    current_row += 1

    weather_headers = ["도시", "현재기온", "체감기온", "최고/최저", "날씨상태", "습도/풍속"]
    weather_widths = [12, 12, 12, 18, 18, 20]
    _set_header_row(ws, current_row, weather_headers, weather_widths, COLOR_HEADER_WEATHER)
    current_row += 1

    for i, w in enumerate(weather_data):
        bg = COLOR_WEATHER_ROW_EVEN if i % 2 == 0 else COLOR_ROW_ODD
        fill = PatternFill(fill_type="solid", fgColor=bg)
        values = [
            w.get("도시", "-"),
            w.get("현재기온", "-"),
            w.get("체감기온", "-"),
            f"{w.get('최고기온', '-')} / {w.get('최저기온', '-')}",
            w.get("날씨상태", "-"),
            f"습도 {w.get('습도', '-')}  바람 {w.get('풍향', '-')} {w.get('풍속', '-')}",
        ]
        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = _body_font()
            cell.fill = fill
            cell.alignment = _center()
            cell.border = _thin_border()
        ws.row_dimensions[current_row].height = 18
        current_row += 1

    current_row += 1

    # ─────────────────────────────────────────
    # 섹션 2: 한국 AI 뉴스
    # ─────────────────────────────────────────
    _section_title(ws, current_row, 1, "🤖 한국 AI 주요 뉴스", 6, COLOR_HEADER_AI_NEWS)
    current_row += 1

    ai_headers = ["No.", "출처", "제목", "발행일", "요약", "링크"]
    ai_widths = [6, 14, 40, 16, 50, 40]
    _set_header_row(ws, current_row, ai_headers, ai_widths, COLOR_HEADER_AI_NEWS)
    current_row += 1

    for i, news in enumerate(korean_news, start=1):
        bg = COLOR_ROW_EVEN if i % 2 == 0 else COLOR_ROW_ODD
        fill = PatternFill(fill_type="solid", fgColor=bg)
        values = [
            i,
            news.get("출처", "-"),
            news.get("제목", "-"),
            news.get("발행일", "-"),
            news.get("요약", "-"),
            news.get("링크", "-"),
        ]
        alignments = [_center(), _center(), _left(), _center(), _left(), _left()]
        for col_idx, (val, align) in enumerate(zip(values, alignments), start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = _body_font()
            cell.fill = fill
            cell.alignment = align
            cell.border = _thin_border()
        ws.row_dimensions[current_row].height = 45
        current_row += 1

    if not korean_news:
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
        cell = ws.cell(row=current_row, column=1, value="수집된 AI 뉴스가 없습니다.")
        cell.alignment = _center()
        current_row += 1

    current_row += 1

    # ─────────────────────────────────────────
    # 섹션 3: 세계 주요 뉴스 (Top 5)
    # ─────────────────────────────────────────
    _section_title(ws, current_row, 1, "🌍 세계 주요 뉴스 Top 5", 6, COLOR_HEADER_WORLD)
    current_row += 1

    world_headers = ["No.", "출처", "제목", "발행일", "요약", "링크"]
    world_widths = [6, 14, 40, 16, 50, 40]
    _set_header_row(ws, current_row, world_headers, world_widths, COLOR_HEADER_WORLD)
    current_row += 1

    for i, news in enumerate(world_news, start=1):
        bg = COLOR_WORLD_ROW_EVEN if i % 2 == 0 else COLOR_ROW_ODD
        fill = PatternFill(fill_type="solid", fgColor=bg)
        values = [
            i,
            news.get("출처", "-"),
            news.get("제목", "-"),
            news.get("발행일", "-"),
            news.get("요약", "-"),
            news.get("링크", "-"),
        ]
        alignments = [_center(), _center(), _left(), _center(), _left(), _left()]
        for col_idx, (val, align) in enumerate(zip(values, alignments), start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = _body_font()
            cell.fill = fill
            cell.alignment = align
            cell.border = _thin_border()
        ws.row_dimensions[current_row].height = 45
        current_row += 1

    if not world_news:
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
        cell = ws.cell(row=current_row, column=1, value="수집된 세계 뉴스가 없습니다.")
        cell.alignment = _center()
        current_row += 1

    # 푸터
    current_row += 1
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
    footer = ws.cell(row=current_row, column=1,
                     value=f"자동 생성: {now.strftime('%Y-%m-%d %H:%M:%S')}  |  RPA 일일 리포트 시스템")
    footer.font = Font(name="맑은 고딕", italic=True, color="888888", size=8)
    footer.alignment = _center()

    wb.save(filepath)

    if log_callback:
        log_callback(f"[저장] 파일 저장 완료: {filepath}")

    return filepath
