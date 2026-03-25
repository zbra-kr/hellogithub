#!/bin/bash
echo "========================================"
echo " Playwright Chromium 설치"
echo "========================================"

python3 -m pip install "playwright>=1.40.0"
if [ $? -ne 0 ]; then
    echo "[오류] playwright 설치 실패"
    exit 1
fi

python3 -m playwright install chromium
if [ $? -ne 0 ]; then
    echo "[오류] Chromium 브라우저 설치 실패"
    exit 1
fi

echo ""
echo "========================================"
echo " 설치 완료! Playwright + Chromium 사용 가능"
echo "========================================"
