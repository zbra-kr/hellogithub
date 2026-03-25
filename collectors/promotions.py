# collectors/promotions.py - 무신사 이벤트/프로모션 수집기

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import COMPETITOR_BRANDS, OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT

try:
    from utils.browser import fetch_page as _pw_fetch
    _HAS_PW = True
except ImportError:
    _HAS_PW = False


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_ALL_BRAND_NAMES = [b["name"] for b in OWN_BRANDS] + [b["name"] for b in COMPETITOR_BRANDS]


def _check_brand_in_text(text: str) -> list[str]:
    return [name for name in _ALL_BRAND_NAMES if name in text]


def _get_html(url: str) -> str:
    if _HAS_PW:
        try:
            return _pw_fetch(
                url,
                wait_selector=(
                    "[class*='EventItem'],[class*='event-item'],"
                    "[class*='BannerItem'],[class*='MagazineItem'],article"
                ),
                timeout_ms=20000,
                extra_headers={"Referer": "https://www.musinsa.com/"},
            )
        except Exception:
            pass
    try:
        headers = {**REQUEST_HEADERS, "Referer": "https://www.musinsa.com/"}
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return ""


def _parse_promotions(html: str) -> list[dict]:
    results = []
    soup = BeautifulSoup(html, "html.parser")

    items = []
    for sel in [
        "[class*='EventItem']", "[class*='event-item']", ".event-list__item",
        "[class*='PromotionItem']", ".promotion-item", "li[class*='event']",
        "[class*='SaleItem']", "[class*='BannerItem']", "[class*='MagazineItem']",
        "article[class*='event']", "[class*='card']", ".magazine-item",
    ]:
        items = soup.select(sel)
        if items:
            break

    if not items:
        items = soup.select(
            "a[href*='/event/'],a[href*='/sale/'],a[href*='event'],a[href*='promotion'],a[href*='magazine']"
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

        related = _check_brand_in_text(item.get_text())
        results.append({
            "이벤트명": title, "할인율": discount,
            "시작일": start_date, "종료일": end_date,
            "관련브랜드": ", ".join(related) if related else "-",
            "링크": link, "수집시각": _now(),
        })
    return results


def collect_promotions(log_callback=None) -> list[dict]:
    all_results = []
    # 무신사 이벤트/매거진 URL 후보
    urls = [
        "https://www.musinsa.com/store/magazine",
        "https://www.musinsa.com/magazine",
        "https://www.musinsa.com/event",
        "https://www.musinsa.com/sale",
        "https://www.musinsa.com/store/event",
        "https://www.musinsa.com/promotion",
    ]
    seen = set()
    for url in urls:
        if log_callback:
            log_callback(f"[프로모션] {url} 수집 중... {'(Playwright)' if _HAS_PW else ''}")
        html = _get_html(url)
        if not html:
            if log_callback:
                log_callback(f"[프로모션] {url}: 응답 없음 스킵")
            continue
        items = _parse_promotions(html)
        new_items = [i for i in items if i["이벤트명"] not in seen]
        for i in new_items:
            seen.add(i["이벤트명"])
        all_results.extend(new_items)
        if log_callback:
            log_callback(f"[프로모션] {url}: {len(new_items)}건 수집")
        if len(all_results) >= 20:
            break

    all_results.sort(key=lambda x: (0 if x["관련브랜드"] != "-" else 1))
    if log_callback:
        log_callback(f"[프로모션] 전체 완료: {len(all_results)}건")
    return all_results
