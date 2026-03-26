# utils/browser.py - Playwright 기반 브라우저 래퍼
#
# 역할:
#   - JS 렌더링이 필요한 사이트(무신사, 29CM, Instagram, TikTok 등)를
#     headless Chromium으로 완전 렌더링 후 HTML 반환
#   - 싱글턴 Browser 인스턴스 재사용 (성능),  컨텍스트는 요청마다 새로 생성 (격리/봇우회)
#   - playwright가 설치되어 있지 않아도 앱이 동작하도록 graceful fallback 지원
#
# 설치 방법:
#   pip install playwright
#   playwright install chromium

import threading

_pw_instance = None
_browser_instance = None
_lock = threading.Lock()


def is_available() -> bool:
    """playwright + chromium 사용 가능 여부 확인"""
    try:
        from playwright.sync_api import sync_playwright  # noqa
        return True
    except ImportError:
        return False


def _get_browser():
    global _pw_instance, _browser_instance
    from playwright.sync_api import sync_playwright

    with _lock:
        if _pw_instance is None:
            _pw_instance = sync_playwright().start()
        if _browser_instance is None or not _browser_instance.is_connected():
            _browser_instance = _pw_instance.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--lang=ko-KR",
                ],
            )
    return _browser_instance


def fetch_page(
    url: str,
    wait_selector: str = None,
    wait_state: str = "networkidle",
    timeout_ms: int = 25000,
    extra_headers: dict = None,
    click_selector: str = None,
) -> str:
    """
    Playwright로 완전 렌더링된 페이지 HTML을 반환합니다.

    Args:
        url           : 요청할 URL
        wait_selector : 이 CSS 셀렉터 요소가 나타날 때까지 대기
                        (None이면 wait_state 기준 대기)
        wait_state    : 'domcontentloaded' | 'networkidle' | 'load'
        timeout_ms    : 전체 타임아웃 (밀리초)
        extra_headers : 추가 HTTP 헤더
        click_selector: 페이지 로드 후 클릭할 셀렉터 (탭 전환 등)

    Returns:
        렌더링 완료된 HTML 문자열
    """
    browser = _get_browser()
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        locale="ko-KR",
        viewport={"width": 1280, "height": 900},
        extra_http_headers={
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
            **(extra_headers or {}),
        },
    )
    page = context.new_page()

    # 봇 감지 회피 스크립트
    page.add_init_script("""
        delete Object.getPrototypeOf(navigator).webdriver;
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US'] });
    """)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        # 특정 버튼/탭 클릭 (리뷰탭, Q&A탭 등)
        if click_selector:
            try:
                page.click(click_selector, timeout=5000)
            except Exception:
                pass

        # 콘텐츠 로드 대기
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=12000)
            except Exception:
                pass  # 셀렉터 미등장 시 현재 상태로 진행
        else:
            try:
                page.wait_for_load_state(wait_state, timeout=12000)
            except Exception:
                pass

        return page.content()
    finally:
        context.close()


def shutdown():
    """앱 종료 시 Playwright/브라우저 인스턴스 정리"""
    global _pw_instance, _browser_instance
    with _lock:
        if _browser_instance:
            try:
                _browser_instance.close()
            except Exception:
                pass
            _browser_instance = None
        if _pw_instance:
            try:
                _pw_instance.stop()
            except Exception:
                pass
            _pw_instance = None
