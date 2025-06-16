import openai
from config import config
from cache_manager import analysis_cache

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
    
    def _should_use_gpt4o(self, title, artist, year=None):
        """GPT-4o 사용 여부 결정 (비용 최적화)"""
        # 1. 연도 기반 판단 (가장 정확한 기준)
        if year and year >= 2022:
            return True
        
        # 2. 최신 아티스트 키워드 (연도 정보가 없을 때만)
        if not year:
            modern_keywords = [
                'newjeans', 'ive', 'aespa', 'itzy', 'stray kids', 'txt', 'enhypen',
                'billie eilish', 'olivia rodrigo', 'dua lipa', 'the weeknd',
                'bad bunny', 'rosalía', 'doja cat', 'lil nas x', 'ice spice'
            ]
            
            artist_lower = artist.lower()
            for keyword in modern_keywords:
                if keyword in artist_lower:
                    return True
        
        # 3. 기본값: GPT-3.5 사용 (비용 절약)
        return False
    
    def _get_optimized_prompt(self, title, artist, use_web_search=True):
        """최적화된 프롬프트 생성 (토큰 수 절약)"""
        if use_web_search:
            return f"""웹 검색으로 '{title}' by {artist} 분석:

형식:
• 대분류: [장르]
• 지역: [지역]  
• 스타일: [스타일]
• 출처: [웹사이트]

📌 정리
• 대분류: [최종]
• 지역: [최종]
• 스타일: [최종]

금지어: USA,America,American,India,Indian,Canada,Canadian,Japan,Japanese,China,Chinese,Korea,Korean,Britain,British,France,French,Germany,German,Australia,Australian
허용지역: K-Pop,East Coast,West Coast,UK,Latin"""
        else:
            return f"""'{title}' by {artist} 장르 분석:

• 대분류: [장르]
• 지역: [지역]
• 스타일: [스타일]

📌 정리
• 대분류: [최종]
• 지역: [최종]  
• 스타일: [최종]

금지어: USA,America,American,India,Indian,Canada,Canadian,Japan,Japanese,China,Chinese,Korea,Korean,Britain,British,France,French,Germany,German,Australia,Australian
허용지역: K-Pop,East Coast,West Coast,UK,Latin"""

    def get_detailed_genre_analysis(self, title, artist, year=None):
        """비용 최적화된 상세한 장르 분석"""
        try:
            # 1. 캐시 확인
            cached_result = analysis_cache.get_cached_analysis(title, artist)
            if cached_result:
                return f"📋 캐시된 결과:\n\n{cached_result}"
            
            # 2. 모델 선택 (비용 최적화)
            use_gpt4o = self._should_use_gpt4o(title, artist, year)
            model = "gpt-4o" if use_gpt4o else "gpt-3.5-turbo"
            
            # 3. 프롬프트 최적화
            prompt = self._get_optimized_prompt(title, artist, use_gpt4o)
            
            # 4. API 호출
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "음악 전문가. 간결하고 정확한 장르 분석."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400 if use_gpt4o else 300,  # 토큰 수 최적화
                temperature=0.3,
            )
            
            result = response.choices[0].message.content.strip()
            
            # 5. 결과에 모델 정보 추가
            model_info = f"\n\n🤖 분석 모델: {model.upper()}"
            if use_gpt4o:
                model_info += " (웹 검색 포함)"
            else:
                model_info += " (기존 지식 기반)"
            
            final_result = result + model_info
            
            # 6. 캐시에 저장
            analysis_cache.save_analysis_to_cache(title, artist, final_result, model)
            
            return final_result
            
        except Exception as e:
            return f"분석 오류: {str(e)}"
    


# 전역 GPT 서비스 인스턴스
gpt_service = GPTService() 