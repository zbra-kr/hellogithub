# collectors/promotions.py - 무신사 이벤트/프로모션 수집기

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import COMPETITOR_BRANDS, OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_ALL_BRAND_NAMES = [b["name"] for b in OWN_BRANDS] + [b["name"] for b in COMPETITOR_BRANDS]


def _check_brand_in_text(text: str) -> list[str]:
    return [name for name in _ALL_BRAND_NAMES if name in text]


def _parse_promotions(html: str) -> list[dict]:
    results = []
    soup = BeautifulSoup(html, "html.parser")

    # 이벤트 카드/리스트 셀렉터 (다양하게 시도)
    items = []
    for sel in [
        ".event-list__item", "[class*='EventItem']", "[class*='event-item']",
        ".promotion-item", "[class*='PromotionItem']", "li[class*='event']",
        ".sale-item", "[class*='SaleItem']", "[class*='BannerItem']",
        "article[class*='event']", ".magazine-item", "[class*='MagazineItem']",
        "li.item", "[class*='card']",
    ]:
        items = soup.select(sel)
        if items:
            break

    # 폴백: 이벤트/세일 링크 수집
    if not items:
        items = soup.select(
            "a[href*='/event/'], a[href*='/sale/'], "
            "a[href*='event'], a[href*='promotion'], a[href*='magazine']"
        )

    for item in items[:30]:
        title_el = item.select_one("[class*='title'],[class*='name'],h2,h3,h4,strong,p")
        date_el = item.select_one("[class*='date'],[class*='period'],time")
        discount_el = item.select_one("[class*='discount'],[class*='sale'],[class*='rate']")
        link_el = item if item.name == "a" else item.select_one("a[href]")

        title = title_el.get_text(strip=True) if title_el else item.get_text(strip=True)[:80]
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 4:
            continue

        date_text = date_el.get_text(strip=True) if date_el else "-"
        parts = re.split(r"[~\-–]", date_text)
        start_date = parts[0].strip() if parts else "-"
        end_date = parts[1].strip() if len(parts) > 1 else "-"

        discount = discount_el.get_text(strip=True) if discount_el else "-"
        link = link_el.get("href", "-") if link_el else "-"
        if link and link.startswith("/"):
            link = "https://www.musinsa.com" + link

        related_brands = _check_brand_in_text(item.get_text())
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
    all_results = []
    headers = {**REQUEST_HEADERS, "Referer": "https://www.musinsa.com/"}

    # 무신사 이벤트/프로모션 URL 후보 (변경된 URL 구조 반영)
    urls = [
        "https://www.musinsa.com/store/magazine",
        "https://www.musinsa.com/magazine",
        "https://www.musinsa.com/event",
        "https://www.musinsa.com/sale",
        "https://www.musinsa.com/store/event",
        "https://www.musinsa.com/promotion",
    ]

    seen_titles = set()
    for url in urls:
        if log_callback:
            log_callback(f"[프로모션] {url} 수집 중...")
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if resp.status_code in (404, 410):
                if log_callback:
                    log_callback(f"[프로모션] {url}: 404 스킵")
                continue
            resp.raise_for_status()
            items = _parse_promotions(resp.text)
            new_items = [i for i in items if i["이벤트명"] not in seen_titles]
            for i in new_items:
                seen_titles.add(i["이벤트명"])
            all_results.extend(new_items)
            if log_callback:
                log_callback(f"[프로모션] {url}: {len(new_items)}건 수집")
            if len(all_results) >= 20:
                break
        except Exception as e:
            if log_callback:
                log_callback(f"[프로모션] {url} 오류: {e}")

    # 관련 브랜드 있는 항목 우선
    all_results.sort(key=lambda x: (0 if x["관련브랜드"] != "-" else 1))
    if log_callback:
        log_callback(f"[프로모션] 전체 완료: {len(all_results)}건")
    return all_results
