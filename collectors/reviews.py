# collectors/reviews.py - 리뷰/별점 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT, REVIEW_LIMIT

try:
    from utils.browser import fetch_page as _pw_fetch
    _HAS_PW = True
except ImportError:
    _HAS_PW = False


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_html(url: str, referer: str = "https://www.musinsa.com/") -> str:
    if _HAS_PW:
        try:
            return _pw_fetch(
                url,
                wait_selector=(
                    "[class*='review-item'],[class*='ReviewItem'],"
                    ".review_list li,[class*='review-list'] li"
                ),
                timeout_ms=20000,
                extra_headers={"Referer": referer},
            )
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


def _find_product_ids_via_search(brand_id: str, brand_name: str, limit: int = 3) -> list[str]:
    """무신사 검색으로 자사 브랜드 상품 ID 수집"""
    product_ids = []
    urls = [
        f"https://www.musinsa.com/brands/{brand_id}/goods",
        f"https://www.musinsa.com/search/musinsa/goods?q={requests.utils.quote(brand_name)}&sortCode=NEWEST",
    ]
    for url in urls:
        try:
            html = _get_html(url)
            if not html:
                continue

            # __NEXT_DATA__에서 상품 번호 추출
            m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*(.*?)\s*</script>', html, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    nos = _extract_goods_nos(data)
                    product_ids.extend(nos[:limit])
                except Exception:
                    pass

            # HTML 폴백
            if not product_ids:
                soup = BeautifulSoup(html, "html.parser")
                for link in soup.select("a[href*='/products/']")[:limit]:
                    m2 = re.search(r"/products/(\d+)", link.get("href", ""))
                    if m2 and m2.group(1) not in product_ids:
                        product_ids.append(m2.group(1))

            if product_ids:
                break
        except Exception:
            pass
    return product_ids[:limit]


