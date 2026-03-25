# collectors/reviews.py - 리뷰/별점 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT, REVIEW_LIMIT


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_brand_product_ids_musinsa(brand_id: str, limit: int = 3) -> list[str]:
    """무신사에서 브랜드의 상품 ID 목록 조회"""
    product_ids = []
    url = f"https://www.musinsa.com/brands/{brand_id}/goods"
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select("a[href*='/products/']")
        seen = set()
        for link in links:
            href = link.get("href", "")
            match = re.search(r"/products/(\d+)", href)
            if match:
                pid = match.group(1)
                if pid not in seen:
                    seen.add(pid)
                    product_ids.append(pid)
                if len(product_ids) >= limit:
                    break
    except Exception:
        pass
    return product_ids


def collect_musinsa_reviews(log_callback=None) -> list[dict]:
    """무신사 자사 브랜드 상품 리뷰 수집"""
    all_results = []

    for brand in OWN_BRANDS:
        brand_name = brand["name"]
        brand_id = brand["musinsa_id"]
        if log_callback:
            log_callback(f"[리뷰] 무신사 {brand_name} 상품 조회 중...")

        product_ids = _get_brand_product_ids_musinsa(brand_id, limit=3)
        if not product_ids:
            if log_callback:
                log_callback(f"[리뷰] 무신사 {brand_name}: 상품 없음")
            continue

        for pid in product_ids:
            # 리뷰 API 시도
            review_urls = [
                f"https://www.musinsa.com/products/{pid}/reviews",
                f"https://goods.musinsa.com/review/list.json?goodsNo={pid}&page=1&pageSize=10",
            ]
            for rev_url in review_urls:
                try:
                    resp = requests.get(rev_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
                    if resp.status_code != 200:
                        continue

                    # JSON 응답 시도
                    try:
                        data = resp.json()
                        review_list = (
                            data.get("data", {}).get("list", []) or
                            data.get("list", []) or
                            data.get("reviews", [])
                        )
                        for review in review_list[:REVIEW_LIMIT]:
                            all_results.append({
                                "플랫폼": "무신사",
                                "브랜드": brand_name,
                                "상품명": review.get("goodsName", review.get("productName", "-")),
                                "별점": str(review.get("starPoint", review.get("rating", "-"))),
                                "리뷰내용": review.get("contents", review.get("content", "-"))[:200],
                                "작성일": review.get("regDate", review.get("createdAt", "-")),
                                "수집시각": _now(),
                            })
                        if review_list:
                            break
                    except Exception:
                        pass

                    # HTML 파싱 폴백
                    soup = BeautifulSoup(resp.text, "html.parser")
                    review_items = soup.select(
                        "[class*='review-item'], [class*='ReviewItem'], "
                        ".review_list li, [class*='review-list'] li"
                    )
                    prod_name_el = soup.select_one("h1[class*='title'], [class*='goods-name']")
                    prod_name = prod_name_el.get_text(strip=True) if prod_name_el else "-"

                    for review in review_items[:REVIEW_LIMIT]:
                        score_el = review.select_one(
                            "[class*='star'], [class*='rating'], [class*='score']"
                        )
                        content_el = review.select_one(
                            "[class*='content'], [class*='text'], p"
                        )
                        date_el = review.select_one(
                            "[class*='date'], time"
                        )
                        all_results.append({
                            "플랫폼": "무신사",
                            "브랜드": brand_name,
                            "상품명": prod_name,
                            "별점": score_el.get_text(strip=True) if score_el else "-",
                            "리뷰내용": content_el.get_text(strip=True)[:200] if content_el else "-",
                            "작성일": date_el.get_text(strip=True) if date_el else "-",
                            "수집시각": _now(),
                        })
                    if review_items:
                        break

                except Exception as e:
                    if log_callback:
                        log_callback(f"[리뷰] 무신사 {brand_name} {pid} 오류: {e}")

    if log_callback:
        log_callback(f"[리뷰] 무신사 전체: {len(all_results)}건")
    return all_results


def collect_29cm_reviews(log_callback=None) -> list[dict]:
    """29CM 자사 브랜드 리뷰 수집"""
    all_results = []

    for brand in OWN_BRANDS:
        brand_name = brand["name"]
        if log_callback:
            log_callback(f"[리뷰] 29CM {brand_name} 수집 중...")
        try:
            search_url = f"https://www.29cm.co.kr/search?keyword={brand_name}&sort=review_count"
            resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            # __NEXT_DATA__ 시도
            match = re.search(
                r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL
            )
            if match:
                data = json.loads(match.group(1))
                items = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("searchResult", {})
                    .get("items", [])
                )
                for item in items[:3]:
                    item_no = item.get("itemNo", "")
                    reviews = item.get("reviews", [])
                    prod_name = item.get("itemName", "-")
                    for rev in reviews[:5]:
                        all_results.append({
                            "플랫폼": "29CM",
                            "브랜드": brand_name,
                            "상품명": prod_name,
                            "별점": str(rev.get("rating", "-")),
                            "리뷰내용": rev.get("content", "-")[:200],
                            "작성일": rev.get("createdAt", "-"),
                            "수집시각": _now(),
                        })

        except Exception as e:
            if log_callback:
                log_callback(f"[리뷰] 29CM {brand_name} 오류: {e}")

    if log_callback:
        log_callback(f"[리뷰] 29CM 전체: {len(all_results)}건")
    return all_results


def collect_reviews(log_callback=None) -> list[dict]:
    """전체 리뷰 수집 (무신사 + 29CM)"""
    all_results = []
    all_results.extend(collect_musinsa_reviews(log_callback=log_callback))
    all_results.extend(collect_29cm_reviews(log_callback=log_callback))
    if log_callback:
        log_callback(f"[리뷰] 전체 완료: {len(all_results)}건")
    return all_results


if __name__ == "__main__":
    data = collect_reviews(log_callback=print)
    for row in data[:5]:
        print(row)
