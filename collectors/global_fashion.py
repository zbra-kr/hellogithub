# collectors/global_fashion.py - 해외 패션 트렌드 뉴스 수집기

import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

from config import GLOBAL_FASHION_FEEDS, REQUEST_HEADERS, REQUEST_TIMEOUT, WORLD_NEWS_LIMIT


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_rss(xml_text: str, source_name: str) -> list[dict]:
    """RSS XML 파싱 후 기사 목록 반환"""
    results = []
    try:
        root = ET.fromstring(xml_text)
        ns = ""
        # Atom 피드 처리
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        channel = root.find(f"{ns}channel") if ns else root.find("channel")
        if channel is None:
            # Atom 형식
            items = root.findall(f"{ns}entry") if ns else root.findall("entry")
        else:
            items = channel.findall("item")

        for item in items[:WORLD_NEWS_LIMIT]:
            title_el = item.find("title")
            link_el = item.find("link")
            pub_el = item.find("pubDate") or item.find("published") or item.find("updated")
            desc_el = item.find("description") or item.find("summary")

            title = title_el.text.strip() if title_el is not None and title_el.text else "-"
            # Atom link는 href 속성
            if link_el is not None:
                link = link_el.text.strip() if link_el.text else link_el.get("href", "-")
            else:
                link = "-"
            pub = pub_el.text.strip() if pub_el is not None and pub_el.text else "-"
            desc = desc_el.text or "" if desc_el is not None else ""
            # HTML 태그 제거
            desc = re.sub(r"<[^>]+>", "", desc).strip()
            if len(desc) > 200:
                desc = desc[:200] + "..."

            results.append({
                "출처": source_name,
                "제목": title,
                "링크": link,
                "발행일": pub,
                "요약": desc,
                "수집시각": _now(),
            })
    except Exception:
        pass
    return results


# BoF RSS URL 후보 (사이트가 자주 변경됨)
_BOF_FALLBACK_URLS = [
    "https://www.businessoffashion.com/feed/",
    "https://www.businessoffashion.com/articles/feed/",
    "https://www.businessoffashion.com/rss/",
    "https://www.businessoffashion.com/feed.xml",
    "https://www.businessoffashion.com/news/feed/",
]


def collect_global_fashion(log_callback=None) -> list[dict]:
    """해외 패션 RSS 피드 수집 (Vogue, WWD, BoF, Hypebeast, Highsnobiety)"""
    all_results = []

    for feed in GLOBAL_FASHION_FEEDS:
        name = feed["name"]
        urls = _BOF_FALLBACK_URLS if name == "Business of Fashion" else [feed["url"]]

        if log_callback:
            log_callback(f"[해외패션] {name} RSS 수집 중...")

        items = []
        for url in urls:
            try:
                resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                items = _parse_rss(resp.text, name)
                if items:
                    break
            except Exception as e:
                if url == urls[-1] and log_callback:
                    log_callback(f"[해외패션] {name} 오류: {e}")

        all_results.extend(items)
        if log_callback:
            log_callback(f"[해외패션] {name}: {len(items)}건 수집")

    if log_callback:
        log_callback(f"[해외패션] 전체 수집 완료: {len(all_results)}건")
    return all_results


if __name__ == "__main__":
    data = collect_global_fashion(log_callback=print)
    for row in data[:5]:
        print(row)
