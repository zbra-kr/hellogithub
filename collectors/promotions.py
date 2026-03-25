# collectors/promotions.py - 무신사 이벤트/프로모션 수집기

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import COMPETITOR_BRANDS, OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_ALL_BRAND_NAMES = (
    [b["name"] for b in OWN_BRANDS] +
    [b["name"] for b in COMPETITOR_BRANDS]
)


def _check_brand_in_text(text: str) -> list[str]:
    """텍스트에서 관련 브랜드명 탐색"""
    found = []
    for name in _ALL_BRAND_NAMES:
        if name in text:
            found.append(name)
    return found


def _parse_promotions_from_html(html: str, source_url: str) -> list[dict]:
    """이벤트 페이지 HTML에서 프로모션 항목 파싱"""
    results = []
    soup = BeautifulSoup(html, "html.parser")

    # 다양한 이벤트 카드/리스트 셀렉터 시도
    selectors = [
        ".event-list__item",
        "[class*='EventItem']",
        "[class*='event-item']",
        ".promotion-item",
        "[class*='PromotionItem']",
        "li[class*='event']",
        ".sale-item",
        "[class*='SaleItem']",
    ]
    items = []
    for sel in selectors:
        items = soup.select(sel)
        if items:
            break

    # 폴백: 이벤트 링크가 있는 카드 탐색
    if not items:
        items = soup.select("a[href*='/event/'], a[href*='/sale/'], a[href*='event']")

    for item in items[:20]:
        title_el = item.select_one(
            "[class*='title'], [class*='name'], h2, h3, h4, strong"
        )
        date_el = item.select_one("[class*='date'], [class*='period'], time")
        discount_el = item.select_one("[class*='discount'], [class*='sale'], [class*='rate']")
        link_el = item if item.name == "a" else item.select_one("a[href]")

        title = title_el.get_text(strip=True) if title_el else item.get_text(strip=True)[:60]
        if not title:
            continue

        date_text = date_el.get_text(strip=True) if date_el else "-"
        # 날짜 분리 시도
        date_parts = re.split(r"[~\-–]", date_text)
        start_date = date_parts[0].strip() if date_parts else "-"
        end_date = date_parts[1].strip() if len(date_parts) > 1 else "-"

        discount = discount_el.get_text(strip=True) if discount_el else "-"
        link = link_el.get("href", "-") if link_el else "-"
        if link and link.startswith("/"):
            link = "https://www.musinsa.com" + link

        text_content = item.get_text()
        related_brands = _check_brand_in_text(text_content)

        results.append({
            "이벤트명": title,
            "할인율": discount,
            "시작일": start_date,
            "종료일": end_date,
            "관련브랜드": ", ".join(related_brands) if related_brands else "-",
            "링크": link,
            "수집시각": _now(),
        })

    return results


def collect_promotions(log_callback=None) -> list[dict]:
    """무신사 이벤트/프로모션 페이지 수집"""
    all_results = []
    urls = [
        "https://www.musinsa.com/event/",
        "https://www.musinsa.com/sale/",
        "https://www.musinsa.com/promotions/",
    ]

    for url in urls:
        if log_callback:
            log_callback(f"[프로모션] {url} 수집 중...")
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            items = _parse_promotions_from_html(resp.text, url)
            # 중복 이벤트명 제거
            existing_titles = {r["이벤트명"] for r in all_results}
            new_items = [i for i in items if i["이벤트명"] not in existing_titles]
            all_results.extend(new_items)
            if log_callback:
                log_callback(f"[프로모션] {url}: {len(new_items)}건 수집")
        except Exception as e:
            if log_callback:
                log_callback(f"[프로모션] {url} 오류: {e}")

    # 관련 브랜드가 있는 항목 우선 정렬
    all_results.sort(key=lambda x: (0 if x["관련브랜드"] != "-" else 1))

    if log_callback:
        log_callback(f"[프로모션] 전체 완료: {len(all_results)}건")
    return all_results


if __name__ == "__main__":
    data = collect_promotions(log_callback=print)
    for row in data[:5]:
        print(row)
