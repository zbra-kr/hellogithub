@echo off
REM ─────────────────────────────────────────────────────────────
REM  RPA 일일 리포트 - Windows .exe 빌드 스크립트
REM  실행 방법: build_exe.bat
REM ─────────────────────────────────────────────────────────────

echo [1/4] 가상환경 확인 및 패키지 설치...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [2/4] 기존 빌드 파일 정리...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist rpa_report.spec del /q rpa_report.spec

echo.
echo [3/4] PyInstaller로 .exe 빌드 중...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "RPA_일일리포트" ^
  --add-data "config.py;." ^
  --add-data "collectors;collectors" ^
  --add-data "utils;utils" ^
  --add-data "gui;gui" ^
  main.py

echo.
echo [4/4] 빌드 완료!
echo.
echo   결과 파일: dist\RPA_일일리포트.exe
echo   해당 파일을 원하는 위치로 복사 후 실행하세요.
echo.

pause
