#!/usr/bin/env python3
"""PyAPI Studio - Main Entry Point"""

import sys
import asyncio
from pathlib import Path

# PyQt6
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# qasync for Qt-asyncio integration
try:
    import qasync
except ImportError:
    print("Installing qasync...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qasync", "-q"])
    import qasync

from src.ui import MainWindow
from src.data import DatabaseManager


def setup_high_dpi():
    """HiDPI 설정"""
    # Qt6는 기본적으로 HiDPI를 지원
    pass


def setup_font(app: QApplication):
    """기본 폰트 설정"""
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)


def setup_database():
    """데이터베이스 초기화"""
    db_path = Path.home() / ".pyapi-studio" / "data.db"
    DatabaseManager.get_instance(db_path)


async def main_async():
    """비동기 메인 함수"""
    app = QApplication.instance()
    
    # 데이터베이스 초기화
    setup_database()
    
    # 메인 윈도우 생성
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 실행
    while True:
        await asyncio.sleep(0.01)
        if not window.isVisible():
            break


def main():
    """메인 함수"""
    # HiDPI 설정
    setup_high_dpi()
    
    # 애플리케이션 생성
    app = QApplication(sys.argv)
    app.setApplicationName("PyAPI Studio")
    app.setOrganizationName("PyAPI")
    app.setApplicationVersion("1.0.0")
    
    # 폰트 설정
    setup_font(app)
    
    # 데이터베이스 초기화
    setup_database()
    
    # qasync 이벤트 루프 설정
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 메인 윈도우 생성
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 실행
    with loop:
        loop.run_forever()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
