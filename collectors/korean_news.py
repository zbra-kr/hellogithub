# collectors/korean_news.py - 한국 AI 뉴스 수집기

import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from config import KOREAN_AI_NEWS_FEEDS, AI_KEYWORDS, KOREAN_NEWS_LIMIT, REQUEST_HEADERS, REQUEST_TIMEOUT


def _is_ai_related(title: str, summary: str = "") -> bool:
    text = (title + " " + summary).upper()
    return any(kw.upper() in text for kw in AI_KEYWORDS)


def _parse_rss_date(date_str: str) -> str:
    """RFC 2822 날짜 → 'YYYY-MM-DD HH:MM' 변환"""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")
    # 형식: "Wed, 25 Mar 2026 08:00:00 +0900"
    try:
        from email.utils import parsedate
        t = parsedate(date_str)
        if t:
            return datetime(*t[:5]).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _parse_feed(content: bytes) -> list[dict]:
    """RSS/Atom XML 파싱"""
    entries = []
    try:
        root = ET.fromstring(content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # RSS 2.0
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            summary = (item.findtext("description") or "").strip()
            entries.append({
                "title": title,
                "link": link,
                "published": _parse_rss_date(pub_date),
                "summary": re.sub(r"<[^>]+>", "", summary)[:200],
            })

        # Atom
        if not entries:
            for entry in root.findall("atom:entry", ns):
                title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                pub_date = (entry.findtext("atom:published", namespaces=ns) or "").strip()
                summary = (entry.findtext("atom:summary", namespaces=ns) or "").strip()
                entries.append({
                    "title": title,
                    "link": link,
                    "published": pub_date[:16] if len(pub_date) >= 16 else datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "summary": re.sub(r"<[^>]+>", "", summary)[:200],
                })
    except ET.ParseError:
        pass
    return entries


def collect_korean_ai_news(log_callback=None) -> list[dict]:
    results = []

    for feed_info in KOREAN_AI_NEWS_FEEDS:
        source = feed_info["name"]
        url = feed_info["url"]

        if log_callback:
            log_callback(f"[뉴스] {source} 수집 중...")

        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            entries = _parse_feed(resp.content)

            count = 0
            for entry in entries:
                title = entry["title"]
                summary = entry["summary"]

                if not title:
                    continue
                if _is_ai_related(title, summary):
                    results.append({
                        "출처": source,
                        "제목": title,
                        "링크": entry["link"],
                        "발행일": entry["published"],
                        "요약": summary,
                    })
                    count += 1

            if log_callback:
                log_callback(f"[뉴스] {source}: AI 관련 {count}건 수집")

        except Exception as e:
            if log_callback:
                log_callback(f"[뉴스] {source} 오류: {e}")

    results.sort(key=lambda x: x["발행일"], reverse=True)
    return results[:KOREAN_NEWS_LIMIT]
