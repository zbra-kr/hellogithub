# collectors/korean_news.py - 한국 AI 뉴스 수집기

import feedparser
import requests
from datetime import datetime
from config import KOREAN_AI_NEWS_FEEDS, AI_KEYWORDS, KOREAN_NEWS_LIMIT, REQUEST_HEADERS, REQUEST_TIMEOUT


def _is_ai_related(title: str, summary: str = "") -> bool:
    """AI 관련 키워드 포함 여부 확인"""
    text = (title + " " + summary).upper()
    return any(kw.upper() in text for kw in AI_KEYWORDS)


def _parse_published(entry) -> str:
    """발행일 파싱"""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def collect_korean_ai_news(log_callback=None) -> list[dict]:
    """
    한국 IT/AI 뉴스 RSS 피드에서 AI 관련 뉴스를 수집합니다.

    Returns:
        list of dict: [{"출처", "제목", "링크", "발행일", "요약"}, ...]
    """
    results = []

    for feed_info in KOREAN_AI_NEWS_FEEDS:
        source = feed_info["name"]
        url = feed_info["url"]

        if log_callback:
            log_callback(f"[뉴스] {source} 수집 중...")

        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            count = 0
            for entry in feed.entries:
                title = getattr(entry, "title", "").strip()
                summary = getattr(entry, "summary", "").strip()
                link = getattr(entry, "link", "").strip()
                published = _parse_published(entry)

                if not title:
                    continue

                if _is_ai_related(title, summary):
                    # HTML 태그 제거 (간단)
                    import re
                    summary_clean = re.sub(r"<[^>]+>", "", summary)[:200]

                    results.append({
                        "출처": source,
                        "제목": title,
                        "링크": link,
                        "발행일": published,
                        "요약": summary_clean,
                    })
                    count += 1

            if log_callback:
                log_callback(f"[뉴스] {source}: AI 관련 {count}건 수집")

        except Exception as e:
            if log_callback:
                log_callback(f"[뉴스] {source} 오류: {e}")

    # 발행일 기준 정렬, 상위 N개 반환
    results.sort(key=lambda x: x["발행일"], reverse=True)
    return results[:KOREAN_NEWS_LIMIT]
