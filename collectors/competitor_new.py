# collectors/competitor_new.py - 경쟁사 신상품 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import COMPETITOR_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT, COMPETITOR_NEW_LIMIT

try:
    from utils.browser import fetch_page as _pw_fetch
    _HAS_PW = True
except ImportError:
    _HAS_PW = False


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_html(url: str) -> str:
    if _HAS_PW:
        try:
            return _pw_fetch(
                url,
                wait_selector="[class*='GoodsItem'],[class*='goods-item'],li[class*='item']",
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


def _find_product_arrays(obj, depth=0) -> list:
    if depth > 8:
        return []
    if isinstance(obj, list) and len(obj) >= 2:
        first = obj[0]
        if isinstance(first, dict) and any(
            k in first for k in ("goodsName", "itemName", "name", "productName")
        ):
            return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = _find_product_arrays(v, depth + 1)
            if found:
                return found
    return []


def _parse_products(html: str, brand_name: str) -> list[dict]:
    results = []

    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*(.*?)\s*</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            items = _find_product_arrays(data)
            for item in items[:COMPETITOR_NEW_LIMIT]:
                name = (item.get("goodsName") or item.get("itemName") or
                        item.get("name") or item.get("productName") or "-")
                price = item.get("normalPrice") or item.get("price") or "-"
                goods_no = item.get("goodsNo") or item.get("id") or ""
                if str(name) != "-":
                    results.append({
                        "브랜드": brand_name, "상품명": str(name),
                        "가격": f"{int(price):,}원" if isinstance(price, (int, float)) else str(price),
                        "등록일": item.get("goodsDate", item.get("registDate", "-")),
                        "링크": f"https://www.musinsa.com/products/{goods_no}" if goods_no else "-",
                        "수집시각": _now(),
                    })
            if results:
                return results
        except Exception:
            pass

    soup = BeautifulSoup(html, "html.parser")
    for sel in [
        "[class*='GoodsItem']", "[class*='goods-item']", ".goods-list__item",
        "[class*='ProductItem']", "li[class*='item']",
    ]:
        els = soup.select(sel)
        if len(els) >= 2:
            for el in els[:COMPETITOR_NEW_LIMIT]:
                name_el = el.select_one("[class*='name'],[class*='title'],strong")
                price_el = el.select_one("[class*='price']")
                link_el = el.select_one("a[href]")
                name = name_el.get_text(strip=True) if name_el else "-"
                if name == "-":
                    continue
                results.append({
                    "브랜드": brand_name, "상품명": name,
                    "가격": re.sub(r"[^\d,원]", "", price_el.get_text()) if price_el else "-",
                    "등록일": "-",
                    "링크": link_el["href"] if link_el else "-",
                    "수집시각": _now(),
                })
            break
    return results


def collect_brand_new_products(brand: dict, log_callback=None) -> list[dict]:
    brand_name = brand["name"]
    musinsa_id = brand["musinsa_id"]

    urls = [
        f"https://www.musinsa.com/brands/{musinsa_id}/goods?sortCode=NEWEST",
        f"https://www.musinsa.com/brands/{musinsa_id}",
        # slug 오류 대비 — 브랜드명 검색 폴백
        f"https://www.musinsa.com/search/musinsa/goods?q={requests.utils.quote(brand_name)}&sortCode=NEWEST",
    ]

    for url in urls:
        html = _get_html(url)
        if html:
            r = _parse_products(html, brand_name)
            if r:
                return r
        # 404 여부 확인 (requests만 사용 시)
        if not _HAS_PW:
            try:
                resp = requests.get(url, headers=REQUEST_HEADERS, timeout=5, allow_redirects=True)
                if resp.status_code == 404:
                    continue
            except Exception:
                pass

    return []


def collect_competitor_new(log_callback=None) -> list[dict]:
    all_results = []
    for brand in COMPETITOR_BRANDS:
        if log_callback:
            log_callback(f"[경쟁사신상품] {brand['name']} 수집 중... {'(Playwright)' if _HAS_PW else ''}")
        items = collect_brand_new_products(brand, log_callback=log_callback)
        all_results.extend(items)
        if log_callback:
            log_callback(f"[경쟁사신상품] {brand['name']}: {len(items)}건")
    if log_callback:
        log_callback(f"[경쟁사신상품] 전체 완료: {len(all_results)}건")
    return all_results
