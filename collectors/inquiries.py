# collectors/inquiries.py - 고객 문의(Q&A) 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT

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
                    "[class*='qna-item'],[class*='QnaItem'],"
                    ".qna_list li,a[href*='/products/']"
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


def _get_brand_product_ids_musinsa(brand_id: str, brand_name: str = "", limit: int = 3) -> list[tuple[str, str]]:
    """
    무신사 브랜드 상품 ID/상품명 조회.
    진단 결과: a[href*='/products/'] 직접 파싱 방식 사용.
    """
    products = []
    urls = [
        f"https://www.musinsa.com/brand/{brand_id}",
        f"https://www.musinsa.com/search/musinsa/goods?q={requests.utils.quote(brand_name)}&sortCode=NEWEST" if brand_name else "",
    ]
    for url in [u for u in urls if u]:
        try:
            html = _get_html(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            seen = set()
            for a_tag in soup.select("a[href*='/products/']"):
                href = a_tag.get("href", "")
                m = re.search(r"/products/(\d+)", href)
                if not m:
                    continue
                pid = m.group(1)
                if pid in seen:
                    continue
                seen.add(pid)

                # 상품명 추출 (a 태그 상위 탐색)
                container = a_tag
                name_el = None
                for _ in range(5):
                    name_el = container.select_one(
                        "[class*='goods_name'],[class*='goodsName'],"
                        "[class*='item_name'],[class*='name'],[class*='title']"
                    )
                    if name_el:
                        break
                    if container.parent:
                        container = container.parent
                    else:
                        break

                if name_el:
                    name = name_el.get_text(strip=True)
                else:
                    img = a_tag.find("img")
                    name = img.get("alt", "").strip() if img else f"상품 {pid}"

                name = re.sub(r"\s+", " ", name).strip() or f"상품 {pid}"
                products.append((pid, name[:80]))

                if len(products) >= limit:
                    break

            if products:
                break
        except Exception:
            pass
    return products[:limit]


def collect_musinsa_inquiries(log_callback=None) -> list[dict]:
    """무신사 자사 브랜드 상품 Q&A 수집"""
    all_results = []

    for brand in OWN_BRANDS:
        brand_name = brand["name"]
        brand_id = brand["musinsa_id"]
        if log_callback:
            log_callback(f"[고객문의] 무신사 {brand_name} 상품 조회 중...")

        products = _get_brand_product_ids_musinsa(brand_id, brand_name=brand_name, limit=3)
        if not products:
            if log_callback:
                log_callback(f"[고객문의] 무신사 {brand_name}: 상품 없음")
            continue

        for pid, prod_name in products:
            referer = f"https://www.musinsa.com/products/{pid}"
            # JSON API (requests 전용)
            json_url = f"https://goods.musinsa.com/goods/qna/list.json?goodsNo={pid}&page=1&pageSize=10"
            html_url = f"https://www.musinsa.com/products/{pid}/qna"
            got_data = False

            try:
                resp = requests.get(json_url, headers={**REQUEST_HEADERS, "Referer": referer},
                                    timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        qa_list = (
                            data.get("data", {}).get("list", []) or
                            data.get("list", []) or
                            data.get("qnaList", [])
                        )
                        for qa in qa_list[:10]:
                            question = qa.get("contents", qa.get("question", qa.get("content", "-")))
                            answer = qa.get("answer", {})
                            has_answer = bool(answer) if isinstance(answer, dict) else bool(answer)
                            answer_text = (
                                answer.get("contents", "") if isinstance(answer, dict) else str(answer)
                            )
                            all_results.append({
                                "플랫폼": "무신사",
                                "브랜드": brand_name,
                                "상품명": prod_name,
                                "질문": str(question)[:200],
                                "답변여부": "답변완료" if has_answer else "미답변",
                                "답변내용": str(answer_text)[:200] if has_answer else "-",
                                "작성일": qa.get("regDate", qa.get("createdAt", "-")),
                                "수집시각": _now(),
                            })
                        if qa_list:
                            got_data = True
                    except Exception:
                        pass
            except Exception:
                pass

            if not got_data:
                # HTML Q&A 페이지 (Playwright 우선)
                try:
                    html = _get_html(html_url, referer=referer)
                    if html:
                        soup = BeautifulSoup(html, "html.parser")
                        qa_items = soup.select(
                            "[class*='qna-item'], [class*='QnaItem'], "
                            ".qna_list li, [class*='inquiry'] li"
                        )
                        for qa in qa_items[:10]:
                            q_el = qa.select_one(
                                "[class*='question'], [class*='title'], [class*='content']"
                            )
                            a_el = qa.select_one("[class*='answer'], [class*='reply']")
                            date_el = qa.select_one("[class*='date'], time")
                            question = q_el.get_text(strip=True)[:200] if q_el else "-"
                            if question == "-":
                                continue
                            has_answer = a_el is not None and bool(a_el.get_text(strip=True))
                            all_results.append({
                                "플랫폼": "무신사",
                                "브랜드": brand_name,
                                "상품명": prod_name,
                                "질문": question,
                                "답변여부": "답변완료" if has_answer else "미답변",
                                "답변내용": a_el.get_text(strip=True)[:200] if has_answer else "-",
                                "작성일": date_el.get_text(strip=True) if date_el else "-",
                                "수집시각": _now(),
                            })
                except Exception as e:
                    if log_callback:
                        log_callback(f"[고객문의] 무신사 {brand_name} {pid} 오류: {e}")

    if log_callback:
        log_callback(f"[고객문의] 무신사 전체: {len(all_results)}건")
    return all_results


def collect_inquiries(log_callback=None) -> list[dict]:
    """전체 고객 문의 수집"""
    all_results = []
    all_results.extend(collect_musinsa_inquiries(log_callback=log_callback))
    if log_callback:
        log_callback(f"[고객문의] 전체 완료: {len(all_results)}건")
    return all_results


if __name__ == "__main__":
    data = collect_inquiries(log_callback=print)
    for row in data[:5]:
        print(row)
