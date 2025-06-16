import os
import sys
import logging
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication, QMessageBox

# eyed3 로그 레벨 설정 (경고 메시지 숨기기)
logging.getLogger("eyed3").setLevel(logging.ERROR)

# 환경변수 로드
load_dotenv()

class Config:
    """애플리케이션 설정 관리 클래스"""
    
    def __init__(self):
        self.openai_api_key = self._get_openai_api_key()
        self.google_api_key = self._get_google_api_key()
        self.google_search_engine_id = self._get_google_search_engine_id()
        
    def _get_openai_api_key(self):
        """OpenAI API 키를 환경변수에서 가져오기"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "오류", "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.\n.env 파일을 확인해주세요.")
            sys.exit()
        return api_key
    
    def _get_google_api_key(self):
        """Google API 키를 환경변수에서 가져오기 (선택사항)"""
        return os.getenv('GOOGLE_API_KEY')
    
    def _get_google_search_engine_id(self):
        """Google Search Engine ID를 환경변수에서 가져오기 (선택사항)"""
        return os.getenv('GOOGLE_SEARCH_ENGINE_ID')

# 전역 설정 인스턴스
config = Config() 