#!/usr/bin/env python3
# main.py - 진입점

import sys
import os

# PyInstaller .exe 실행 시 경로 처리
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from gui.app import RPAApp


def main():
    app = RPAApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
