@echo off
echo ========================================
echo  Playwright Chromium 설치
echo ========================================

python -m pip install playwright>=1.40.0
if errorlevel 1 (
    echo [오류] playwright 설치 실패
    pause
    exit /b 1
)

python -m playwright install chromium
if errorlevel 1 (
    echo [오류] Chromium 브라우저 설치 실패
    pause
    exit /b 1
)

echo.
echo ========================================
echo  설치 완료! Playwright + Chromium 사용 가능
echo ========================================
pause
