# config.py
import os

SCHEDULE_TIME = "08:00"

# 자사 브랜드
OWN_BRANDS = [
    {
        "name": "커버낫",
        "url": "https://covernat.co.kr",
        "best_url": "https://covernat.co.kr/product/best",
        "musinsa_id": "covernat",
        "insta": "covernat_official",
        "naver_store_id": "",  # 네이버 스마트스토어 ID (있으면 입력)
    },
    {
        "name": "리",
        "url": "https://leekorea.co.kr",
        "best_url": "https://leekorea.co.kr/product/best",
        "musinsa_id": "leekorea",
        "insta": "leekorea_official",
        "naver_store_id": "",
    },
    {
        "name": "와키윌리",
        "url": "https://wackywilly.co.kr",
        "best_url": "https://wackywilly.co.kr/product/best",
        "musinsa_id": "wackywilly",
        "insta": "wackywilly",
        "naver_store_id": "",
    },
]

# 경쟁사 브랜드 (무신사 브랜드 슬러그)
COMPETITOR_BRANDS = [
    {"name": "마땡킴", "musinsa_id": "mathemkim"},
    {"name": "플리즈노팔로우", "musinsa_id": "pleasenofollow"},
    {"name": "무신사 스탠다드", "musinsa_id": "musinsa-standard"},
    {"name": "아디다스", "musinsa_id": "adidas"},
    {"name": "나이키", "musinsa_id": "nike"},
    {"name": "아웃스탠딩", "musinsa_id": "outstanding"},
    {"name": "닥터마틴", "musinsa_id": "dr-martens"},
    {"name": "폴로 랄프 로렌", "musinsa_id": "polo-ralph-lauren"},
    {"name": "아식스", "musinsa_id": "asics"},
    {"name": "뉴발란스", "musinsa_id": "new-balance"},
    {"name": "디스이즈네버댓", "musinsa_id": "thisisneverthat"},
]

# 무신사 카테고리 코드 (모든 복종)
MUSINSA_CATEGORIES = [
    {"name": "아우터", "code": "001"},
    {"name": "상의", "code": "002"},
    {"name": "바지", "code": "003"},
    {"name": "원피스/스커트", "code": "100"},
    {"name": "신발", "code": "007"},
    {"name": "가방", "code": "012"},
    {"name": "모자", "code": "010"},
    {"name": "시계/쥬얼리", "code": "014"},
]

# 패션 트렌드 해시태그
FASHION_HASHTAGS = [
    "패션", "오오티디", "OOTD", "streetwear", "코디",
    "무신사", "커버낫", "캐주얼", "스트릿패션", "신상",
]

# 해외 패션 뉴스 RSS
GLOBAL_FASHION_FEEDS = [
    {"name": "Vogue", "url": "https://www.vogue.com/feed/rss"},
    {"name": "WWD", "url": "https://wwd.com/feed/"},
    {"name": "Business of Fashion", "url": "https://www.businessoffashion.com/rss"},
    {"name": "Hypebeast", "url": "https://hypebeast.com/feed"},
    {"name": "Highsnobiety", "url": "https://www.highsnobiety.com/feed/"},
]

# 수집 설정
BESTSELLER_LIMIT = 20          # 베스트셀러 수집 개수
COMPETITOR_NEW_LIMIT = 10      # 경쟁사 신상품 수집 개수
REVIEW_LIMIT = 20              # 리뷰 수집 개수
WORLD_NEWS_LIMIT = 10          # 해외 뉴스 수집 개수
PRICE_COMPARE_LIMIT = 10       # 복종당 가격비교 상품 수

# HTTP 설정
REQUEST_TIMEOUT = 15
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "패션_RPA_리포트")
os.makedirs(OUTPUT_DIR, exist_ok=True)
