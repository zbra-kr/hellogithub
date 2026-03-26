"""
debug_scrape.py - 실제 수집되는 HTML 구조 진단 스크립트
실행: python debug_scrape.py
결과: debug_output/ 폴더에 HTML 파일 저장
"""
import os, re, json
os.makedirs("debug_output", exist_ok=True)

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")

TESTS = [
    ("musinsa_ranking",    "https://www.musinsa.com/ranking/best",
     "[class*='GoodsItem'],[class*='goods-item'],li[class*='item']"),
    ("musinsa_brand_covernat", "https://www.musinsa.com/brand/covernat",
     "[class*='GoodsItem'],[class*='goods-item'],a[href*='/products/']"),
    ("musinsa_brand_matinkim", "https://www.musinsa.com/brand/matinkim",
     "[class*='GoodsItem'],a[href*='/products/']"),
    ("29cm_best",          "https://shop.29cm.co.kr/best-items",
     "[class*='ProductItem'],[class*='RankItem'],li[class*='item']"),
    ("29cm_covernat",      "https://shop.29cm.co.kr/brand/15404",
     "[class*='ProductItem'],li[class*='item']"),
]

def fetch(pw, url, wait_sel):
    browser = pw.chromium.launch(headless=True, args=[
        "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
    ])
    ctx = browser.new_context(user_agent=UA, locale="ko-KR",
                               viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.add_init_script("""
        delete Object.getPrototypeOf(navigator).webdriver;
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
        Object.defineProperty(navigator,'languages',{get:()=>['ko-KR','ko','en-US']});
    """)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_selector(wait_sel, timeout=15000)
            print(f"  ✅ selector 발견: {wait_sel[:50]}")
        except:
            print(f"  ❌ selector 미발견 (timeout)")
        html = page.content()
    except Exception as e:
        html = f"ERROR: {e}"
        print(f"  ❌ 로딩 실패: {e}")
    finally:
        ctx.close()
        browser.close()
    return html

def analyze(name, html):
    if html.startswith("ERROR"):
        return

    # __NEXT_DATA__ 존재 여부
    nd = re.search(r'<script[^>]+id="__NEXT_DATA__"', html)
    print(f"  __NEXT_DATA__: {'있음' if nd else '없음'}")

    # 상품 링크 수
    prod_links = re.findall(r'href="[^"]*?/products?/\d+', html)
    print(f"  상품 링크(/products/): {len(prod_links)}개")

    # 봇 감지 단서
    for kw in ["captcha", "CAPTCHA", "로그인", "접근이 제한", "403", "blocked", "Blocked"]:
        if kw in html:
            print(f"  ⚠️  '{kw}' 감지됨")

    # __NEXT_DATA__ 내 product key 탐색
    if nd:
        m2 = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*(.*?)\s*</script>', html, re.DOTALL)
        if m2:
            try:
                data = json.loads(m2.group(1))
                txt = json.dumps(data, ensure_ascii=False)
                for key in ["goodsName","itemName","brandName","goodsNo","productId"]:
                    cnt = txt.count(f'"{key}"')
                    if cnt:
                        print(f"  JSON key '{key}': {cnt}회")
            except:
                print("  __NEXT_DATA__ JSON 파싱 실패")

    # HTML 첫 500자 (페이지 타입 파악)
    body = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
    body = re.sub(r'<style.*?</style>', '', body, flags=re.DOTALL)
    body = re.sub(r'<[^>]+>', ' ', body)
    body = re.sub(r'\s+', ' ', body).strip()[:500]
    print(f"  텍스트 미리보기: {body[:300]}")

with sync_playwright() as pw:
    for name, url, sel in TESTS:
        print(f"\n{'='*60}")
        print(f"[{name}] {url}")
        html = fetch(pw, url, sel)
        out_path = f"debug_output/{name}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  저장: {out_path} ({len(html):,}bytes)")
        analyze(name, html)

print("\n\n진단 완료. debug_output/ 폴더의 HTML 파일을 확인하세요.")
