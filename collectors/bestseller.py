# collectors/bestseller.py - 베스트셀러 순위 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT, BESTSELLER_LIMIT

try:
    from utils.browser import fetch_page as _pw_fetch
    _HAS_PW = True
except ImportError:
    _HAS_PW = False


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_price(text: str) -> str:
    cleaned = re.sub(r"[^\d,원]", "", (text or "").strip())
    return cleaned or "-"


_API_HEADERS = {
    **REQUEST_HEADERS,
    "Referer": "https://www.musinsa.com/",
    "Accept": "application/json, text/plain, */*",
    "x-musinsa-client-type": "web",
}


def _call_musinsa_ranking_api(limit: int = 20) -> list[dict]:
    """무신사 내부 랭킹 API 직접 호출"""
    api_urls = [
        f"https://www.musinsa.com/api/goods/ranking?sortCode=POPULAR&page=1&size={limit}",
        f"https://api.musinsa.com/api/goods/ranking?page=1&pageSize={limit}&sortCode=POPULAR",
        f"https://www.musinsa.com/api/ranking?page=1&size={limit}",
    ]
    for url in api_urls:
        try:
            resp = requests.get(url, headers=_API_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                continue
            data = resp.json()
            items = (
                data.get("data", {}).get("goods") or
                data.get("data", {}).get("list") or
                data.get("goods") or data.get("list") or []
            )
            if items:
                return items
        except Exception:
            pass
    return []


def _get_html(url: str, wait_selector: str = None, referer: str = "") -> str:
    if _HAS_PW:
        try:
            return _pw_fetch(url, wait_selector=wait_selector, timeout_ms=25000,
                             extra_headers={"Referer": referer})
        except Exception:
            pass
    try:
        headers = {**REQUEST_HEADERS, "Referer": referer}
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return ""


def _find_product_arrays(obj, depth=0) -> list:
    if depth > 8:
        return []
    if isinstance(obj, list) and len(obj) >= 3:
        first = obj[0]
        if isinstance(first, dict) and any(
            k in first for k in ("goodsName", "itemName", "name", "productName", "title")
        ):
            return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = _find_product_arrays(v, depth + 1)
            if found:
                return found
    return []


def _parse_html(html: str, platform: str) -> list[dict]:
    """__NEXT_DATA__ 또는 HTML에서 상품 목록 파싱"""
    results = []

    # __NEXT_DATA__ JSON 파싱 (Next.js SSR 데이터)
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*(.*?)\s*</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            items = _find_product_arrays(data)
            for i, item in enumerate(items[:BESTSELLER_LIMIT], start=1):
                name = (item.get("goodsName") or item.get("itemName") or
                        item.get("name") or item.get("productName") or item.get("title") or "-")
                brand = (item.get("brandName") or
                         (item.get("brand", {}).get("name") if isinstance(item.get("brand"), dict) else item.get("brand")) or "-")
                price = (item.get("normalPrice") or item.get("consumerPrice") or
                         item.get("price") or item.get("salePrice") or "-")
                discount = item.get("discountRate", "-")
                goods_no = (item.get("goodsNo") or item.get("itemNo") or
                            item.get("id") or item.get("productId") or "")
                link = (
                    f"https://www.musinsa.com/products/{goods_no}" if platform == "무신사" and goods_no else
                    f"https://www.29cm.co.kr/catalog/{goods_no}" if platform == "29CM" and goods_no else "-"
                )
                if str(name) != "-":
                    results.append({
                        "플랫폼": platform, "브랜드": str(brand), "상품명": str(name),
                        "순위": i,
                        "가격": f"{int(price):,}원" if isinstance(price, (int, float)) else str(price),
                        "할인율": f"{discount}%" if str(discount).replace("%","").isdigit() else str(discount),
                        "링크": link, "수집시각": _now(),
                    })
        except Exception:
            pass

    # BeautifulSoup 폴백
    if not results:
        soup = BeautifulSoup(html, "html.parser")
        for sel in [
            "[class*='GoodsItem']", "[class*='goods-item']", ".goods-list__item",
            "[class*='ProductItem']", "[class*='RankItem']", "li[class*='item']",
        ]:
            els = soup.select(sel)
            if len(els) >= 3:
                for i, el in enumerate(els[:BESTSELLER_LIMIT], start=1):
                    name_el = el.select_one("[class*='name'],[class*='title'],strong")
                    brand_el = el.select_one("[class*='brand']")
                    price_el = el.select_one("[class*='price']")
                    link_el = el.select_one("a[href]")
                    name = name_el.get_text(strip=True) if name_el else "-"
                    if name == "-":
                        continue
                    results.append({
                        "플랫폼": platform,
                        "브랜드": brand_el.get_text(strip=True) if brand_el else "-",
                        "상품명": name, "순위": i,
                        "가격": _clean_price(price_el.get_text() if price_el else ""),
                        "할인율": "-",
                        "링크": link_el["href"] if link_el else "-",
                        "수집시각": _now(),
                    })
                break
    return results


def collect_musinsa_bestseller(log_callback=None) -> list[dict]:
    if log_callback:
        log_callback(f"[베스트셀러] 무신사 수집 중... {'(Playwright)' if _HAS_PW else '(requests)'}")

    # 1단계: 내부 API 직접 호출
    raw_items = _call_musinsa_ranking_api(limit=BESTSELLER_LIMIT)
    if raw_items:
        results = []
        for i, item in enumerate(raw_items[:BESTSELLER_LIMIT], start=1):
            name = (item.get("goodsName") or item.get("name") or "-")
            brand = (item.get("brandName") or
                     (item.get("brand", {}).get("name") if isinstance(item.get("brand"), dict) else "-"))
            price = item.get("normalPrice") or item.get("price") or item.get("salePrice") or "-"
            goods_no = item.get("goodsNo") or item.get("id") or ""
            results.append({
                "플랫폼": "무신사", "브랜드": str(brand or "-"), "상품명": str(name),
                "순위": i,
                "가격": f"{int(price):,}원" if isinstance(price, (int, float)) else str(price),
                "할인율": f"{item.get('discountRate', '-')}%",
                "링크": f"https://www.musinsa.com/products/{goods_no}" if goods_no else "-",
                "수집시각": _now(),
            })
        if log_callback:
            log_callback(f"[베스트셀러] 무신사: {len(results)}건 수집 (API)")
        return results

    # 2단계: HTML 페이지 (Playwright 또는 requests)
    ref = "https://www.musinsa.com/"
    for url in [
        "https://www.musinsa.com/ranking/best",
        "https://www.musinsa.com/ranking",
    ]:
        html = _get_html(url,
                         wait_selector="[class*='GoodsItem'],[class*='goods-item'],li[class*='item']",
                         referer=ref)
        if html:
            r = _parse_html(html, "무신사")
            if r:
                if log_callback:
                    log_callback(f"[베스트셀러] 무신사: {len(r)}건 수집")
                return r
    if log_callback:
        log_callback("[베스트셀러] 무신사: 0건 (Playwright 설치 후 재시도)")
    return []


def collect_29cm_bestseller(log_callback=None) -> list[dict]:
    if log_callback:
        log_callback(f"[베스트셀러] 29CM 수집 중... {'(Playwright)' if _HAS_PW else '(requests)'}")
    ref = "https://www.29cm.co.kr/"
    # 실제 작동 URL: /best-items, /store/best-items
    for url in [
        "https://shop.29cm.co.kr/best-items",
        "https://www.29cm.co.kr/store/best-items",
        "https://www.29cm.co.kr/best",
    ]:
        html = _get_html(url,
                         wait_selector="[class*='RankItem'],[class*='ProductItem'],li[class*='item'],[class*='BestItem']",
                         referer=ref)
        if html:
            r = _parse_html(html, "29CM")
            if r:
                if log_callback:
                    log_callback(f"[베스트셀러] 29CM: {len(r)}건 수집")
                return r
    if log_callback:
        log_callback("[베스트셀러] 29CM: 0건 (URL 확인 필요)")
    return []


def collect_own_brand_bestseller(brand: dict, log_callback=None) -> list[dict]:
    results = []
    brand_name = brand["name"]
    base = brand["url"].rstrip("/")
    if log_callback:
        log_callback(f"[베스트셀러] {brand_name} 자사몰 수집 중...")

    for url in [
        brand.get("best_url", ""),
        f"{base}/product/best",
        f"{base}/best",
        f"{base}/category/best",
    ]:
        if not url:
            continue
        html = _get_html(url,
                         wait_selector=".prdList li,[class*='product-list'] li",
                         referer=base + "/")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        items = []
        for sel in [
            ".prdList li", ".xans-product-listnormal li",
            "[class*='product-list'] li", ".goods-list li",
            "#best_list li", ".best_list li", ".thumb_list li",
        ]:
            items = soup.select(sel)
            if len(items) >= 3:
                break
        for i, item in enumerate(items[:BESTSELLER_LIMIT], start=1):
            name_el = item.select_one(
                ".name,.prd_name,.goods_name,strong.name,p.name,[class*='name'],[class*='title']"
            )
            price_el = item.select_one(".price,.cost,.prd_price,[class*='price'],.sale_price")
            link_el = item.select_one("a[href]")
            name = name_el.get_text(strip=True) if name_el else "-"
            if not name or name == "-":
                continue
            href = link_el["href"] if link_el else "-"
            if href != "-" and not href.startswith("http"):
                href = base + href
            results.append({
                "플랫폼": f"{brand_name} 자사몰", "브랜드": brand_name, "상품명": name,
                "순위": i, "가격": _clean_price(price_el.get_text() if price_el else ""),
                "할인율": "-", "링크": href, "수집시각": _now(),
            })
        if results:
            break

    if log_callback:
        log_callback(f"[베스트셀러] {brand_name} 자사몰: {len(results)}건 수집")
    return results


def collect_29cm_brand_bestseller(brand: dict, log_callback=None) -> list[dict]:
    """29CM 자사 브랜드 페이지에서 베스트셀러 수집"""
    results = []
    brand_name = brand["name"]
    cm29_id = brand.get("cm29_id", "")
    if not cm29_id:
        return results

    ref = "https://www.29cm.co.kr/"
    for url in [
        f"https://shop.29cm.co.kr/brand/{cm29_id}",
        f"https://www.29cm.co.kr/store/brand/{cm29_id}",
    ]:
        html = _get_html(url,
                         wait_selector="[class*='ProductItem'],[class*='GoodsItem'],li[class*='item']",
                         referer=ref)
        if not html:
            continue
        r = _parse_html(html, "29CM")
        if r:
            for item in r:
                item["브랜드"] = brand_name
            results = r
            break
    if log_callback:
        log_callback(f"[베스트셀러] 29CM {brand_name}: {len(results)}건 수집")
    return results


def collect_bestseller(log_callback=None) -> list[dict]:
    all_results = []
    all_results.extend(collect_musinsa_bestseller(log_callback=log_callback))
    all_results.extend(collect_29cm_bestseller(log_callback=log_callback))
    # 29CM 베스트가 0건이면 브랜드 페이지에서 직접 수집
    cm29_count = sum(1 for r in all_results if r["플랫폼"] == "29CM")
    if cm29_count == 0:
        for brand in OWN_BRANDS:
            all_results.extend(collect_29cm_brand_bestseller(brand, log_callback=log_callback))
    for brand in OWN_BRANDS:
        all_results.extend(collect_own_brand_bestseller(brand, log_callback=log_callback))
    return all_results
