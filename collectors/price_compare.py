# collectors/price_compare.py - 가격 비교 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import (
    OWN_BRANDS, COMPETITOR_BRANDS, MUSINSA_CATEGORIES,
    REQUEST_HEADERS, REQUEST_TIMEOUT, PRICE_COMPARE_LIMIT,
)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _find_product_arrays(obj, depth=0) -> list:
    if depth > 8:
        return []
    if isinstance(obj, list) and len(obj) >= 2:
        first = obj[0]
        if isinstance(first, dict) and any(
            k in first for k in ("goodsName", "itemName", "name", "brandName")
        ):
            return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = _find_product_arrays(v, depth + 1)
            if found:
                return found
    return []


def _extract_price_int(val) -> int | None:
    if isinstance(val, (int, float)) and val > 0:
        return int(val)
    if isinstance(val, str):
        digits = re.sub(r"[^\d]", "", val)
        return int(digits) if digits else None
    return None


def _collect_category_prices(category: dict, log_callback=None) -> list[dict]:
    cat_name = category["name"]
    cat_code = category["code"]
    headers = {**REQUEST_HEADERS, "Referer": "https://www.musinsa.com/"}

    # 카테고리 URL 후보 — 파라미터명이 바뀐 경우 대비
    urls = [
        f"https://www.musinsa.com/ranking/best?categorySub={cat_code}",
        f"https://www.musinsa.com/ranking/best?category={cat_code}",
        f"https://www.musinsa.com/category/{cat_code}?sortCode=POPULAR",
        f"https://www.musinsa.com/search/musinsa/goods?q={requests.utils.quote(cat_name)}&sortCode=POPULAR",
    ]

    own_names = {b["name"] for b in OWN_BRANDS}
    comp_names = {b["name"] for b in COMPETITOR_BRANDS}
    brand_prices: dict[str, list[int]] = {}

    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if resp.status_code in (404, 410):
                continue
            resp.raise_for_status()

            # __NEXT_DATA__ 파싱
            m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*(.*?)\s*</script>', resp.text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    items = _find_product_arrays(data)
                    for item in items[:PRICE_COMPARE_LIMIT]:
                        b_name = (
                            item.get("brandName") or
                            (item.get("brand", {}).get("name") if isinstance(item.get("brand"), dict) else None) or ""
                        )
                        price = _extract_price_int(
                            item.get("normalPrice") or item.get("price") or item.get("salePrice")
                        )
                        if b_name and price:
                            brand_prices.setdefault(b_name, []).append(price)
                except Exception:
                    pass

            # BeautifulSoup 폴백
            if not brand_prices:
                soup = BeautifulSoup(resp.text, "html.parser")
                for sel in [
                    ".ranking-list__item", ".goods-list__item",
                    "[class*='RankingItem']", "li[class*='list-item']",
                    "[class*='GoodsItem']",
                ]:
                    els = soup.select(sel)
                    if len(els) >= 3:
                        for el in els[:PRICE_COMPARE_LIMIT]:
                            brand_el = el.select_one("[class*='brand']")
                            price_el = el.select_one("[class*='price']")
                            if brand_el and price_el:
                                b_name = brand_el.get_text(strip=True)
                                price = _extract_price_int(price_el.get_text())
                                if b_name and price:
                                    brand_prices.setdefault(b_name, []).append(price)
                        break

            if brand_prices:
                break  # 데이터 수집 성공 시 다음 URL 시도 불필요

        except Exception as e:
            if log_callback:
                log_callback(f"[가격비교] {cat_name} 오류({url}): {e}")

    results = []
    for b_name, prices in brand_prices.items():
        if not prices:
            continue
        b_type = "자사" if b_name in own_names else ("경쟁사" if b_name in comp_names else "기타")
        results.append({
            "복종": cat_name,
            "브랜드": b_name,
            "브랜드유형": b_type,
            "평균가": f"{int(sum(prices) / len(prices)):,}원",
            "최저가": f"{min(prices):,}원",
            "최고가": f"{max(prices):,}원",
            "상품수": len(prices),
            "수집시각": _now(),
        })
    return results


def collect_price_compare(log_callback=None) -> list[dict]:
    all_results = []
    for category in MUSINSA_CATEGORIES:
        if log_callback:
            log_callback(f"[가격비교] {category['name']} 카테고리 수집 중...")
        items = _collect_category_prices(category, log_callback=log_callback)
        all_results.extend(items)
        if log_callback:
            log_callback(f"[가격비교] {category['name']}: {len(items)}건")
    if log_callback:
        log_callback(f"[가격비교] 전체 완료: {len(all_results)}건")
    return all_results
