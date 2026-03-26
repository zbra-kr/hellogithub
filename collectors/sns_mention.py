# collectors/sns_mention.py - SNS 브랜드 멘션 수집기

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


def _extract_count(html: str) -> str:
    patterns = [
        r'"edge_hashtag_to_media"[^}]*"count"\s*:\s*(\d+)',
        r'"media_count"\s*:\s*(\d+)',
        r'"count"\s*:\s*(\d+)',
        r'([\d,]+)\s*posts',
        r'게시물\s*([\d,]+)',
    ]
    for p in patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            if raw.isdigit():
                return f"{int(raw):,}"

    # script[type=application/json] 탐색
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/json"):
        try:
            text = json.dumps(json.loads(script.string or ""))
            for p in patterns:
                m = re.search(p, text, re.IGNORECASE)
                if m:
                    raw = m.group(1).replace(",", "")
                    if raw.isdigit():
                        return f"{int(raw):,}"
        except Exception:
            continue
    return "-"


def _fetch_instagram_tag(tag: str) -> dict:
    tag = tag.lstrip("#")
    url = f"https://www.instagram.com/explore/tags/{tag}/"
    result = {"해시태그": f"#{tag}", "총게시물수": "-", "메모": ""}

    if _HAS_PW:
        try:
            html = _pw_fetch(
                url,
                wait_selector="article,header,[class*='_aagw'],[class*='hashtag']",
                timeout_ms=18000,
                extra_headers={"Referer": "https://www.instagram.com/"},
            )
            count = _extract_count(html)
            result["총게시물수"] = count
            if count == "-":
                result["메모"] = "로그인 없이는 수집 제한"
        except Exception as e:
            result["메모"] = f"Playwright 오류: {e}"
    else:
        try:
            headers = {**REQUEST_HEADERS, "Accept": "text/html,*/*;q=0.8"}
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (401, 403):
                result["메모"] = "로그인 필요 (Playwright 설치 권장)"
                return result
            count = _extract_count(resp.text)
            result["총게시물수"] = count
            if count == "-":
                result["메모"] = "파싱 실패 (Playwright 설치 권장)"
        except Exception as e:
            result["메모"] = f"오류: {e}"
    return result


def collect_sns_mention(log_callback=None) -> list[dict]:
    all_results = []
    for brand in OWN_BRANDS:
        brand_name = brand["name"]
        insta_handle = brand.get("insta", "")

        tags_to_check = [brand_name]
        if insta_handle and insta_handle != brand_name:
            tags_to_check.append(insta_handle)

        for tag in tags_to_check:
            if log_callback:
                log_callback(f"[SNS멘션] Instagram #{tag} 수집 중... {'(Playwright)' if _HAS_PW else ''}")
            tag_data = _fetch_instagram_tag(tag)
            all_results.append({
                "브랜드": brand_name,
                "해시태그": tag_data["해시태그"],
                "총게시물수": tag_data["총게시물수"],
                "최근24h추정": "-",
                "메모": tag_data.get("메모", ""),
                "수집시각": _now(),
            })

    if log_callback:
        log_callback(f"[SNS멘션] 전체 완료: {len(all_results)}건")
    return all_results
