#!/usr/bin/env python3
"""
Google Custom Search API 설정 가이드

이 스크립트는 Google Custom Search API를 설정하는 방법을 안내합니다.
"""

import os
import webbrowser
from pathlib import Path

def print_header(title):
    """헤더 출력"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_step(step_num, title, description):
    """단계별 안내 출력"""
    print(f"\n📋 단계 {step_num}: {title}")
    print("-" * 40)
    print(description)

def open_url(url, description):
    """URL 열기"""
    print(f"\n🌐 {description}")
    print(f"URL: {url}")
    
    try:
        webbrowser.open(url)
        print("✅ 브라우저에서 열었습니다.")
    except:
        print("❌ 브라우저 열기 실패. 위 URL을 직접 복사해서 열어주세요.")

def check_env_file():
    """환경변수 파일 확인"""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env 파일이 존재합니다.")
        return True
    else:
        print("❌ .env 파일이 없습니다. 생성해야 합니다.")
        return False

def create_env_template():
    """환경변수 템플릿 생성"""
    env_content = """# OpenAI API 키 (필수)
OPENAI_API_KEY=your_openai_api_key_here

# Google Search API 설정 (선택사항 - 웹 검색 기능용)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("✅ .env 템플릿 파일을 생성했습니다.")
    print("📝 .env 파일을 열어서 실제 API 키를 입력해주세요.")

def main():
    """메인 함수"""
    print_header("Google Custom Search API 설정 가이드")
    
    print("""
🎵 SmartGenreTagger에 웹 검색 기능을 추가하려면 
   Google Custom Search API 설정이 필요합니다.

💡 이 기능은 선택사항입니다:
   - 설정하면: Google Search + GPT-3.5로 최신 정보 분석
   - 설정 안하면: 기존 GPT 모델만으로 분석

💰 비용: Google Custom Search API는 하루 100회까지 무료
""")
    
    # 환경변수 파일 확인
    print_header("환경변수 파일 확인")
    if not check_env_file():
        create_env_template()
    
    # 단계별 설정 안내
    print_step(1, "Google Cloud Console 접속", 
               "Google Cloud Console에 로그인하고 프로젝트를 생성하거나 선택합니다.")
    
    open_url("https://console.cloud.google.com/", "Google Cloud Console 열기")
    
    input("\n⏸️  프로젝트 생성/선택 완료 후 Enter를 눌러주세요...")
    
    print_step(2, "Custom Search API 활성화",
               "API 및 서비스 > 라이브러리에서 'Custom Search API'를 검색하고 활성화합니다.")
    
    open_url("https://console.cloud.google.com/apis/library/customsearch.googleapis.com", 
             "Custom Search API 활성화 페이지 열기")
    
    input("\n⏸️  API 활성화 완료 후 Enter를 눌러주세요...")
    
    print_step(3, "API 키 생성",
               "API 및 서비스 > 사용자 인증 정보에서 'API 키'를 생성합니다.")
    
    open_url("https://console.cloud.google.com/apis/credentials", 
             "API 키 생성 페이지 열기")
    
    print("\n📝 생성된 API 키를 복사해두세요!")
    input("\n⏸️  API 키 생성 완료 후 Enter를 눌러주세요...")
    
    print_step(4, "Custom Search Engine 생성",
               "Google Custom Search Engine을 생성하고 검색 엔진 ID를 얻습니다.")
    
    open_url("https://cse.google.com/cse/create/new", 
             "Custom Search Engine 생성 페이지 열기")
    
    print("""
🔧 설정 방법:
1. '검색할 사이트' 입력란에 '*' 입력 (전체 웹 검색)
2. '검색 엔진 이름' 입력 (예: SmartGenreTagger Search)
3. '만들기' 클릭
4. 생성 후 '제어판'에서 '검색 엔진 ID' 복사
""")
    
    input("\n⏸️  Custom Search Engine 생성 완료 후 Enter를 눌러주세요...")
    
    print_step(5, "환경변수 설정",
               ".env 파일에 API 키와 검색 엔진 ID를 입력합니다.")
    
    print("""
📝 .env 파일을 열어서 다음 값들을 입력하세요:

GOOGLE_API_KEY=여기에_API_키_입력
GOOGLE_SEARCH_ENGINE_ID=여기에_검색엔진ID_입력

⚠️  주의사항:
- API 키와 검색 엔진 ID 앞뒤에 공백이 없어야 합니다
- 따옴표는 사용하지 마세요
""")
    
    print_header("설정 완료!")
    print("""
🎉 Google Custom Search API 설정이 완료되었습니다!

✅ 이제 SmartGenreTagger에서 다음 기능을 사용할 수 있습니다:
   - 🔍 스마트 분석: Google Search + GPT-3.5 조합
   - 🌐 구글 검색: 브라우저에서 직접 검색

💡 팁:
   - Google Search API는 하루 100회까지 무료입니다
   - 캐시 기능으로 중복 검색을 방지합니다
   - API 한도 초과 시 자동으로 기존 방식으로 전환됩니다

🚀 이제 앱을 실행해보세요!
""")

if __name__ == "__main__":
    main() 