import os
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSearchService:
    """Google Custom Search API를 사용한 웹 검색 서비스"""
    
    def __init__(self):
        # 환경변수에서 API 키와 검색 엔진 ID 가져오기
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not self.api_key or not self.search_engine_id:
            print("⚠️ Google Search API 설정이 필요합니다:")
            print("1. Google Cloud Console에서 Custom Search API 활성화")
            print("2. API 키 생성")
            print("3. Custom Search Engine 생성")
            print("4. 환경변수 설정:")
            print("   export GOOGLE_API_KEY='your_api_key'")
            print("   export GOOGLE_SEARCH_ENGINE_ID='your_search_engine_id'")
            self.service = None
        else:
            try:
                self.service = build("customsearch", "v1", developerKey=self.api_key)
            except Exception as e:
                print(f"Google Search API 초기화 오류: {e}")
                self.service = None
    
    def search_music_info(self, title, artist, num_results=5):
        """음악 정보 검색"""
        if not self.service:
            return None
        
        try:
            # 검색 쿼리 구성
            query = f'"{title}" "{artist}" genre music information discogs allmusic'
            
            # 검색 실행
            result = self.service.cse().list(
                q=query,
                cx=self.search_engine_id,
                num=num_results
            ).execute()
            
            # 검색 결과 처리
            search_results = []
            if 'items' in result:
                for item in result['items']:
                    search_results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'link': item.get('link', ''),
                        'displayLink': item.get('displayLink', '')
                    })
            
            return search_results
            
        except HttpError as e:
            print(f"Google Search API 오류: {e}")
            return None
        except Exception as e:
            print(f"검색 중 오류 발생: {e}")
            return None
    
    def format_search_results(self, search_results):
        """검색 결과를 텍스트로 포맷팅"""
        if not search_results:
            return "검색 결과를 찾을 수 없습니다."
        
        formatted_text = "🔍 웹 검색 결과:\n\n"
        
        for i, result in enumerate(search_results, 1):
            formatted_text += f"{i}. {result['title']}\n"
            formatted_text += f"   출처: {result['displayLink']}\n"
            formatted_text += f"   내용: {result['snippet']}\n\n"
        
        return formatted_text


# 전역 검색 서비스 인스턴스
google_search_service = GoogleSearchService() 