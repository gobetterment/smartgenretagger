#!/usr/bin/env python3
"""
SmartGenreTagger - AI 기반 MP3 장르 태그 편집기
메인 진입점
"""

import sys
from PySide6.QtWidgets import QApplication
from main_window import SmartGenreTaggerMainWindow


def main():
    """애플리케이션 메인 함수"""
    app = QApplication(sys.argv)
    
    # 메인 윈도우 생성 및 표시
    window = SmartGenreTaggerMainWindow()
    window.show()
    
    # 애플리케이션 실행
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 