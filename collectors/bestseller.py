# collectors/bestseller.py - 베스트셀러 순위 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import (
    OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT, BESTSELLER_LIMIT
)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_price(text: str) -> str:
    if not text:
        return "-"
    return re.sub(r"[^\d,원]", "", text.strip()) or "-"


def _parse_musinsa_next_data(html: str) -> list[dict]:
    """무신사 __NEXT_DATA__ JSON에서 상품 데이터 추출 시도"""
    results = []
    try:
        match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            return results
        data = json.loads(match.group(1))
        # 다양한 키 경로 탐색
        props = data.get("props", {}).get("pageProps", {})
        items = (
            props.get("dehydratedState", {})
            .get("queries", [{}])[0]
            .get("state", {})
            .get("data", {})
            .get("list", [])
        )
        for i, item in enumerate(items[:BESTSELLER_LIMIT], start=1):
            results.append({
                "플랫폼": "무신사",
                "브랜드": item.get("brandName", "-"),
                "상품명": item.get("goodsName", item.get("name", "-")),
                "순위": i,
                "가격": str(item.get("normalPrice", item.get("price", "-"))),
                "할인율": str(item.get("discountRate", "-")),
                "링크": f"https://www.musinsa.com/products/{item.get('goodsNo', '')}",
                "수집시각": _now(),
            })
    except Exception:
        pass
    return results


def collect_musinsa_bestseller(log_callback=None) -> list[dict]:
    """무신사 베스트셀러 수집"""
    results = []
    url = "https://www.musinsa.com/ranking/best"
    if log_callback:
        log_callback("[베스트셀러] 무신사 수집 중...")
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        # __NEXT_DATA__ 시도
        results = _parse_musinsa_next_data(html)

        # BeautifulSoup 폴백
        if not results:
            soup = BeautifulSoup(html, "html.parser")
            items = soup.select(".ranking-list__item, .goods-list__item, [class*='RankingItem'], li[class*='list-item']")
            for i, item in enumerate(items[:BESTSELLER_LIMIT], start=1):
                name_el = item.select_one("[class*='goods-name'], [class*='item-name'], .goods_nm, .title")
                brand_el = item.select_one("[class*='brand'], .brand_name, .brand")
                price_el = item.select_one("[class*='price'], .price")
                link_el = item.select_one("a[href]")
                results.append({
                    "플랫폼": "무신사",
                    "브랜드": brand_el.get_text(strip=True) if brand_el else "-",
                    "상품명": name_el.get_text(strip=True) if name_el else "-",
                    "순위": i,
                    "가격": _clean_price(price_el.get_text() if price_el else ""),
                    "할인율": "-",
                    "링크": link_el["href"] if link_el else "-",
                    "수집시각": _now(),
                })

        if log_callback:
            log_callback(f"[베스트셀러] 무신사: {len(results)}건 수집")
    except Exception as e:
        if log_callback:
            log_callback(f"[베스트셀러] 무신사 오류: {e}")
    return results


def collect_29cm_bestseller(log_callback=None) -> list[dict]:
    """29CM 베스트셀러 수집"""
    results = []
    url = "https://www.29cm.co.kr/ranking"
    if log_callback:
        log_callback("[베스트셀러] 29CM 수집 중...")
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # __NEXT_DATA__ 시도
        match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            items = data.get("props", {}).get("pageProps", {}).get("items", [])
            for i, item in enumerate(items[:BESTSELLER_LIMIT], start=1):
                results.append({
                    "플랫폼": "29CM",
                    "브랜드": item.get("brandName", item.get("brand", {}).get("name", "-")),
                    "상품명": item.get("itemName", item.get("name", "-")),
                    "순위": i,
                    "가격": str(item.get("consumerPrice", item.get("price", "-"))),
                    "할인율": str(item.get("discountRate", "-")),
                    "링크": f"https://www.29cm.co.kr/catalog/{item.get('itemNo', '')}",
                    "수집시각": _now(),
                })

        if not results:
            items = soup.select("[class*='RankItem'], [class*='rank-item'], [class*='ProductItem'], li[class*='item']")
            for i, item in enumerate(items[:BESTSELLER_LIMIT], start=1):
                name_el = item.select_one("[class*='name'], [class*='title']")
                brand_el = item.select_one("[class*='brand']")
                price_el = item.select_one("[class*='price']")
                link_el = item.select_one("a[href]")
                results.append({
                    "플랫폼": "29CM",
                    "브랜드": brand_el.get_text(strip=True) if brand_el else "-",
                    "상품명": name_el.get_text(strip=True) if name_el else "-",
                    "순위": i,
                    "가격": _clean_price(price_el.get_text() if price_el else ""),
                    "할인율": "-",
                    "링크": link_el["href"] if link_el else "-",
                    "수집시각": _now(),
                })

        if log_callback:
            log_callback(f"[베스트셀러] 29CM: {len(results)}건 수집")
    except Exception as e:
        if log_callback:
            log_callback(f"[베스트셀러] 29CM 오류: {e}")
    return results


def collect_own_brand_bestseller(brand: dict, log_callback=None) -> list[dict]:
    """자사몰 베스트셀러 수집 (Cafe24 기반)"""
    results = []
    brand_name = brand["name"]
    urls_to_try = [
        brand.get("best_url", ""),
        brand["url"] + "/best",
        brand["url"] + "/product/best",
        brand["url"] + "/category/best",
    ]
    if log_callback:
        log_callback(f"[베스트셀러] {brand_name} 자사몰 수집 중...")
    for url in urls_to_try:
        if not url:
            continue
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            # Cafe24 공통 셀렉터
            items = soup.select(
                ".prdList li, .xans-product-listnormal li, "
                "[class*='product-list'] li, .goods-list li, "
                "#best_list li, .best_list li"
            )
            for i, item in enumerate(items[:BESTSELLER_LIMIT], start=1):
                name_el = item.select_one(".name, .prd_name, .goods_name, strong.name, p.name")
                price_el = item.select_one(".price, .cost, .prd_price, span[class*='price']")
                link_el = item.select_one("a[href]")
                name = name_el.get_text(strip=True) if name_el else "-"
                if name == "-":
                    continue
                results.append({
                    "플랫폼": f"{brand_name} 자사몰",
                    "브랜드": brand_name,
                    "상품명": name,
                    "순위": i,
                    "가격": _clean_price(price_el.get_text() if price_el else ""),
                    "할인율": "-",
                    "링크": link_el["href"] if link_el else "-",
                    "수집시각": _now(),
                })
            if results:
                break
        except Exception as e:
            if log_callback:
                log_callback(f"[베스트셀러] {brand_name} ({url}) 오류: {e}")
    if log_callback:
        log_callback(f"[베스트셀러] {brand_name} 자사몰: {len(results)}건 수집")
    return results


def collect_bestseller(log_callback=None) -> list[dict]:
    """전체 베스트셀러 수집 (무신사 + 29CM + 자사몰 3곳)"""
    all_results = []
    all_results.extend(collect_musinsa_bestseller(log_callback=log_callback))
    all_results.extend(collect_29cm_bestseller(log_callback=log_callback))
    for brand in OWN_BRANDS:
        all_results.extend(collect_own_brand_bestseller(brand, log_callback=log_callback))
    return all_results


if __name__ == "__main__":
    data = collect_bestseller(log_callback=print)
    for row in data[:5]:
        print(row)
