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


def _extract_price_int(text: str) -> int | None:
    """가격 문자열에서 숫자 추출"""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _collect_category_prices(category: dict, log_callback=None) -> list[dict]:
    """특정 카테고리의 무신사 베스트 상품 가격 수집"""
    results = []
    cat_name = category["name"]
    cat_code = category["code"]
    url = f"https://www.musinsa.com/ranking/best?categorySub={cat_code}"

    all_brands = (
        [b["name"] for b in OWN_BRANDS] +
        [b["name"] for b in COMPETITOR_BRANDS]
    )

    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        brand_prices: dict[str, list[int]] = {}

        # __NEXT_DATA__ 추출 시도
        match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                items = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("dehydratedState", {})
                    .get("queries", [{}])[0]
                    .get("state", {})
                    .get("data", {})
                    .get("list", [])
                )
                for item in items[:PRICE_COMPARE_LIMIT]:
                    b_name = item.get("brandName", "")
                    price = item.get("normalPrice", item.get("price", 0))
                    if b_name and isinstance(price, (int, float)) and price > 0:
                        brand_prices.setdefault(b_name, []).append(int(price))
            except Exception:
                pass

        # BeautifulSoup 폴백
        if not brand_prices:
            soup = BeautifulSoup(html, "html.parser")
            items = soup.select(
                ".ranking-list__item, .goods-list__item, [class*='RankingItem'], li[class*='list-item']"
            )
            for item in items[:PRICE_COMPARE_LIMIT]:
                brand_el = item.select_one("[class*='brand'], .brand_name, .brand")
                price_el = item.select_one("[class*='price'], .price")
                if brand_el and price_el:
                    b_name = brand_el.get_text(strip=True)
                    price = _extract_price_int(price_el.get_text())
                    if b_name and price and price > 0:
                        brand_prices.setdefault(b_name, []).append(price)

        # 자사/경쟁사 브랜드 집계
        own_names = {b["name"] for b in OWN_BRANDS}
        comp_names = {b["name"] for b in COMPETITOR_BRANDS}

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

    except Exception as e:
        if log_callback:
            log_callback(f"[가격비교] {cat_name} 오류: {e}")

    return results


def collect_price_compare(log_callback=None) -> list[dict]:
    """전 복종 가격 비교 수집"""
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


if __name__ == "__main__":
    data = collect_price_compare(log_callback=print)
    for row in data[:5]:
        print(row)
