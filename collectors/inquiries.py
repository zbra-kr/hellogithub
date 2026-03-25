# collectors/inquiries.py - 고객 문의(Q&A) 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_brand_product_ids_musinsa(brand_id: str, limit: int = 3) -> list[tuple[str, str]]:
    """무신사에서 브랜드 상품 ID와 상품명 조회"""
    products = []
    url = f"https://www.musinsa.com/brands/{brand_id}/goods"
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("a[href*='/products/']")
        seen = set()
        for item in items:
            href = item.get("href", "")
            match = re.search(r"/products/(\d+)", href)
            if match:
                pid = match.group(1)
                if pid not in seen:
                    seen.add(pid)
                    name_el = item.select_one("[class*='name'], [class*='title']")
                    name = name_el.get_text(strip=True) if name_el else f"상품 {pid}"
                    products.append((pid, name))
                if len(products) >= limit:
                    break
    except Exception:
        pass
    return products


def collect_musinsa_inquiries(log_callback=None) -> list[dict]:
    """무신사 자사 브랜드 상품 Q&A 수집"""
    all_results = []

    for brand in OWN_BRANDS:
        brand_name = brand["name"]
        brand_id = brand["musinsa_id"]
        if log_callback:
            log_callback(f"[고객문의] 무신사 {brand_name} 상품 조회 중...")

        products = _get_brand_product_ids_musinsa(brand_id, limit=3)
        if not products:
            if log_callback:
                log_callback(f"[고객문의] 무신사 {brand_name}: 상품 없음")
            continue

        for pid, prod_name in products:
            qa_urls = [
                f"https://www.musinsa.com/products/{pid}/qna",
                f"https://goods.musinsa.com/goods/qna/list.json?goodsNo={pid}&page=1&pageSize=10",
            ]
            for qa_url in qa_urls:
                try:
                    resp = requests.get(qa_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
                    if resp.status_code != 200:
                        continue

                    # JSON 응답 시도
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
                            break
                    except Exception:
                        pass

                    # HTML 파싱 폴백
                    soup = BeautifulSoup(resp.text, "html.parser")
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
                    if qa_items:
                        break

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
