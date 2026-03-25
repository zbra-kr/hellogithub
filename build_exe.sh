#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  RPA 일일 리포트 - Linux/macOS 빌드 스크립트
#  (Windows .exe는 Windows에서 build_exe.bat 사용)
# ─────────────────────────────────────────────────────────────

set -e

echo "[1/4] 패키지 설치..."
pip install -r requirements.txt
pip install pyinstaller

echo ""
echo "[2/4] 기존 빌드 파일 정리..."
rm -rf dist build RPA_일일리포트.spec

echo ""
echo "[3/4] PyInstaller로 바이너리 빌드 중..."
pyinstaller \
  --onefile \
  --windowed \
  --name "RPA_일일리포트" \
  --add-data "config.py:." \
  --add-data "collectors:collectors" \
  --add-data "utils:utils" \
  --add-data "gui:gui" \
  main.py

echo ""
echo "[4/4] 빌드 완료!"
echo ""
echo "  결과 파일: dist/RPA_일일리포트"
echo ""
