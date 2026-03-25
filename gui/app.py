# gui/app.py - 패션 브랜드 모니터링 RPA GUI

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

from collectors.bestseller import collect_bestseller
from collectors.sns_trend import collect_sns_trend
from collectors.global_fashion import collect_global_fashion
from collectors.competitor_new import collect_competitor_new
from collectors.price_compare import collect_price_compare
from collectors.promotions import collect_promotions
from collectors.reviews import collect_reviews
from collectors.sns_mention import collect_sns_mention
from collectors.inquiries import collect_inquiries
from utils.excel_writer import save_to_excel
from config import SCHEDULE_TIME, OUTPUT_DIR


class RPAApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("패션 브랜드 일일 모니터링 RPA")
        self.geometry("940x720")
        self.resizable(True, True)
        self.configure(bg="#1A1A1A")

        # 상태 변수
        self._is_running = False
        self._log_queue = queue.Queue()
        self._last_file = None
        self._scheduler_thread = None
        self._stop_scheduler = threading.Event()

        # 수집 항목 체크박스 변수
        self._check_vars = {
            "베스트셀러":    tk.BooleanVar(value=True),
            "트렌드해시태그": tk.BooleanVar(value=True),
            "해외패션뉴스":  tk.BooleanVar(value=True),
            "경쟁사신상품":  tk.BooleanVar(value=True),
            "가격비교":      tk.BooleanVar(value=True),
            "프로모션":      tk.BooleanVar(value=True),
            "리뷰분석":      tk.BooleanVar(value=True),
            "SNS멘션":       tk.BooleanVar(value=True),
            "고객문의":      tk.BooleanVar(value=True),
        }

        self._build_ui()
        self._start_scheduler()
        self._poll_log_queue()

    # ─────────────────────────────────────────
    # UI 구성
    # ─────────────────────────────────────────

    def _build_ui(self):
        # 타이틀 바
        title_frame = tk.Frame(self, bg="#1A1A1A", pady=10)
        title_frame.pack(fill="x")

        tk.Label(
            title_frame,
            text="패션 브랜드 일일 모니터링 RPA",
            font=("맑은 고딕", 16, "bold"),
            fg="#E8C56D",
            bg="#1A1A1A",
        ).pack(side="left", padx=20)

        self._schedule_label = tk.Label(
            title_frame,
            text=f"매일 {SCHEDULE_TIME} 자동 실행",
            font=("맑은 고딕", 10),
            fg="#888888",
            bg="#1A1A1A",
        )
        self._schedule_label.pack(side="right", padx=20)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10)

        # 상태 패널
        status_frame = tk.Frame(self, bg="#111111", pady=8, padx=16)
        status_frame.pack(fill="x", padx=10, pady=(6, 0))

        tk.Label(
            status_frame, text="상태:", font=("맑은 고딕", 9, "bold"),
            fg="#888888", bg="#111111"
        ).grid(row=0, column=0, sticky="w")

        self._status_var = tk.StringVar(value="대기 중")
        self._status_label = tk.Label(
            status_frame,
            textvariable=self._status_var,
            font=("맑은 고딕", 9),
            fg="#69F0AE",
            bg="#111111",
            width=40,
            anchor="w",
        )
        self._status_label.grid(row=0, column=1, sticky="w", padx=8)

        tk.Label(
            status_frame, text="마지막 실행:",
            font=("맑은 고딕", 9, "bold"),
            fg="#888888", bg="#111111"
        ).grid(row=0, column=2, sticky="w", padx=(20, 0))

        self._last_run_var = tk.StringVar(value="-")
        tk.Label(
            status_frame,
            textvariable=self._last_run_var,
            font=("맑은 고딕", 9),
            fg="#E8C56D",
            bg="#111111",
        ).grid(row=0, column=3, sticky="w", padx=8)

        # 탭 구조
        notebook_frame = tk.Frame(self, bg="#1A1A1A")
        notebook_frame.pack(fill="both", expand=True, padx=10, pady=(8, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Fashion.TNotebook",
            background="#1A1A1A",
            tabmargins=[2, 4, 2, 0],
        )
        style.configure(
            "Fashion.TNotebook.Tab",
            background="#2D2D2D",
            foreground="#AAAAAA",
            padding=[12, 6],
            font=("맑은 고딕", 9),
        )
        style.map(
            "Fashion.TNotebook.Tab",
            background=[("selected", "#1A1A1A")],
            foreground=[("selected", "#E8C56D")],
        )

        self._notebook = ttk.Notebook(notebook_frame, style="Fashion.TNotebook")
        self._notebook.pack(fill="both", expand=True)

        # 탭 1: 대시보드
        tab_dash = tk.Frame(self._notebook, bg="#1A1A1A")
        self._notebook.add(tab_dash, text="대시보드")
        self._build_dashboard_tab(tab_dash)

        # 탭 2~5 (향후 확장용 - 현재는 로그만 표시)
        for tab_name in ["베스트셀러", "트렌드", "경쟁사", "리뷰·문의"]:
            tab = tk.Frame(self._notebook, bg="#1A1A1A")
            self._notebook.add(tab, text=tab_name)
            tk.Label(
                tab,
                text=f"수집 실행 후 엑셀 파일에서 [{tab_name}] 시트를 확인하세요.",
                font=("맑은 고딕", 11),
                fg="#888888",
                bg="#1A1A1A",
            ).pack(pady=40)

        # 하단 바
        footer = tk.Frame(self, bg="#0D0D0D", pady=4)
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text=f"저장 위치: {OUTPUT_DIR}",
            font=("맑은 고딕", 8),
            fg="#444444",
            bg="#0D0D0D",
        ).pack(side="left", padx=10)

    def _build_dashboard_tab(self, parent):
        # 버튼 패널
        btn_frame = tk.Frame(parent, bg="#1A1A1A", pady=10)
        btn_frame.pack(fill="x")

        btn_style = {
            "font": ("맑은 고딕", 10, "bold"),
            "relief": "flat",
            "cursor": "hand2",
            "padx": 16,
            "pady": 8,
            "bd": 0,
        }

        self._collect_btn = tk.Button(
            btn_frame,
            text="▶ 전체 수집",
            bg="#E8C56D",
            fg="#1A1A1A",
            activebackground="#C9A84C",
            activeforeground="#1A1A1A",
            command=self._on_collect_all_click,
            **btn_style,
        )
        self._collect_btn.pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="📊 베스트셀러만",
            bg="#2D2D2D",
            fg="#E0E0E0",
            activebackground="#3D3D3D",
            activeforeground="white",
            command=lambda: self._on_partial_collect(["베스트셀러"]),
            **btn_style,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="💰 가격비교만",
            bg="#2D2D2D",
            fg="#E0E0E0",
            activebackground="#3D3D3D",
            activeforeground="white",
            command=lambda: self._on_partial_collect(["가격비교"]),
            **btn_style,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="📝 리뷰/문의만",
            bg="#2D2D2D",
            fg="#E0E0E0",
            activebackground="#3D3D3D",
            activeforeground="white",
            command=lambda: self._on_partial_collect(["리뷰분석", "고객문의"]),
            **btn_style,
        ).pack(side="left", padx=(0, 8))

        self._open_btn = tk.Button(
            btn_frame,
            text="📂 결과 폴더",
            bg="#2D2D2D",
            fg="#E0E0E0",
            activebackground="#3D3D3D",
            activeforeground="white",
            command=self._open_output_folder,
            **btn_style,
        )
        self._open_btn.pack(side="left", padx=(0, 8))

        self._open_file_btn = tk.Button(
            btn_frame,
            text="📄 최근 파일",
            bg="#2D2D2D",
            fg="#E0E0E0",
            activebackground="#3D3D3D",
            activeforeground="white",
            command=self._open_last_file,
            **btn_style,
        )
        self._open_file_btn.pack(side="left", padx=(0, 8))

        # 수집 항목 체크박스
        check_frame = tk.LabelFrame(
            parent,
            text=" 수집 항목 선택 ",
            font=("맑은 고딕", 9),
            fg="#888888",
            bg="#1A1A1A",
            bd=1,
            relief="groove",
            pady=6,
            padx=10,
        )
        check_frame.pack(fill="x", padx=0, pady=(0, 6))

        items = list(self._check_vars.keys())
        for idx, key in enumerate(items):
            cb = tk.Checkbutton(
                check_frame,
                text=key,
                variable=self._check_vars[key],
                font=("맑은 고딕", 9),
                fg="#CCCCCC",
                bg="#1A1A1A",
                selectcolor="#2D2D2D",
                activebackground="#1A1A1A",
                activeforeground="#E8C56D",
            )
            cb.grid(row=0, column=idx, padx=8, pady=2, sticky="w")

        # 진행 바
        progress_frame = tk.Frame(parent, bg="#1A1A1A", pady=2)
        progress_frame.pack(fill="x")

        self._progress = ttk.Progressbar(
            progress_frame, mode="indeterminate", length=900
        )
        self._progress.pack(fill="x")

        # 로그 패널
        log_frame = tk.Frame(parent, bg="#1A1A1A", pady=4)
        log_frame.pack(fill="both", expand=True)

        tk.Label(
            log_frame, text="실행 로그",
            font=("맑은 고딕", 9, "bold"),
            fg="#666666", bg="#1A1A1A"
        ).pack(anchor="w")

        self._log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#0A0A0A",
            fg="#CCCCCC",
            insertbackground="white",
            relief="flat",
            bd=4,
            state="disabled",
        )
        self._log_text.pack(fill="both", expand=True)

        self._log_text.tag_config("INFO", foreground="#79C0FF")
        self._log_text.tag_config("OK", foreground="#56D364")
        self._log_text.tag_config("WARN", foreground="#E8C56D")
        self._log_text.tag_config("ERROR", foreground="#FF7B72")
        self._log_text.tag_config("TIME", foreground="#444444")

    # ─────────────────────────────────────────
    # 로그 처리
    # ─────────────────────────────────────────

    def _log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_queue.put((timestamp, message, level))

    def _poll_log_queue(self):
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

    def _on_collect_all_click(self):
        if self._is_running:
            messagebox.showinfo("알림", "현재 수집이 진행 중입니다.")
            return
        selected = [k for k, v in self._check_vars.items() if v.get()]
        self._run_collection(selected)

    def _on_partial_collect(self, keys: list[str]):
        if self._is_running:
            messagebox.showinfo("알림", "현재 수집이 진행 중입니다.")
            return
        self._run_collection(keys)

    def _run_collection(self, selected_keys: list[str] = None):
        if self._is_running:
            return
        self._is_running = True
        self._set_collecting_state(True)
        thread = threading.Thread(
            target=self._collect_all,
            args=(selected_keys or list(self._check_vars.keys()),),
            daemon=True,
        )
        thread.start()

    def _collect_all(self, selected_keys: list[str]):
        """실제 수집 로직 (백그라운드 스레드)"""
        results = {
            "bestseller": [],
            "sns_trend": [],
            "global_fashion": [],
            "competitor_new": [],
            "price_compare": [],
            "promotions": [],
            "reviews": [],
            "sns_mention": [],
            "inquiries": [],
        }
        try:
            self._log("=" * 60, "TIME")
            self._log("패션 브랜드 모니터링 수집을 시작합니다.", "INFO")
            log = lambda m: self._log(m, "INFO")

            key_map = {
                "베스트셀러":    ("bestseller",    collect_bestseller,    "베스트셀러"),
                "트렌드해시태그": ("sns_trend",     collect_sns_trend,     "트렌드 해시태그"),
                "해외패션뉴스":  ("global_fashion", collect_global_fashion, "해외 패션 뉴스"),
                "경쟁사신상품":  ("competitor_new", collect_competitor_new, "경쟁사 신상품"),
                "가격비교":      ("price_compare",  collect_price_compare, "가격 비교"),
                "프로모션":      ("promotions",     collect_promotions,    "프로모션"),
                "리뷰분석":      ("reviews",        collect_reviews,       "리뷰/별점"),
                "SNS멘션":       ("sns_mention",    collect_sns_mention,   "SNS 멘션"),
                "고객문의":      ("inquiries",      collect_inquiries,     "고객 문의"),
            }

            for key in selected_keys:
                if key not in key_map:
                    continue
                result_key, func, label = key_map[key]
                self._set_status(f"{label} 수집 중...")
                try:
                    results[result_key] = func(log_callback=log)
                except Exception as e:
                    self._log(f"[{label}] 수집 오류: {e}", "ERROR")

            # 엑셀 저장
            self._set_status("엑셀 파일 저장 중...")
            filepath = save_to_excel(
                bestseller=results["bestseller"],
                sns_trend=results["sns_trend"],
                global_fashion=results["global_fashion"],
                competitor_new=results["competitor_new"],
                price_compare=results["price_compare"],
                promotions=results["promotions"],
                reviews=results["reviews"],
                sns_mention=results["sns_mention"],
                inquiries=results["inquiries"],
                log_callback=lambda m: self._log(m, "OK"),
            )
            self._last_file = filepath

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._last_run_var.set(now_str)
            self._set_status("수집 완료")

            total = sum(len(v) for v in results.values())
            self._log(f"수집 완료! 총 {total}건 수집됨", "OK")
            self._log(f"저장: {filepath}", "OK")

        except Exception as e:
            self._log(f"오류 발생: {e}", "ERROR")
            self._set_status("오류 발생")
        finally:
            self._is_running = False
            self._set_collecting_state(False)

    # ─────────────────────────────────────────
    # 스케줄러
    # ─────────────────────────────────────────

    def _start_scheduler(self):
        schedule.every().day.at(SCHEDULE_TIME).do(
            lambda: self._run_collection(list(self._check_vars.keys()))
        )
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
            self._collect_btn.configure(
                state="disabled", bg="#555555", fg="#AAAAAA", text="⏳ 수집 중..."
            )
            self._progress.start(12)
        else:
            self._collect_btn.configure(
                state="normal", bg="#E8C56D", fg="#1A1A1A", text="▶ 전체 수집"
            )
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
        try:
            from utils.browser import shutdown as _browser_shutdown
            _browser_shutdown()
        except Exception:
            pass
        self.destroy()
