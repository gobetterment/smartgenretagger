# SmartGenreTagger

MP3 파일의 장르 태그를 GPT AI의 도움으로 자동 추천받고 편집할 수 있는 스마트한 GUI 애플리케이션입니다.

## 주요 기능

- 📁 **폴더 선택**: MP3 파일들이 있는 폴더를 선택하여 일괄 로드
- 🤖 **GPT 장르 추천**: OpenAI GPT를 활용한 지능형 장르 추천
- 📝 **직접 편집**: GPT 추천이 마음에 들지 않으면 직접 수정 가능
- 💾 **개별/일괄 저장**: 파일별 개별 저장 또는 전체 일괄 저장
- 📊 **테이블 뷰**: 엑셀과 같은 직관적인 테이블 형태로 정보 표시

## 스크린샷

![애플리케이션 스크린샷](screenshot.png)

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/SmartGenreTagger.git
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

`.env` 파일을 열어서 OpenAI API 키를 입력하세요:

```
OPENAI_API_KEY=your_actual_api_key_here
```

OpenAI API 키는 [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)에서 발급받을 수 있습니다.

## 사용 방법

### 1. 애플리케이션 실행

```bash
python main.py
```

### 2. 기본 사용법

1. **폴더 선택**: "폴더 선택" 버튼을 클릭하여 MP3 파일들이 있는 폴더 선택
2. **장르 추천**: "전체 GPT 장르 추천" 버튼으로 모든 파일의 장르를 한 번에 추천받기
3. **편집**: GPT 추천 컬럼을 더블클릭하여 장르 직접 수정
4. **저장**: 저장 컬럼을 더블클릭하여 개별 파일 저장

### 3. 키보드 단축키

- **Enter**: 편집 완료
- **Escape**: 편집 취소
- **더블클릭**: 셀 편집 또는 저장

## 장르 추천 규칙

GPT는 다음 규칙에 따라 장르를 추천합니다:

- **대분류**: Pop, Rock, Hip Hop, R&B, Electronic, Jazz, Classical 등
- **지역 표기**: K-Pop, East Coast, West Coast, UK, Latin (음악적으로 의미있는 경우만)
- **스타일**: Alternative, Trap, House, Ballad, Punk, Indie 등
- **형식**: `대분류 / 지역 / 스타일` (최대 4개, 슬래시 앞뒤 공백)

예시:

- `Hip Hop / East Coast / Trap`
- `Pop / K-Pop / Ballad`
- `Rock / Alternative`

## 시스템 요구사항

- Python 3.9 이상
- macOS, Windows, Linux 지원
- OpenAI API 키 필요

## 의존성

- `eyed3`: MP3 태그 편집
- `openai`: OpenAI API 클라이언트
- `python-dotenv`: 환경변수 관리
- `tkinter`: GUI (Python 기본 포함)

## 문제 해결

### tkinter 관련 오류 (macOS)

```bash
brew install python-tk
```

### eyed3 설치 오류

```bash
pip install --upgrade pip
pip install eyed3
```

### API 키 오류

- `.env` 파일이 올바른 위치에 있는지 확인
- API 키가 유효한지 확인
- OpenAI 계정에 충분한 크레딧이 있는지 확인

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 연락처

프로젝트 링크: [https://github.com/yourusername/SmartGenreTagger](https://github.com/yourusername/SmartGenreTagger)

## 감사의 말

- [OpenAI](https://openai.com/) - GPT API 제공
- [eyed3](https://eyed3.readthedocs.io/) - MP3 태그 편집 라이브러리
