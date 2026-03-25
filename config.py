# config.py - 설정 파일

import os

# 스케줄 설정
SCHEDULE_TIME = "08:00"  # 매일 실행 시각 (HH:MM)

# 날씨 설정 (wttr.in 무료 API, 키 불필요)
WEATHER_CITIES = [
    {"name": "서울", "query": "Seoul"},
    {"name": "부산", "query": "Busan"},
]

# 한국 AI 뉴스 RSS 피드
KOREAN_AI_NEWS_FEEDS = [
    {"name": "전자신문", "url": "https://rss.etnews.com/Section901.xml"},
    {"name": "ZDNet Korea", "url": "https://www.zdnet.co.kr/rss/"},
    {"name": "연합뉴스 IT", "url": "https://www.yonhapnewstv.co.kr/browse/feeds/rss/category/tech"},
    {"name": "ITWorld", "url": "https://www.itworld.co.kr/rss.xml"},
    {"name": "디지털투데이", "url": "http://www.digitaltoday.co.kr/rss/allArticle.xml"},
]

# AI 관련 키워드 필터
AI_KEYWORDS = [
    "AI", "인공지능", "머신러닝", "딥러닝", "LLM", "챗GPT", "ChatGPT",
    "GPT", "Claude", "Gemini", "생성형", "자동화", "로봇", "데이터",
    "반도체", "엔비디아", "NVIDIA", "OpenAI", "Anthropic", "Google AI"
]

# 세계 뉴스 RSS 피드
WORLD_NEWS_FEEDS = [
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Reuters", "url": "https://feeds.reuters.com/reuters/topNews"},
    {"name": "AP News", "url": "https://feeds.apnews.com/rss/topnews"},
    {"name": "CNN", "url": "http://rss.cnn.com/rss/edition_world.rss"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
]

# 수집 개수 설정
KOREAN_NEWS_LIMIT = 10    # 한국 AI 뉴스 최대 수집 개수
WORLD_NEWS_LIMIT = 5      # 세계 뉴스 수집 개수

# 엑셀 저장 경로
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "RPA_Reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# HTTP 요청 설정
REQUEST_TIMEOUT = 15      # 초
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
