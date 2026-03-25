# collectors/bestseller.py - 베스트셀러 순위 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT, BESTSELLER_LIMIT

# Playwright 선택적 사용 (설치된 경우에만)
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


def _get_html(url: str, wait_selector: str = None, referer: str = "") -> str:
    """Playwright 우선, 실패/미설치 시 requests 폴백"""
    if _HAS_PW:
        try:
            return _pw_fetch(url, wait_selector=wait_selector, timeout_ms=20000,
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
    ref = "https://www.musinsa.com/"
    for url in [
        "https://www.musinsa.com/ranking/best",
        "https://www.musinsa.com/ranking",
        "https://www.musinsa.com/category/001?sortCode=POPULAR",
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
        log_callback("[베스트셀러] 무신사: 0건 (URL 확인 필요)")
    return []


def collect_29cm_bestseller(log_callback=None) -> list[dict]:
    if log_callback:
        log_callback(f"[베스트셀러] 29CM 수집 중... {'(Playwright)' if _HAS_PW else '(requests)'}")
    ref = "https://www.29cm.co.kr/"
    for url in [
        "https://www.29cm.co.kr/ranking/ranking",
        "https://www.29cm.co.kr/ranking",
        "https://www.29cm.co.kr/best",
    ]:
        html = _get_html(url,
                         wait_selector="[class*='RankItem'],[class*='ProductItem'],li[class*='item']",
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


def collect_bestseller(log_callback=None) -> list[dict]:
    all_results = []
    all_results.extend(collect_musinsa_bestseller(log_callback=log_callback))
    all_results.extend(collect_29cm_bestseller(log_callback=log_callback))
    for brand in OWN_BRANDS:
        all_results.extend(collect_own_brand_bestseller(brand, log_callback=log_callback))
    return all_results
