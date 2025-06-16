import openai
from config import config
from cache_manager import analysis_cache
from web_search_service import google_search_service

class GPTService:
    """GPT API를 사용한 장르 추천 서비스"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=config.openai_api_key)
    
    def get_genre_recommendation(self, title, artist):
        """노래 제목과 아티스트를 기반으로 장르 추천"""
        try:
            prompt = f"노래 제목이 '{title}', 아티스트가 '{artist}'인 MP3의 장르를 대분류/지역/스타일 형식으로 최대 4개까지 추천해줘."
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "음악전문가로서 노래 장르를 추천해줘. 절대 금지 단어: USA, America, American, India, Indian, Canada, Canadian, Japan, Japanese, China, Chinese, Korea, Korean, Britain, British, France, French, Germany, German, Australia, Australian, Nigeria, Nigeria, Ghana - 이런 국가명/국적 단어는 절대 사용하지 마! 허용되는 지역 표기는 오직 K-Pop, East Coast, West Coast, UK, Latin만 가능. 형식: 대분류/지역/스타일 (최대 4개). 예시 1:Hip Hop / East Coast / Trap, 예시 2: Pop / Ballad 예시 3: Rock / Alternative / Indie"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"GPT 오류: {str(e)}"
    

    
    def _get_optimized_prompt(self, title, artist, use_web_search=True):
        """최적화된 프롬프트 생성"""
        return f"""'{title}' by {artist}의 장르 분석을 해줘:

다음 형식으로 간결하게 분석해줘:

🔍 스마트 분석 결과:
• 대분류: [주요 장르]
• 지역: [음악적 지역/스타일]
• 음악스타일: [간결한 스타일 설명]
• 아티스트: [주요 장르 특징]
• 곡 특징: [독특한 요소]

📌 최종 장르 추천 (영어로)
* [Genre] / [Style] 또는 [Genre] / [Region] / [Style] (지역이 중요한 경우만)

⚠️ 절대 금지어: USA, America, American, India, Indian, Canada, Canadian, Japan, Japanese, China, Chinese, Korea, Korean, Britain, British, France, French, Germany, German, Australia, Australian - 이런 국가명은 절대 사용 금지!

✅ 허용 지역 (꼭 필요한 경우만): K-Pop, East Coast, West Coast, UK, Latin

🚨 중요 주의사항: 
- 곡명에 (Dirty), (Clean), (Explicit), (Radio Edit) 등의 버전 표기가 있어도 이는 단순히 가사 버전을 나타내는 것이므로 장르 분석에 영향을 주지 마세요
- 예: "Song Title (Dirty)" → 이 곡이 Dirty South 장르라는 뜻이 아님!

예시:
- Hip Hop / Trap (지역 불필요)
- Pop / Ballad (지역 불필요) 
- Hip Hop / East Coast / Boom Bap (지역이 중요한 경우)
- Pop / K-Pop / Ballad (K-Pop은 허용)"""

    def get_detailed_genre_analysis(self, title, artist, year=None):
        """Google Search + GPT-3.5 조합 분석 (캐시 우선)"""
        try:
            # 1. 캐시 확인 - 캐시가 있으면 바로 반환
            cached_result = analysis_cache.get_cached_analysis(title, artist)
            if cached_result:
                print(f"💾 [{title} - {artist}] 캐시된 분석 결과 사용")
                print(f"🚀 API 호출 없이 즉시 반환\n")
                return cached_result  # 캐시 표시 제거하고 바로 결과 반환
            
            # 2. 무조건 Google Search + GPT-3.5 조합 사용
            print(f"🎵 [{title} - {artist}] 새로운 분석 시작...")
            if google_search_service.is_available():
                print(f"🌐 Google Search API 사용 가능 - 웹 검색 + GPT-3.5 조합 분석")
                return self._analyze_with_web_search(title, artist, year)
            else:
                print(f"⚠️ Google Search API 없음 - GPT-3.5만 사용")
                # Google Search API가 없으면 GPT-3.5만 사용
                return self._analyze_with_gpt35_only(title, artist, year)
            
        except Exception as e:
            return f"분석 오류: {str(e)}"
    
    def _analyze_with_web_search(self, title, artist, year):
        """Google Search + GPT-3.5 조합 분석"""
        try:
            # 1. Google Search로 정보 수집
            search_results = google_search_service.search_music_info(title, artist)
            
            if search_results:
                # 검색 결과를 GPT 분석용으로 포맷팅
                search_context = google_search_service.format_search_results_for_gpt(search_results)
                
                # GPT에게 전달할 검색 결과 로그 출력
                print(f"📤 GPT에게 전달할 검색 정보:")
                print("=" * 60)
                print(search_context)
                print("=" * 60)
                print(f"🤖 GPT-3.5로 분석 시작...\n")
                
                # GPT-3.5로 검색 결과 분석
                prompt = f"""다음 신뢰성 높은 음악 사이트 검색 결과를 바탕으로 '{title}' by {artist}의 장르 분석을 해줘:

