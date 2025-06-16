# SmartGenreTagger

AI 기반 MP3 장르 태그 편집기

## 주요 기능

- MP3 파일 폴더 일괄 불러오기 및 메타데이터(제목, 아티스트, 연도, 장르) 편집
- MusicBrainz + Spotify API 기반 최신 장르 추천 (GPT 미사용)
- 추천 장르 직접 편집 및 저장
- 오디오 재생/일시정지/시크바 지원

## 설치 및 실행

1. 의존성 설치

```
pip install -r requirements.txt
```

2. .env 파일 생성

```
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
# (선택) OPENAI_API_KEY=your_openai_api_key_here
```

3. 실행

```
python main.py
```

## 장르 추천 방식

- MusicBrainz에서 곡/아티스트의 태그 기반 장르 추출
- Spotify에서 아티스트/앨범의 장르 정보 추가 추출
- 두 소스의 장르를 통합, 우선순위 및 필터링 후 최대 3~4개 추천
- 최신곡/글로벌 곡도 높은 정확도로 장르 추천 가능

## 참고

- MusicBrainz, Spotify API 사용 (무료)
- OpenAI API는 더 이상 필요하지 않음 (향후 확장용)

## 스크린샷

![애플리케이션 스크린샷](screenshot.png)

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/gobetterment/smartgenretagger.git
cd SmartGenreTagger
```

### 2. 가상환경 생성 및 활성화

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어서 API 키들을 입력하세요:

```
# OpenAI API 키 (필수)
OPENAI_API_KEY=your_actual_api_key_here

# Google Search API 설정 (선택사항 - 웹 검색 기능용)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here
```

- **OpenAI API 키**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)에서 발급
- **Google Search API**: 웹 검색 기능을 원하는 경우 설정 (선택사항)

### 5. Google Search API 설정 (선택사항)

웹 검색 기능을 사용하려면 Google Custom Search API를 설정하세요:

```bash
python setup_google_search.py
```

이 스크립트가 단계별로 설정을 안내해드립니다.

## 사용 방법

### 1. 애플리케이션 실행

```bash
python main.py
```

### 2. 기본 사용법

1. **📁 폴더 선택**: "폴더 선택" 버튼을 클릭하여 MP3 파일들이 있는 폴더 선택
2. **🤖 장르 추천**:
   - "🔍 스마트 분석": Google Search + GPT-3.5로 최신 정보 분석
   - "🌐 구글 검색": 브라우저에서 직접 음악 정보 검색
   - "🤖 전체 추천": 모든 파일의 장르를 한 번에 추천
   - "🤖 선택 추천": 선택한 파일들만 장르 추천
3. **✏️ 편집**:
   - **연도**: 연도 컬럼 더블클릭으로 편집 (4자리 숫자만 허용)
   - **GPT추천**: GPT추천 컬럼 더블클릭으로 장르 직접 수정
4. **💾 저장**:
   - **개별**: 저장 컬럼 단순 클릭으로 개별 파일 저장
   - **일괄**: "💾 선택 저장" 또는 "💾 전체 저장" 버튼 사용
5. **🎧 재생**: 파일을 선택하고 재생 버튼(▶️) 클릭

### 3. 키보드 단축키

#### 편집 모드

- **Enter**: 편집 완료 및 저장
- **Escape**: 편집 취소
- **더블클릭**: 연도/GPT추천 컬럼 편집 시작

#### 복사/붙여넣기 (편집 모드에서)

- **macOS**: ⌘C (복사), ⌘V (붙여넣기), ⌘A (전체 선택)
- **Windows**: Ctrl+C (복사), Ctrl+V (붙여넣기), Ctrl+A (전체 선택)
- **우클릭**: 컨텍스트 메뉴로 복사/붙여넣기

#### 테이블 조작

- **Ctrl+클릭** (Windows) / **Cmd+클릭** (macOS): 다중 선택
- **Shift+클릭**: 범위 선택

## 장르 추천 규칙

GPT는 다음 규칙에 따라 장르를 추천합니다:

### ✅ **허용되는 형식**

- **대분류**: Pop, Rock, Hip Hop, R&B, Electronic, Jazz, Classical, Folk, Country, Reggae 등
- **허용 지역**: K-Pop, East Coast, West Coast, UK, Latin (음악적으로 의미있는 경우만)
- **스타일**: Alternative, Trap, House, Ballad, Punk, Indie, Acoustic, Experimental 등

### ❌ **금지 단어**

- 국가명/국적: USA, America, American, India, Indian, Canada, Canadian, Japan, Japanese, China, Chinese, Korea, Korean, Britain, British, France, French, Germany, German, Australia, Australian

### 📝 **형식 예시**

- `Hip Hop / East Coast / Trap`
- `Pop / K-Pop / Ballad`
- `Rock / Alternative`
- `Electronic / House`

## 시스템 요구사항

- **Python**: 3.9 이상
- **운영체제**: macOS, Windows, Linux
- **OpenAI API**: 유효한 API 키 필요
- **메모리**: 최소 512MB RAM
- **저장공간**: 50MB 이상

## 의존성

```txt
eyed3>=0.9.6                      # MP3 태그 편집
openai>=1.0.0                     # OpenAI API 클라이언트
python-dotenv>=1.0.0              # 환경변수 관리
pygame>=2.5.0                     # 오디오 재생
google-api-python-client>=2.149.0 # Google Search API (선택사항)
```

## 문제 해결

### 🔧 **일반적인 문제**

#### tkinter 관련 오류 (macOS)

```bash
brew install python-tk
```

#### eyed3 설치 오류

```bash
pip install --upgrade pip
pip install eyed3
```

#### pygame 오디오 오류

```bash
# macOS
brew install sdl2 sdl2_mixer

