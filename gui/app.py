# gui/app.py - 메인 GUI 애플리케이션

import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import schedule
import time
import os
import subprocess
import sys

from collectors.korean_news import collect_korean_ai_news
from collectors.weather import collect_weather
from collectors.world_news import collect_world_news
from utils.excel_writer import save_to_excel
from config import SCHEDULE_TIME, OUTPUT_DIR


class RPAApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("일일 AI·날씨·뉴스 RPA 리포트")
        self.geometry("820x640")
        self.resizable(True, True)
        self.configure(bg="#1A1A2E")

        # 상태 변수
        self._is_running = False
        self._log_queue = queue.Queue()
        self._last_file = None
        self._scheduler_thread = None
        self._stop_scheduler = threading.Event()

        self._build_ui()
        self._start_scheduler()
        self._poll_log_queue()

    # ─────────────────────────────────────────
    # UI 구성
    # ─────────────────────────────────────────

    def _build_ui(self):
        # 타이틀 바
        title_frame = tk.Frame(self, bg="#1A1A2E", pady=12)
        title_frame.pack(fill="x")

        tk.Label(
            title_frame,
            text="📋  일일 AI · 날씨 · 뉴스 RPA 리포트",
            font=("맑은 고딕", 16, "bold"),
            fg="#E0E0E0",
            bg="#1A1A2E",
        ).pack(side="left", padx=20)

        # 스케줄 시간 표시
        self._schedule_label = tk.Label(
            title_frame,
            text=f"⏰  매일 {SCHEDULE_TIME} 자동 실행",
            font=("맑은 고딕", 10),
            fg="#80CBC4",
            bg="#1A1A2E",
        )
        self._schedule_label.pack(side="right", padx=20)

        # 구분선
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10)

        # 상태 패널
        status_frame = tk.Frame(self, bg="#16213E", pady=8, padx=16)
        status_frame.pack(fill="x", padx=10, pady=(8, 0))

        tk.Label(
            status_frame, text="상태:", font=("맑은 고딕", 9, "bold"),
            fg="#AAAAAA", bg="#16213E"
        ).grid(row=0, column=0, sticky="w")

        self._status_var = tk.StringVar(value="대기 중")
        self._status_label = tk.Label(
            status_frame,
            textvariable=self._status_var,
            font=("맑은 고딕", 9),
            fg="#69F0AE",
            bg="#16213E",
            width=40,
            anchor="w",
        )
        self._status_label.grid(row=0, column=1, sticky="w", padx=8)

        tk.Label(
            status_frame, text="마지막 실행:",
            font=("맑은 고딕", 9, "bold"),
            fg="#AAAAAA", bg="#16213E"
        ).grid(row=0, column=2, sticky="w", padx=(20, 0))

        self._last_run_var = tk.StringVar(value="-")
        tk.Label(
            status_frame,
            textvariable=self._last_run_var,
            font=("맑은 고딕", 9),
            fg="#FFD740",
            bg="#16213E",
        ).grid(row=0, column=3, sticky="w", padx=8)

        # 버튼 패널
        btn_frame = tk.Frame(self, bg="#1A1A2E", pady=10)
        btn_frame.pack(fill="x", padx=10)

        btn_style = {
            "font": ("맑은 고딕", 10, "bold"),
            "relief": "flat",
            "cursor": "hand2",
            "padx": 18,
            "pady": 8,
            "bd": 0,
        }

        self._collect_btn = tk.Button(
            btn_frame,
            text="▶  지금 수집 실행",
            bg="#2E75B6",
            fg="white",
            activebackground="#1B4F8A",
            activeforeground="white",
            command=self._on_collect_click,
            **btn_style,
        )
        self._collect_btn.pack(side="left", padx=(0, 8))

        self._open_btn = tk.Button(
            btn_frame,
            text="📂  결과 폴더 열기",
            bg="#37474F",
            fg="white",
            activebackground="#263238",
            activeforeground="white",
            command=self._open_output_folder,
            **btn_style,
        )
        self._open_btn.pack(side="left", padx=(0, 8))

        self._open_file_btn = tk.Button(
            btn_frame,
            text="📄  최근 파일 열기",
            bg="#37474F",
            fg="white",
            activebackground="#263238",
            activeforeground="white",
            command=self._open_last_file,
            **btn_style,
        )
        self._open_file_btn.pack(side="left", padx=(0, 8))

        # 진행 바
        progress_frame = tk.Frame(self, bg="#1A1A2E", pady=4)
        progress_frame.pack(fill="x", padx=10)

        self._progress = ttk.Progressbar(
            progress_frame, mode="indeterminate", length=780
        )
        self._progress.pack(fill="x")

        # 로그 패널
        log_frame = tk.Frame(self, bg="#1A1A2E", pady=4)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(4, 0))

        tk.Label(
            log_frame, text="실행 로그",
            font=("맑은 고딕", 9, "bold"),
            fg="#AAAAAA", bg="#1A1A2E"
        ).pack(anchor="w")

        self._log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#0D1117",
            fg="#C9D1D9",
            insertbackground="white",
            relief="flat",
            bd=4,
            state="disabled",
        )
        self._log_text.pack(fill="both", expand=True)

        # 태그 색상
        self._log_text.tag_config("INFO", foreground="#79C0FF")
        self._log_text.tag_config("OK", foreground="#56D364")
        self._log_text.tag_config("WARN", foreground="#E3B341")
        self._log_text.tag_config("ERROR", foreground="#FF7B72")
        self._log_text.tag_config("TIME", foreground="#6E7681")

        # 하단 바
        footer = tk.Frame(self, bg="#0D1117", pady=4)
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text=f"저장 위치: {OUTPUT_DIR}",
            font=("맑은 고딕", 8),
            fg="#555555",
            bg="#0D1117",
        ).pack(side="left", padx=10)

    # ─────────────────────────────────────────
    # 로그 처리
    # ─────────────────────────────────────────

    def _log(self, message: str, level: str = "INFO"):
        """로그 큐에 메시지 추가 (스레드 안전)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_queue.put((timestamp, message, level))

    def _poll_log_queue(self):
        """큐에서 로그를 꺼내 UI에 표시 (메인 스레드)"""
        try:
            while True:
                timestamp, message, level = self._log_queue.get_nowait()
                self._log_text.configure(state="normal")
                self._log_text.insert("end", f"[{timestamp}] ", "TIME")
                self._log_text.insert("end", f"{message}\n", level)
                self._log_text.see("end")
                self._log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    # ─────────────────────────────────────────
    # 수집 실행
    # ─────────────────────────────────────────

    def _on_collect_click(self):
        if self._is_running:
            messagebox.showinfo("알림", "현재 수집이 진행 중입니다.")
            return
        self._run_collection()

    def _run_collection(self):
        """별도 스레드에서 데이터 수집 실행"""
        if self._is_running:
            return
        self._is_running = True
        self._set_collecting_state(True)
        thread = threading.Thread(target=self._collect_all, daemon=True)
        thread.start()

    def _collect_all(self):
        """실제 수집 로직 (백그라운드 스레드)"""
        try:
            self._log("=" * 50, "TIME")
            self._log("데이터 수집을 시작합니다.", "INFO")

            # 1. 날씨 수집
            self._set_status("날씨 정보 수집 중...")
            weather_data = collect_weather(log_callback=lambda m: self._log(m, "INFO"))

            # 2. 한국 AI 뉴스 수집
            self._set_status("한국 AI 뉴스 수집 중...")
            korean_news = collect_korean_ai_news(log_callback=lambda m: self._log(m, "INFO"))

            # 3. 세계 뉴스 수집
            self._set_status("세계 주요 뉴스 수집 중...")
            world_news = collect_world_news(log_callback=lambda m: self._log(m, "INFO"))

            # 4. 엑셀 저장
            self._set_status("엑셀 파일 저장 중...")
            filepath = save_to_excel(
                korean_news, weather_data, world_news,
                log_callback=lambda m: self._log(m, "OK")
            )
            self._last_file = filepath

            # 완료
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._last_run_var.set(now_str)
            self._set_status("수집 완료")
            self._log(f"✅  수집 완료! 날씨 {len(weather_data)}건, AI뉴스 {len(korean_news)}건, 세계뉴스 {len(world_news)}건", "OK")
            self._log(f"📄  저장: {filepath}", "OK")

        except Exception as e:
            self._log(f"❌  오류 발생: {e}", "ERROR")
            self._set_status("오류 발생")
        finally:
            self._is_running = False
            self._set_collecting_state(False)

    # ─────────────────────────────────────────
    # 스케줄러
    # ─────────────────────────────────────────

    def _start_scheduler(self):
        schedule.every().day.at(SCHEDULE_TIME).do(self._run_collection)
        self._log(f"스케줄러 설정: 매일 {SCHEDULE_TIME}에 자동 실행", "INFO")

        def _scheduler_loop():
            while not self._stop_scheduler.is_set():
                schedule.run_pending()
                time.sleep(30)

        self._scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    # ─────────────────────────────────────────
    # UI 유틸
    # ─────────────────────────────────────────

    def _set_status(self, msg: str):
        self._status_var.set(msg)

    def _set_collecting_state(self, collecting: bool):
        if collecting:
            self._collect_btn.configure(state="disabled", bg="#555555", text="⏳  수집 중...")
            self._progress.start(12)
        else:
            self._collect_btn.configure(state="normal", bg="#2E75B6", text="▶  지금 수집 실행")
            self._progress.stop()

    def _open_output_folder(self):
        try:
            if sys.platform == "win32":
                os.startfile(OUTPUT_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", OUTPUT_DIR])
            else:
                subprocess.Popen(["xdg-open", OUTPUT_DIR])
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 열 수 없습니다:\n{e}")

    def _open_last_file(self):
        if not self._last_file or not os.path.exists(self._last_file):
            messagebox.showinfo("알림", "아직 생성된 파일이 없습니다.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(self._last_file)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self._last_file])
            else:
                subprocess.Popen(["xdg-open", self._last_file])
        except Exception as e:
            messagebox.showerror("오류", f"파일을 열 수 없습니다:\n{e}")

    def on_close(self):
        self._stop_scheduler.set()
        self.destroy()
