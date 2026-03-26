# collectors/competitor_new.py - 경쟁사 신상품 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote

from config import COMPETITOR_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT, COMPETITOR_NEW_LIMIT

try:
    from utils.browser import fetch_page as _pw_fetch
    _HAS_PW = True
except ImportError:
    _HAS_PW = False


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 무신사 내부 API 헤더 (앱/API 요청처럼 위장)
_API_HEADERS = {
    **REQUEST_HEADERS,
    "Referer": "https://www.musinsa.com/",
    "Accept": "application/json, text/plain, */*",
    "x-musinsa-client-type": "web",
}


def _call_musinsa_brand_api(musinsa_id: str, limit: int = 10) -> list[dict]:
    """무신사 내부 API로 브랜드 신상품 수집"""
    results = []

    # 방법 1: 브랜드 상품 API (JSON)
    api_urls = [
        f"https://www.musinsa.com/api/brand/{musinsa_id}/goods?sortCode=NEWEST&page=1&size={limit}",
        f"https://api.musinsa.com/api/brand/{musinsa_id}/products?sort=new&page=1&pageSize={limit}",
        f"https://www.musinsa.com/api/goods/brand?brandCode={musinsa_id}&sortCode=NEWEST&page=1&size={limit}",
    ]
    for url in api_urls:
        try:
            resp = requests.get(url, headers=_API_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                continue
            data = resp.json()
            # 다양한 응답 구조 대응
            items = (
                data.get("data", {}).get("goods") or
                data.get("data", {}).get("list") or
                data.get("goods") or
                data.get("list") or
                data.get("items") or []
            )
            for item in items[:limit]:
                results.append(_normalize_item(item))
            if results:
                return results
        except Exception:
            pass

    return results


def _get_html(url: str) -> str:
    if _HAS_PW:
        try:
            return _pw_fetch(
                url,
                wait_selector="[class*='GoodsItem'],[class*='goods-item'],li[class*='item']",
                timeout_ms=25000,
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


def _normalize_item(item: dict) -> dict:
    name = (item.get("goodsName") or item.get("name") or
            item.get("productName") or item.get("itemName") or "-")
    brand = (item.get("brandName") or
             (item.get("brand", {}).get("name") if isinstance(item.get("brand"), dict)
              else item.get("brand")) or "-")
    price = item.get("normalPrice") or item.get("price") or item.get("salePrice") or "-"
    goods_no = item.get("goodsNo") or item.get("id") or item.get("productId") or ""
    link = f"https://www.musinsa.com/products/{goods_no}" if goods_no else "-"
    return {
        "브랜드": str(brand), "상품명": str(name),
        "가격": f"{int(price):,}원" if isinstance(price, (int, float)) and price else str(price),
        "등록일": item.get("wdate", item.get("createdAt", "-")),
        "링크": link, "수집시각": _now(),
    }


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
    """
    무신사 브랜드 페이지 상품 파싱.
    진단 결과: __NEXT_DATA__에 상품 없음, a[href*='/products/'] 링크 160~212개 존재.
    → a 태그 직접 순회 방식으로 파싱.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen_pids = set()

    for a_tag in soup.select("a[href*='/products/']"):
        href = a_tag.get("href", "")
        m = re.search(r"/products/(\d+)", href)
        if not m:
            continue
        pid = m.group(1)
        if pid in seen_pids:
            continue
        seen_pids.add(pid)

        # a 태그 또는 상위 컨테이너에서 이름/가격 추출
        # 최대 5단계 상위 탐색하며 상품명 요소 탐색
        container = a_tag
        name_el = None
        price_el = None
        for _ in range(6):
            name_el = container.select_one(
                "[class*='goods_name'],[class*='goodsName'],"
                "[class*='item_name'],[class*='itemName'],"
                "[class*='product_name'],[class*='productName']"
            )
            price_el = container.select_one(
                "[class*='price'],[class*='cost'],[class*='Price']"
            )
            if name_el:
                break
            if container.parent:
                container = container.parent
            else:
                break

        # 상품명 추출
        if name_el:
            name = name_el.get_text(strip=True)
        else:
            # img alt 또는 a 직접 텍스트 사용
            img = a_tag.find("img")
            name = img.get("alt", "").strip() if img else a_tag.get_text(strip=True)[:80]

        name = re.sub(r"\s+", " ", name).strip()
        if not name or len(name) < 2:
            continue

        # 가격 추출
        price_text = ""
        if price_el:
            price_text = re.sub(r"[^\d,원]", "", price_el.get_text(strip=True))

        full_link = ("https://www.musinsa.com" + href) if href.startswith("/") else href

        results.append({
            "브랜드": brand_name,
            "상품명": name[:100],
            "가격": price_text or "-",
            "등록일": "-",
            "링크": full_link,
            "수집시각": _now(),
        })

        if len(results) >= COMPETITOR_NEW_LIMIT:
            break

    return results


def collect_brand_new_products(brand: dict, log_callback=None) -> list[dict]:
    brand_name = brand["name"]
    musinsa_id = brand["musinsa_id"]

    # 1단계: 내부 API 직접 호출 (Playwright 불필요)
    results = _call_musinsa_brand_api(musinsa_id, limit=COMPETITOR_NEW_LIMIT)
    if results:
        for r in results:
            r["브랜드"] = brand_name
        return results

    # 2단계: HTML 페이지 (Playwright 또는 requests)
    urls = [
        f"https://www.musinsa.com/brand/{musinsa_id}/goods?sortCode=NEWEST",
        f"https://www.musinsa.com/brand/{musinsa_id}",
        f"https://www.musinsa.com/search/musinsa/goods?q={quote(brand_name)}&sortCode=NEWEST",
    ]
    for url in urls:
        html = _get_html(url)
        if html:
            r = _parse_products(html, brand_name)
            if r:
                return r

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
        f"https://www.musinsa.com/brand/{musinsa_id}/goods?sortCode=NEWEST",
        f"https://www.musinsa.com/brand/{musinsa_id}",
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
