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
        self.spotify_client_id = self._get_spotify_client_id() if os.getenv('SPOTIFY_CLIENT_ID') else None
        self.spotify_client_secret = self._get_spotify_client_secret() if os.getenv('SPOTIFY_CLIENT_SECRET') else None
        self.openai_api_key = self._get_openai_api_key()
        self.discogs_token = self._get_discogs_token()
        
    def _get_spotify_client_id(self):
        """Spotify Client ID를 환경변수에서 가져오기"""
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        if not client_id:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "오류", "SPOTIFY_CLIENT_ID 환경변수가 설정되지 않았습니다.\n.env 파일을 확인해주세요.")
            sys.exit()
        return client_id
    
    def _get_spotify_client_secret(self):
        """Spotify Client Secret을 환경변수에서 가져오기"""
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        if not client_secret:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "오류", "SPOTIFY_CLIENT_SECRET 환경변수가 설정되지 않았습니다.\n.env 파일을 확인해주세요.")
            sys.exit()
        return client_secret
        
    def _get_openai_api_key(self):
        """OpenAI API 키를 환경변수에서 가져오기 (필수)"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "오류", "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.\n.env 파일을 확인해주세요.")
            sys.exit()
        return api_key

    def _get_discogs_token(self):
        token = os.getenv('DISCOGS_TOKEN')
        if not token:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "오류", "DISCOGS_TOKEN 환경변수가 설정되지 않았습니다.\n.env 파일을 확인해주세요.")
            sys.exit()
        return token

# 전역 설정 인스턴스
config = Config() 