{search_context}

⭐ 표시된 AllMusic, Wikipedia, MusicBrainz의 정보를 우선적으로 참고하여 다음 형식으로 간결하게 분석해줘:

🔍 스마트 분석 결과:
• 대분류: [주요 장르]
• 지역: [음악적 지역/스타일]
• 음악스타일: [간결한 스타일 설명]
• 아티스트: [간결한 아티스트 특징]
• 곡 특징: [독특한 요소]

📌 최종 장르 추천 (영어로)
* [Genre] / [Style] 또는 [Genre] / [Region] / [Style] (지역이 중요한 경우만)

⚠️ 절대 금지어: USA, America, American, India, Indian, Canada, Canadian, Japan, Japanese, China, Chinese, Korea, Korean, Britain, British, France, French, Germany, German, Australia, Australian - 이런 국가명은 절대 사용 금지!

✅ 허용 지역 (꼭 필요한 경우만): K-Pop, East Coast, West Coast, UK, Latin

🚨 중요 주의사항: 
- 곡명에 (Dirty), (Clean), (Explicit), (Radio Edit) 등의 버전 표기가 있어도 이는 단순히 가사 버전을 나타내는 것이므로 장르 분석에 영향을 주지 마세요
- 예: "Song Title (Dirty)" → 이 곡이 Dirty South 장르라는 뜻이 아님!

예시:
- Hip Hop / Trap (지역 불필요)
- Pop / Ballad (지역 불필요) 
- Hip Hop / East Coast / Boom Bap (지역이 중요한 경우)
- Pop / K-Pop / Ballad (K-Pop은 허용)"""

                model_used = "gpt-3.5-turbo + Google Search"
                
            else:
                # 검색 실패 시 기본 분석
                prompt = self._get_optimized_prompt(title, artist, False)
                model_used = "gpt-3.5-turbo"
            
            # GPT-3.5로 분석
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "음악 전문가. 웹 검색 결과를 바탕으로 정확한 장르 분석. 중요: USA, America, American 등 국가명은 절대 사용 금지! 지역이 중요하지 않으면 생략하고 Genre/Style 형식만 사용."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=450,  # 간결한 분석으로 토큰 절약
                temperature=0.3,
            )
            
            result = response.choices[0].message.content.strip()
            
            # GPT 분석 결과 로그 출력
            print(f"🤖 GPT-3.5 분석 완료!")
            print("📋 GPT 원본 응답:")
            print("-" * 50)
            print(result)
            print("-" * 50)
            print()
            
            # 최종 추천 장르 추출 및 표시
            final_result = self._extract_final_recommendation(result, title, artist)
            
            # 캐시에 저장
            analysis_cache.save_analysis_to_cache(title, artist, final_result, model_used)
            print(f"💾 분석 결과 캐시에 저장됨 ({model_used})\n")
            
            return final_result
            
        except Exception as e:
            return f"웹 검색 분석 오류: {str(e)}"
    
    def _analyze_with_gpt35_only(self, title, artist, year):
        """GPT-3.5만 사용한 분석 (Google Search API 없을 때)"""
        try:
            # 무조건 GPT-3.5 사용
            model = "gpt-3.5-turbo"
            
            # 프롬프트 최적화
            prompt = self._get_optimized_prompt(title, artist, False)  # 웹 검색 없음
            
            # API 호출
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "음악 전문가. 간결하고 정확한 장르 분석. 중요: USA, America, American 등 국가명은 절대 사용 금지! 지역이 중요하지 않으면 생략하고 Genre/Style 형식만 사용."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,  # 간결한 분석으로 토큰 절약
                temperature=0.3,
            )
            
            result = response.choices[0].message.content.strip()
            
            # 최종 추천 장르 추출 및 표시
            final_result = self._extract_final_recommendation(result, title, artist)
            
            # 캐시에 저장
            analysis_cache.save_analysis_to_cache(title, artist, final_result, model)
            
            return final_result
            
        except Exception as e:
            return f"분석 오류: {str(e)}"
    
    def _extract_final_recommendation(self, analysis_result, title, artist):
        """분석 결과를 그대로 표시 (상세한 분석 내용 포함)"""
        try:
            # 상세한 분석 결과를 그대로 표시하되, 사용 안내만 추가
            return f"""{analysis_result}
"""
                
        except Exception as e:
            # 오류 시 기본 형식으로 표시
            return f"""🎵 {title} - {artist}

{analysis_result}

"""


# 전역 GPT 서비스 인스턴스
gpt_service = GPTService() 