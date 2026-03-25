# collectors/competitor_new.py - 경쟁사 신상품 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import COMPETITOR_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT, COMPETITOR_NEW_LIMIT


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_price(text: str) -> str:
    if not text:
        return "-"
    return re.sub(r"[^\d,원]", "", text.strip()) or "-"


def collect_brand_new_products(brand: dict, log_callback=None) -> list[dict]:
    """무신사에서 특정 브랜드의 최신 상품 수집"""
    results = []
    brand_name = brand["name"]
    musinsa_id = brand["musinsa_id"]
    url = f"https://www.musinsa.com/brands/{musinsa_id}/goods?sortCode=NEWEST"

    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        # __NEXT_DATA__ 추출 시도
        match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                props = data.get("props", {}).get("pageProps", {})
                # 다양한 경로 탐색
                items = (
                    props.get("dehydratedState", {})
                    .get("queries", [{}])[0]
                    .get("state", {})
                    .get("data", {})
                    .get("list", [])
                )
                if not items:
                    items = props.get("goodsList", props.get("items", []))
                for item in items[:COMPETITOR_NEW_LIMIT]:
                    results.append({
                        "브랜드": brand_name,
                        "상품명": item.get("goodsName", item.get("name", "-")),
                        "가격": str(item.get("normalPrice", item.get("price", "-"))),
                        "등록일": item.get("goodsDate", item.get("registDate", "-")),
                        "링크": f"https://www.musinsa.com/products/{item.get('goodsNo', item.get('id', ''))}",
                        "수집시각": _now(),
                    })
            except Exception:
                pass

        # BeautifulSoup 폴백
        if not results:
            soup = BeautifulSoup(html, "html.parser")
            items = soup.select(
                ".goods-list__item, [class*='GoodsItem'], [class*='goods-item'], "
                "li[class*='item'], .product-item"
            )
            for item in items[:COMPETITOR_NEW_LIMIT]:
                name_el = item.select_one(
                    "[class*='goods-name'], [class*='item-name'], .goods_nm, .name, .title"
                )
                price_el = item.select_one("[class*='price'], .price")
                link_el = item.select_one("a[href]")
                name = name_el.get_text(strip=True) if name_el else "-"
                if name == "-":
                    continue
                results.append({
                    "브랜드": brand_name,
                    "상품명": name,
                    "가격": _clean_price(price_el.get_text() if price_el else ""),
                    "등록일": "-",
                    "링크": link_el["href"] if link_el else "-",
                    "수집시각": _now(),
                })

    except Exception as e:
        if log_callback:
            log_callback(f"[경쟁사신상품] {brand_name} 오류: {e}")

    return results


def collect_competitor_new(log_callback=None) -> list[dict]:
    """경쟁사 브랜드 전체 신상품 수집"""
    all_results = []

    for brand in COMPETITOR_BRANDS:
        if log_callback:
            log_callback(f"[경쟁사신상품] {brand['name']} 수집 중...")
        items = collect_brand_new_products(brand, log_callback=log_callback)
        all_results.extend(items)
        if log_callback:
            log_callback(f"[경쟁사신상품] {brand['name']}: {len(items)}건")

    if log_callback:
        log_callback(f"[경쟁사신상품] 전체 완료: {len(all_results)}건")
    return all_results


if __name__ == "__main__":
    data = collect_competitor_new(log_callback=print)
    for row in data[:5]:
        print(row)