# Ubuntu/Debian
sudo apt-get install python3-pygame
```

### 🔑 **API 관련 문제**

#### API 키 오류

- `.env` 파일이 프로젝트 루트에 있는지 확인
- API 키가 유효한지 확인
- OpenAI 계정에 충분한 크레딧이 있는지 확인

#### GPT 응답 오류

- 인터넷 연결 상태 확인
- OpenAI 서비스 상태 확인
- API 사용량 한도 확인

### 💾 **파일 저장 문제**

#### MP3 태그 저장 실패

- 파일이 다른 프로그램에서 사용 중이지 않은지 확인
- 파일 권한 확인 (읽기/쓰기 권한 필요)
- 파일이 손상되지 않았는지 확인

## 개발 정보

### 🏗️ **아키텍처**

- **GUI**: tkinter (Python 표준 라이브러리)
- **MP3 처리**: eyed3 라이브러리
- **AI**: OpenAI GPT-3.5-turbo API
- **오디오 재생**: pygame 라이브러리

### 📁 **프로젝트 구조**

```
SmartGenreTagger/
├── main.py              # 메인 애플리케이션
├── requirements.txt     # 의존성 목록
├── .env.example        # 환경변수 템플릿
├── .env               # 환경변수 (생성 필요)
├── README.md          # 프로젝트 문서
└── screenshot.png     # 스크린샷
```

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 버전 히스토리

- **v1.0.0**: 기본 장르 추천 및 편집 기능
- **v1.1.0**: 연도 편집 기능 추가
- **v1.2.0**: 음악 재생 기능 추가
- **v1.3.0**: 복사/붙여넣기 기능 추가
- **v1.4.0**: 운영체제별 단축키 지원

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 연락처

프로젝트 링크: [https://github.com/gobetterment/smartgenretagger](https://github.com/gobetterment/smartgenretagger)

## 감사의 말

- [OpenAI](https://openai.com/) - GPT API 제공
- [eyed3](https://eyed3.readthedocs.io/) - MP3 태그 편집 라이브러리
- [pygame](https://www.pygame.org/) - 오디오 재생 라이브러리