def _extract_goods_nos(obj, result=None, depth=0) -> list[str]:
    if result is None:
        result = []
    if depth > 8 or len(result) >= 5:
        return result
    if isinstance(obj, dict):
        no = obj.get("goodsNo") or obj.get("itemNo") or obj.get("productId")
        if no:
            result.append(str(no))
        for v in obj.values():
            _extract_goods_nos(v, result, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _extract_goods_nos(item, result, depth + 1)
    return result


def _collect_reviews_for_product(pid: str, brand_name: str, platform: str) -> list[dict]:
    """특정 상품 ID의 리뷰 수집"""
    results = []
    referer = f"https://www.musinsa.com/products/{pid}"

    if platform == "무신사":
        review_urls = [
            f"https://goods.musinsa.com/review/list.json?goodsNo={pid}&page=1&pageSize=10",
            f"https://www.musinsa.com/products/{pid}/reviews",
        ]
    else:
        return results

    for url in review_urls:
        try:
            # JSON API는 requests로만 시도 (Playwright 불필요)
            headers = {**REQUEST_HEADERS, "Referer": referer}
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                # HTML 리뷰 페이지는 Playwright로 시도
                if "reviews" in url:
                    html = _get_html(url, referer=referer)
                    if not html:
                        continue
                    resp = type("R", (), {"text": html, "status_code": 200})()
                else:
                    continue

            # JSON API 응답
            try:
                data = resp.json()
                review_list = (
                    data.get("data", {}).get("list") or
                    data.get("list") or
                    data.get("reviews") or []
                )
                for rev in review_list[:REVIEW_LIMIT]:
                    results.append({
                        "플랫폼": platform,
                        "브랜드": brand_name,
                        "상품명": rev.get("goodsName", rev.get("productName", "-")),
                        "별점": str(rev.get("starPoint", rev.get("rating", "-"))),
                        "리뷰내용": str(rev.get("contents", rev.get("content", "-")))[:200],
                        "작성일": rev.get("regDate", rev.get("createdAt", "-")),
                        "수집시각": _now(),
                    })
                if results:
                    break
            except (ValueError, AttributeError):
                pass

            # HTML 파싱 폴백
            html_text = getattr(resp, "text", "")
            if not html_text and "reviews" in url:
                html_text = _get_html(url, referer=referer)
            soup = BeautifulSoup(html_text, "html.parser")
            prod_name_el = soup.select_one("h1,[class*='goods-name'],[class*='product-name']")
            prod_name = prod_name_el.get_text(strip=True) if prod_name_el else "-"
            for sel in [
                "[class*='review-item']", "[class*='ReviewItem']",
                ".review_list li", "[class*='review-list'] li",
            ]:
                items = soup.select(sel)
                if items:
                    for rev in items[:REVIEW_LIMIT]:
                        score_el = rev.select_one("[class*='star'],[class*='rating'],[class*='score']")
                        content_el = rev.select_one("[class*='content'],[class*='text'],p")
                        date_el = rev.select_one("[class*='date'],time")
                        results.append({
                            "플랫폼": platform,
                            "브랜드": brand_name,
                            "상품명": prod_name,
                            "별점": score_el.get_text(strip=True) if score_el else "-",
                            "리뷰내용": content_el.get_text(strip=True)[:200] if content_el else "-",
                            "작성일": date_el.get_text(strip=True) if date_el else "-",
                            "수집시각": _now(),
                        })
                    break
            if results:
                break
        except Exception:
            pass
    return results


def collect_musinsa_reviews(log_callback=None) -> list[dict]:
    all_results = []
    for brand in OWN_BRANDS:
        brand_name = brand["name"]
        brand_id = brand["musinsa_id"]
        if log_callback:
            log_callback(f"[리뷰] 무신사 {brand_name} 상품 조회 중...")

        pids = _find_product_ids_via_search(brand_id, brand_name, limit=3)
        if not pids:
            if log_callback:
                log_callback(f"[리뷰] 무신사 {brand_name}: 상품 없음 (brand ID 확인 필요)")
            continue

        for pid in pids:
            reviews = _collect_reviews_for_product(pid, brand_name, "무신사")
            all_results.extend(reviews)

    if log_callback:
        log_callback(f"[리뷰] 무신사 전체: {len(all_results)}건")
    return all_results


def collect_29cm_reviews(log_callback=None) -> list[dict]:
    all_results = []

    for brand in OWN_BRANDS:
        brand_name = brand["name"]
        if log_callback:
            log_callback(f"[리뷰] 29CM {brand_name} 수집 중... {'(Playwright)' if _HAS_PW else ''}")

        # 29CM 검색 URL 후보
        search_urls = [
            f"https://www.29cm.co.kr/search?keyword={requests.utils.quote(brand_name)}&sort=REVIEW_COUNT",
            f"https://www.29cm.co.kr/search?keyword={requests.utils.quote(brand_name)}",
        ]
        for url in search_urls:
            try:
                html = _get_html(url, referer="https://www.29cm.co.kr/")
                if not html:
                    continue

                m = re.search(
                    r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*(.*?)\s*</script>', html, re.DOTALL
                )
                if m:
                    data = json.loads(m.group(1))
                    items = _find_any_items(data)
                    for item in items[:3]:
                        prod_name = item.get("itemName", item.get("name", "-"))
                        for rev in item.get("reviews", [])[:5]:
                            all_results.append({
                                "플랫폼": "29CM", "브랜드": brand_name,
                                "상품명": prod_name,
                                "별점": str(rev.get("rating", "-")),
                                "리뷰내용": str(rev.get("content", "-"))[:200],
                                "작성일": rev.get("createdAt", "-"),
                                "수집시각": _now(),
                            })
                break
            except Exception as e:
                if log_callback:
                    log_callback(f"[리뷰] 29CM {brand_name} 오류: {e}")

    if log_callback:
        log_callback(f"[리뷰] 29CM 전체: {len(all_results)}건")
    return all_results


def _find_any_items(obj, depth=0) -> list:
    if depth > 8:
        return []
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        if any(k in obj[0] for k in ("itemNo", "itemName", "goodsNo", "name")):
            return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = _find_any_items(v, depth + 1)
            if found:
                return found
    return []


def collect_reviews(log_callback=None) -> list[dict]:
    all_results = []
    all_results.extend(collect_musinsa_reviews(log_callback=log_callback))
    all_results.extend(collect_29cm_reviews(log_callback=log_callback))
    if log_callback:
        log_callback(f"[리뷰] 전체 완료: {len(all_results)}건")
    return all_results
