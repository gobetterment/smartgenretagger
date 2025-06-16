import openai
from config import config
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
    
    def get_detailed_genre_analysis(self, title, artist):
        """곡에 대한 상세한 장르 분석"""
        try:
            prompt = f"""
            '{title}' by {artist} 곡에 대해 상세한 장르 분석을 해줘.
            
            다음 형식으로 분석해줘:
            
            • 대분류: [주요 장르]
            • 지역: [지역적 특성]
            • 스타일: [구체적인 스타일 설명]
            • 아티스트 배경: [아티스트의 주요 장르와 특징]
            
            ⸻
            
            📌 정리
            • 대분류: [최종 대분류]
            • 지역: [최종 지역]
            • 스타일: [최종 스타일]
            
            주의사항:
            - 절대 금지 단어: USA, America, American, India, Indian, Canada, Canadian, Japan, Japanese, China, Chinese, Korea, Korean, Britain, British, France, French, Germany, German, Australia, Australian
            - 허용되는 지역 표기: K-Pop, East Coast, West Coast, UK, Latin만 사용
            - 구체적이고 정확한 정보 제공
            - 아티스트의 실제 음악적 배경과 곡의 특성을 반영
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # 비용 효율적인 GPT-3.5 사용
                messages=[
                    {"role": "system", "content": "당신은 음악 전문가입니다. 곡과 아티스트에 대한 정확하고 상세한 장르 분석을 제공해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"상세 분석 오류: {str(e)}"

# 전역 GPT 서비스 인스턴스
gpt_service = GPTService() 