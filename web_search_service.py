import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import config


class GoogleSearchService:
    """Google Custom Search API를 사용한 웹 검색 서비스"""
    
    def __init__(self):
        # config에서 API 키와 검색 엔진 ID 가져오기
        self.api_key = config.google_api_key
        self.search_engine_id = config.google_search_engine_id
        
        if not self.api_key or not self.search_engine_id:
            print("⚠️ Google Search API 설정이 필요합니다:")
            print("1. Google Cloud Console에서 Custom Search API 활성화")
            print("2. API 키 생성")
            print("3. Custom Search Engine 생성")
            print("4. .env 파일에 다음 추가:")
            print("   GOOGLE_API_KEY=your_api_key")
            print("   GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id")
            self.service = None
        else:
            try:
                self.service = build("customsearch", "v1", developerKey=self.api_key)
            except Exception as e:
                print(f"Google Search API 초기화 오류: {e}")
                self.service = None
    
    def search_music_info(self, title, artist, num_results=5):
        """음악 정보 검색 - 신뢰성 있는 사이트 우선"""
        if not self.service:
            return None
        
        try:
            # 곡명 정리 (맨 마지막 괄호/대괄호 제거)
            cleaned_title = self._clean_song_title(title)
            if cleaned_title != title:
                print(f"🧹 곡명 정리: '{title}' → '{cleaned_title}'")
            
            # 1단계: 최우선 신뢰성 사이트 검색 (AllMusic, Wikipedia, MusicBrainz)
            priority_results = self._search_priority_sites(cleaned_title, artist)
            
            # 2단계: 추가 음악 전문 사이트 검색 (결과가 부족한 경우)
            if len(priority_results) < 3:
                additional_results = self._search_additional_sites(cleaned_title, artist, num_results - len(priority_results))
                priority_results.extend(additional_results)
            
            return priority_results[:num_results] if priority_results else None
            
        except Exception as e:
            print(f"검색 중 오류 발생: {e}")
            return None
    
    def _clean_song_title(self, title):
        """곡명 맨 마지막의 괄호/대괄호 제거"""
        import re
        
        cleaned_title = title.strip()
        
        # 맨 마지막 소괄호 제거 (공백 포함)
        cleaned_title = re.sub(r'\s*\([^)]*\)$', '', cleaned_title)
        
        # 맨 마지막 대괄호 제거 (공백 포함)  
        cleaned_title = re.sub(r'\s*\[[^\]]*\]$', '', cleaned_title)
        
        # 양끝 공백 제거
        cleaned_title = cleaned_title.strip()
        
        # 빈 문자열이면 원본 반환
        return cleaned_title if cleaned_title else title
    
    def _search_priority_sites(self, title, artist):
        """우선순위 사이트 검색 (AllMusic, Wikipedia, MusicBrainz)"""
        priority_sites = [
            ("site:allmusic.com", "AllMusic"),
            ("site:en.wikipedia.org", "Wikipedia"), 
            ("site:musicbrainz.org", "MusicBrainz")
        ]
        
        results = []
        print(f"\n🔍 [{title} - {artist}] 우선순위 사이트 검색 시작...")
        
        for site_query, site_name in priority_sites:
            try:
                query = f'"{title}" "{artist}" {site_query}'
                print(f"   📡 {site_name} 검색 중: {query}")
                
                result = self.service.cse().list(
                    q=query,
                    cx=self.search_engine_id,
                    num=2  # 각 사이트에서 최대 2개
                ).execute()
                
                if 'items' in result:
                    site_results = []
                    for item in result['items']:
                        result_data = {
                            'title': item.get('title', ''),
                            'snippet': item.get('snippet', ''),
                            'link': item.get('link', ''),
                            'displayLink': item.get('displayLink', ''),
                            'priority': True  # 우선순위 사이트 표시
                        }
                        results.append(result_data)
                        site_results.append(result_data)
                    
                    print(f"   ✅ {site_name}에서 {len(site_results)}개 결과 발견:")
                    for i, res in enumerate(site_results, 1):
                        print(f"      {i}. {res['title'][:60]}...")
                        print(f"         URL: {res['link']}")
                        print(f"         내용: {res['snippet'][:100]}...")
                else:
                    print(f"   ❌ {site_name}에서 결과 없음")
                        
            except HttpError as e:
                print(f"   ⚠️ {site_name} 검색 오류: {e}")
                continue
        
        print(f"🔍 우선순위 사이트 검색 완료: 총 {len(results)}개 결과\n")
        return results
    
    def _search_additional_sites(self, title, artist, num_needed):
        """추가 음악 전문 사이트 검색"""
        try:
            print(f"🔍 추가 음악 사이트 검색 시작 ({num_needed}개 필요)...")
            
            # 추가 신뢰성 있는 음악 사이트들
            query = f'"{title}" "{artist}" genre music (site:discogs.com OR site:last.fm OR site:rateyourmusic.com OR site:genius.com)'
            print(f"   📡 추가 사이트 검색 쿼리: {query}")
            
            result = self.service.cse().list(
                q=query,
                cx=self.search_engine_id,
                num=num_needed
            ).execute()
            
            additional_results = []
            if 'items' in result:
                print(f"   ✅ 추가 사이트에서 {len(result['items'])}개 결과 발견:")
                for i, item in enumerate(result['items'], 1):
                    result_data = {
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'link': item.get('link', ''),
                        'displayLink': item.get('displayLink', ''),
                        'priority': False  # 추가 사이트 표시
                    }
                    additional_results.append(result_data)
                    
                    print(f"      {i}. {result_data['title'][:60]}...")
                    print(f"         사이트: {result_data['displayLink']}")
                    print(f"         URL: {result_data['link']}")
                    print(f"         내용: {result_data['snippet'][:100]}...")
            else:
                print(f"   ❌ 추가 사이트에서 결과 없음")
            
            print(f"🔍 추가 사이트 검색 완료: {len(additional_results)}개 결과\n")
            return additional_results
            
        except HttpError as e:
            print(f"   ⚠️ 추가 사이트 검색 오류: {e}")
            return []
    
    def format_search_results_for_gpt(self, search_results):
        """검색 결과를 GPT 분석용으로 포맷팅 - 신뢰성 사이트 우선 표시"""
        if not search_results:
            return "검색 결과를 찾을 수 없습니다."
        
        # 우선순위 사이트와 추가 사이트 분리
        priority_results = [r for r in search_results if r.get('priority', False)]
        additional_results = [r for r in search_results if not r.get('priority', False)]
        
        formatted_text = "신뢰성 높은 음악 정보 사이트 검색 결과:\n\n"
        
        # 우선순위 사이트 결과 먼저 표시
        if priority_results:
            formatted_text += "🔸 신뢰성 높은 사이트 (AllMusic, Wikipedia, MusicBrainz):\n"
            for i, result in enumerate(priority_results, 1):
                formatted_text += f"{i}. {result['title']}\n"
                formatted_text += f"   출처: {result['displayLink']} ⭐\n"
                formatted_text += f"   내용: {result['snippet']}\n\n"
        
        # 추가 사이트 결과 표시
        if additional_results:
            formatted_text += "🔸 추가 음악 전문 사이트:\n"
            start_num = len(priority_results) + 1
            for i, result in enumerate(additional_results, start_num):
                formatted_text += f"{i}. {result['title']}\n"
                formatted_text += f"   출처: {result['displayLink']}\n"
                formatted_text += f"   내용: {result['snippet']}\n\n"
        
        return formatted_text
    
    def is_available(self):
        """Google Search API 사용 가능 여부 확인"""
        return self.service is not None


# 전역 검색 서비스 인스턴스
google_search_service = GoogleSearchService() 