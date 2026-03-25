# collectors/sns_trend.py - SNS 트렌드 해시태그 수집기
# Playwright 사용 시 Instagram/TikTok JS 렌더링 데이터 수집 가능

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import FASHION_HASHTAGS, REQUEST_HEADERS, REQUEST_TIMEOUT

try:
    from utils.browser import fetch_page as _pw_fetch
    _HAS_PW = True
except ImportError:
    _HAS_PW = False


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _extract_count_from_html(html: str) -> str:
    """HTML/JSON에서 게시물 수 추출 (다양한 패턴 시도)"""
    patterns = [
        r'"edge_hashtag_to_media"[^}]*"count"\s*:\s*(\d+)',
        r'"media_count"\s*:\s*(\d+)',
        r'"count"\s*:\s*(\d+)',
        r'게시물\s*([\d,]+)\s*개',
        r'([\d,]+)\s*posts',
        r'"videoCount"\s*:\s*(\d+)',    # TikTok
        r'"view_count"\s*:\s*(\d+)',
    ]
    for p in patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            if raw.isdigit():
                return f"{int(raw):,}"
    return "-"


def _parse_instagram_html(html: str) -> str:
    """렌더링된 Instagram HTML에서 게시물 수 추출"""
    soup = BeautifulSoup(html, "html.parser")

    # script[type=application/json] 탐색
    for script in soup.find_all("script", type="application/json"):
        try:
            data = json.loads(script.string or "")
            text = json.dumps(data)
            count = _extract_count_from_html(text)
            if count != "-":
                return count
        except Exception:
            continue

    # window._sharedData 탐색
    m = re.search(r'window\._sharedData\s*=\s*({.*?});</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            hashtag_data = (
                data.get("entry_data", {})
                .get("TagPage", [{}])[0]
                .get("graphql", {})
                .get("hashtag", {})
            )
            count = hashtag_data.get("edge_hashtag_to_media", {}).get("count")
            if count:
                return f"{int(count):,}"
        except Exception:
            pass

    # __additionalData 탐색 (새 Instagram 구조)
    m2 = re.search(r'"__additionalData"\s*:\s*({.*?})\s*[,}]', html, re.DOTALL)
    if m2:
        count = _extract_count_from_html(m2.group(1))
        if count != "-":
            return count

    # 페이지 전체 텍스트에서 직접 탐색
    return _extract_count_from_html(html)


def _parse_tiktok_html(html: str) -> str:
    """렌더링된 TikTok HTML에서 조회수 추출"""
    soup = BeautifulSoup(html, "html.parser")

    # SIGI_STATE JSON
    m = re.search(r'<script[^>]+id="SIGI_STATE"[^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            text = json.dumps(data)
            count = _extract_count_from_html(text)
            if count != "-":
                return count
        except Exception:
            pass

    # __UNIVERSAL_DATA_FOR_REHYDRATION__
    m2 = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__["\s]*=\s*({.*?})\s*</script>', html, re.DOTALL)
    if m2:
        count = _extract_count_from_html(m2.group(1))
        if count != "-":
            return count

    # data-e2e 속성
    view_el = soup.select_one("[data-e2e*='challenge-vv'],[data-e2e*='view'],[class*='videoCount']")
    if view_el:
        text = view_el.get_text(strip=True)
        if text:
            return text

    return _extract_count_from_html(html)


def collect_instagram_hashtag(hashtag: str, log_callback=None) -> dict:
    tag = hashtag.lstrip("#")
    url = f"https://www.instagram.com/explore/tags/{tag}/"
    result = {
        "플랫폼": "Instagram", "해시태그": f"#{tag}",
        "게시물수": "-", "조회수": "-", "수집시각": _now(), "메모": "",
    }

    if _HAS_PW:
        # Playwright: JS 완전 렌더링 후 파싱
        try:
            html = _pw_fetch(
                url,
                wait_selector="article,header,[class*='_aagw'],[class*='hashtag']",
                timeout_ms=18000,
                extra_headers={"Referer": "https://www.instagram.com/"},
            )
            count = _parse_instagram_html(html)
            result["게시물수"] = count
            if count == "-":
                result["메모"] = "로그인 없이는 수집 제한"
            return result
        except Exception as e:
            result["메모"] = f"Playwright 오류: {e}"
            return result
    else:
        # requests 폴백
        try:
            headers = {**REQUEST_HEADERS, "Accept": "text/html,*/*;q=0.8"}
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (401, 403):
                result["메모"] = "로그인 필요 (Playwright 설치 권장)"
                return result
            count = _parse_instagram_html(resp.text)
            result["게시물수"] = count
            if count == "-":
                result["메모"] = "파싱 실패 (Playwright 설치 권장)"
        except Exception as e:
            result["메모"] = f"오류: {e}"
        return result


def collect_tiktok_hashtag(hashtag: str, log_callback=None) -> dict:
    tag = hashtag.lstrip("#")
    url = f"https://www.tiktok.com/tag/{tag}"
    result = {
        "플랫폼": "TikTok", "해시태그": f"#{tag}",
        "게시물수": "-", "조회수": "-", "수집시각": _now(), "메모": "",
    }

    if _HAS_PW:
        try:
            html = _pw_fetch(
                url,
                wait_selector="[data-e2e*='challenge'],[class*='challenge-num'],[class*='videoCount']",
                timeout_ms=20000,
                extra_headers={"Referer": "https://www.tiktok.com/"},
            )
            count = _parse_tiktok_html(html)
            result["조회수"] = count
            if count == "-":
                result["메모"] = "TikTok 봇 차단 가능성"
            return result
        except Exception as e:
            result["메모"] = f"Playwright 오류: {e}"
            return result
    else:
        try:
            headers = {**REQUEST_HEADERS, "Referer": "https://www.tiktok.com/"}
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (403, 429):
                result["메모"] = "접근 차단 (Playwright 설치 권장)"
                return result
            count = _parse_tiktok_html(resp.text)
            result["조회수"] = count
            if count == "-":
                result["메모"] = "파싱 실패 (Playwright 설치 권장)"
        except Exception as e:
            result["메모"] = f"오류: {e}"
        return result


def collect_sns_trend(log_callback=None) -> list[dict]:
    all_results = []
    for tag in FASHION_HASHTAGS:
        if log_callback:
            log_callback(f"[SNS트렌드] Instagram #{tag} 수집 중...")
        all_results.append(collect_instagram_hashtag(tag, log_callback=log_callback))

        if log_callback:
            log_callback(f"[SNS트렌드] TikTok #{tag} 수집 중...")
        all_results.append(collect_tiktok_hashtag(tag, log_callback=log_callback))

    if log_callback:
        log_callback(f"[SNS트렌드] 수집 완료: {len(all_results)}건")
    return all_results
