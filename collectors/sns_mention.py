# collectors/sns_mention.py - SNS 브랜드 멘션 수집기

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import OWN_BRANDS, REQUEST_HEADERS, REQUEST_TIMEOUT


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fetch_instagram_tag(tag: str) -> dict:
    """인스타그램 공개 해시태그 페이지에서 게시물 수 추출"""
    tag = tag.lstrip("#")
    url = f"https://www.instagram.com/explore/tags/{tag}/"
    result = {
        "해시태그": f"#{tag}",
        "총게시물수": "-",
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
            result["총게시물수"] = f"{count:,}" if isinstance(count, int) else str(count)
            return result

        # script[type=application/json] 탐색
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", type="application/json"):
            try:
                data = json.loads(script.string or "")
                text = json.dumps(data)
                count_match = re.search(r'"count"\s*:\s*(\d+)', text)
                if count_match:
                    result["총게시물수"] = f"{int(count_match.group(1)):,}"
                    return result
            except Exception:
                continue

        # 텍스트 직접 탐색
        count_match = re.search(r'"edge_hashtag_to_media"[^}]*"count"\s*:\s*(\d+)', html)
        if count_match:
            result["총게시물수"] = f"{int(count_match.group(1)):,}"
        else:
            result["메모"] = "파싱 불가 (Instagram 구조 변경 가능성)"

    except Exception as e:
        result["메모"] = f"오류: {e}"
    return result


def collect_sns_mention(log_callback=None) -> list[dict]:
    """자사 브랜드 인스타그램 멘션 수집"""
    all_results = []

    for brand in OWN_BRANDS:
        brand_name = brand["name"]
        insta_handle = brand.get("insta", "")

        # 브랜드명 해시태그 + 공식 계정명 해시태그 검색
        tags_to_check = [brand_name]
        if insta_handle and insta_handle != brand_name:
            tags_to_check.append(insta_handle)

        for tag in tags_to_check:
            if log_callback:
                log_callback(f"[SNS멘션] Instagram #{tag} 수집 중...")
            tag_data = _fetch_instagram_tag(tag)
            all_results.append({
                "브랜드": brand_name,
                "해시태그": tag_data["해시태그"],
                "총게시물수": tag_data["총게시물수"],
                "최근24h추정": "-",  # 로그인 없이는 수집 불가
                "메모": tag_data.get("메모", ""),
                "수집시각": _now(),
            })

    if log_callback:
        log_callback(f"[SNS멘션] 전체 완료: {len(all_results)}건")
    return all_results


if __name__ == "__main__":
    data = collect_sns_mention(log_callback=print)
    for row in data:
        print(row)
