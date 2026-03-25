# collectors/sns_trend.py - SNS 트렌드 해시태그 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import FASHION_HASHTAGS, REQUEST_HEADERS, REQUEST_TIMEOUT


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def collect_instagram_hashtag(hashtag: str, log_callback=None) -> dict:
    """인스타그램 공개 해시태그 페이지에서 데이터 수집"""
    tag = hashtag.lstrip("#")
    url = f"https://www.instagram.com/explore/tags/{tag}/"
    result = {
        "플랫폼": "Instagram",
        "해시태그": f"#{tag}",
        "게시물수": "-",
        "조회수": "-",
        "수집시각": _now(),
        "메모": "",
    }
    try:
        headers = dict(REQUEST_HEADERS)
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

        if resp.status_code in (401, 403):
            result["메모"] = "로그인 필요 또는 접근 차단"
            return result

        html = resp.text

        # window._sharedData 추출 시도
        match = re.search(r'window\._sharedData\s*=\s*({.*?});</script>', html, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            hashtag_data = (
                data.get("entry_data", {})
                .get("TagPage", [{}])[0]
                .get("graphql", {})
                .get("hashtag", {})
            )
            count = hashtag_data.get("edge_hashtag_to_media", {}).get("count", "-")
            result["게시물수"] = f"{count:,}" if isinstance(count, int) else str(count)
            return result

        # script 태그 내 JSON 탐색
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", type="application/json"):
            try:
                data = json.loads(script.string or "")
                # 중첩 구조에서 count 탐색
                text = json.dumps(data)
                count_match = re.search(r'"count"\s*:\s*(\d+)', text)
                if count_match:
                    count = int(count_match.group(1))
                    result["게시물수"] = f"{count:,}"
                    return result
            except Exception:
                continue

        # 텍스트에서 직접 탐색
        count_match = re.search(r'"edge_hashtag_to_media"[^}]*"count"\s*:\s*(\d+)', html)
        if count_match:
            result["게시물수"] = f"{int(count_match.group(1)):,}"
        else:
            result["메모"] = "파싱 불가 (Instagram 구조 변경 가능)"

    except Exception as e:
        result["메모"] = f"오류: {e}"
    return result


def collect_tiktok_hashtag(hashtag: str, log_callback=None) -> dict:
    """틱톡 공개 해시태그 페이지에서 데이터 수집"""
    tag = hashtag.lstrip("#")
    url = f"https://www.tiktok.com/tag/{tag}"
    result = {
        "플랫폼": "TikTok",
        "해시태그": f"#{tag}",
        "게시물수": "-",
        "조회수": "-",
        "수집시각": _now(),
        "메모": "",
    }
    try:
        headers = dict(REQUEST_HEADERS)
        headers["Referer"] = "https://www.tiktok.com/"
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

        if resp.status_code in (403, 429):
            result["메모"] = "접근 차단 또는 봇 감지"
            return result

        html = resp.text

        # SIGI_STATE JSON 추출 시도
        match = re.search(r'<script[^>]+id="SIGI_STATE"[^>]*>(.*?)</script>', html, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            challenge = data.get("ChallengePage", {}).get("challengeInfo", {}).get("challenge", {})
            view_count = challenge.get("stats", {}).get("videoCount", "-")
            result["조회수"] = f"{view_count:,}" if isinstance(view_count, int) else str(view_count)
            return result

        # __UNIVERSAL_DATA__ 추출 시도
        match2 = re.search(r'window\["__UNIVERSAL_DATA_FOR_REHYDRATION__"\]\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
        if match2:
            data = json.loads(match2.group(1))
            text = json.dumps(data)
            view_match = re.search(r'"videoCount"\s*:\s*(\d+)', text)
            if view_match:
                result["조회수"] = f"{int(view_match.group(1)):,}"
                return result

        # 일반 텍스트 파싱
        soup = BeautifulSoup(html, "html.parser")
        view_el = soup.select_one("[class*='videoCount'], [data-e2e*='challenge-views']")
        if view_el:
            result["조회수"] = view_el.get_text(strip=True)
        else:
            result["메모"] = "파싱 불가 (TikTok 구조 변경 가능)"

    except Exception as e:
        result["메모"] = f"오류: {e}"
    return result


def collect_sns_trend(log_callback=None) -> list[dict]:
    """인스타그램 + 틱톡 패션 해시태그 트렌드 수집"""
    all_results = []

    for tag in FASHION_HASHTAGS:
        if log_callback:
            log_callback(f"[SNS트렌드] Instagram #{tag} 수집 중...")
        ig_result = collect_instagram_hashtag(tag, log_callback=log_callback)
        all_results.append(ig_result)

        if log_callback:
            log_callback(f"[SNS트렌드] TikTok #{tag} 수집 중...")
        tt_result = collect_tiktok_hashtag(tag, log_callback=log_callback)
        all_results.append(tt_result)

    if log_callback:
        log_callback(f"[SNS트렌드] 수집 완료: {len(all_results)}건")
    return all_results


if __name__ == "__main__":
    data = collect_sns_trend(log_callback=print)
    for row in data[:4]:
        print(row)
