import musicbrainzngs
import discogs_client
import time
import re
from config import config
import openai
import pickle
import threading
import os
from typing import Dict, List, Optional, Tuple, Union

# =============================================================================
# 프롬프트 템플릿 관리
# =============================================================================

class PromptManager:
    """프롬프트 템플릿을 효율적으로 관리하는 클래스"""
    
    # 기본 구성 요소들
    ROLE = "당신은 전문 DJ입니다."
    MAX_TAGS = "**최대 4개**"
    
    # 공통 규칙 구성 요소들
    RULES = {
        'main_genre_required': "**필수**: 대분류 1개 반드시 포함 (Hip Hop, Pop, R&B, EDM, Rock, Jazz, Blues, Country, Folk)",
        'sub_genres_allowed': "**추가 가능**: 구체적 세부 장르 (Trap, Boom Bap, UK Drill, Amapiano, Dancehall, Afrobeats 등)",
        'compound_processing': """**복합 장르 분해 규칙** - 반드시 적용:
   • Southern Hip Hop → 제외 (southern hip hop도 제외)
   • West Coast Hip Hop → 제외 (west coast hip hop도 제외)
   • East Coast Hip Hop → 제외 (east coast hip hop도 제외)
   • Midwest Hip Hop → 제외 (midwest hip hop도 제외)
   • Southern → 제외 (지역명 단독)
   • West Coast → 제외 (지역명 단독)
   • East Coast → 제외 (지역명 단독)
   • Midwest → 제외 (지역명 단독)
   • Hardcore Hip Hop → Hip Hop + Hardcore (2개로 분리) 
   • Contemporary R&B → R&B (Contemporary 제거)
   • Alternative R&B → R&B (Alternative 제거)
   """,
        'hyphen_formatting': """**하이픈 → 띄어쓰기 변환** (예외: K-Pop만 하이픈 유지)
   • Dance-Pop → Dance Pop
   • Synth-Pop → Synth Pop  
   • Alt-Rock → Alt Rock""",
        'special_conversions': """**한국 음악 특별 처리**:
   • Korean Hip Hop → K-Rap
   • Korean Rap → K-Rap
   • K-Pop은 하이픈 유지""",
        'meaningless_filter': """**무의미 단어 완전 제거**: Contemporary, Modern, New, Current, Recent, Latest, Music, Alternative, Urban""",
        'regional_filter': """**지역 태그 엄격 제한**:
   • 완전 제외: Southern Hip Hop, East Coast Hip Hop, West Coast Hip Hop, Midwest Hip Hop (대소문자 무관)
   • 완전 제외: Southern, East Coast, West Coast, Midwest (지역명 단독도 제외)
   • 허용: UK Drill, K-Pop, K-Rap, Latin, Afrobeats, Hardcore
   • 금지: English, American, British, 연도(2010s, 90s 등)""",
        'genre_priority': """**장르 우선순위** (반드시 준수):
   1순위: 대분류 (Hip Hop, Pop, R&B, EDM, Rock, Afrobeats)
   2순위: Trap, Boom Bap, Afrobeats, UK Drill, Dancehall, K-Pop, K-Rap, Latin
   3순위: House, Techno, Dubstep
   
   ⚠️ Alternative, Contemporary는 항상 제거""",
        'african_music': """**아프리카 음악 최우선**: Afrobeats, Afrobeat, Latin이 입력에 있으면 반드시 포함""",
        'deduplication': "중복 및 유사 장르 제거",
        'practicality': "DJing 실용성 최우선",
        'list_only': "제공된 리스트 내 장르만 사용"
    }
    
    # 규칙 조합 프리셋
    RULE_PRESETS = {
        'genre_refine': ['list_only', 'main_genre_required', 'sub_genres_allowed', 
                        'compound_processing', 'hyphen_formatting', 'special_conversions', 
                        'meaningless_filter', 'regional_filter', 'genre_priority', 'african_music', 'deduplication'],
        'direct_recommendation': ['main_genre_required', 'sub_genres_allowed', 'compound_processing', 
                                'hyphen_formatting', 'special_conversions', 'meaningless_filter',
                                'regional_filter', 'genre_priority', 'african_music', 'deduplication', 'practicality'],
        'minimal': ['main_genre_required', 'sub_genres_allowed', 'hyphen_formatting', 
                   'special_conversions', 'meaningless_filter', 'genre_priority', 'deduplication'],
        'strict': ['list_only', 'main_genre_required', 'compound_processing', 'hyphen_formatting', 
                  'special_conversions', 'meaningless_filter', 'regional_filter', 'genre_priority', 'african_music', 'deduplication']
    }
    
    # 출력 형식
    OUTPUT_FORMAT = """📋 **출력 형식 (절대 규칙):**
⚠️ **반드시 준수**: 한 줄, 슬래시 구분, 첫 글자 대문자, 최대 4개

✅ **올바른 예시:**
- Hip Hop / Southern / Trap
- R&B / Neo Soul / Contemporary → R&B / Neo Soul (Contemporary 제거)
- Afrobeats / Hip Hop / Dancehall
- Pop / Dance / Electronic
- UK Drill / Hip Hop / Grime

❌ **절대 금지 예시:**
- Alternative R&B (→ R&B로 변경)
- Contemporary R&B (→ R&B로 변경)  
- Hardcore Hip Hop (→ Hip Hop / Hardcore로 분리)
- Dance-Pop (→ Dance Pop으로 변경)

"""
    
    # GPT 설정
    SYSTEM_MESSAGE = "You are a professional DJ. FOLLOW ALL RULES EXACTLY. NO EXCEPTIONS. Split compound genres. Remove Alternative/Contemporary. Prioritize Afrobeats/Amapiano. Output format: Genre / Genre / Genre (max 4). RESPOND WITH GENRES ONLY."
    SYSTEM_MESSAGE_DIRECT = "You are a professional DJ and music expert. Analyze the song accurately. NEVER force genres that don't match. Split compound genres. Remove Alternative/Contemporary. COMPLETELY EXCLUDE ALL REGIONAL TERMS: Southern, East Coast, West Coast, Midwest, Southern Hip Hop, East Coast Hip Hop, West Coast Hip Hop, Midwest Hip Hop. Focus on what the song actually sounds like. Output format: Genre / Genre / Genre (max 4). RESPOND WITH GENRES ONLY."
    MODEL_CONFIG = {
        "model": "gpt-3.5-turbo",
        "max_tokens": 200,
        "temperature": 0.05
    }
    
    @classmethod
    def build_rules_section(cls, rule_keys: List[str]) -> str:
        """선택된 규칙들로 규칙 섹션 구성"""
        rules_text = "🎯 **추천 규칙:**\n"
        for i, key in enumerate(rule_keys, 1):
            if key in cls.RULES:
                rules_text += f"{i}. {cls.RULES[key]}\n"
        return rules_text.strip()
    
    @classmethod
    def get_rules_by_preset(cls, preset_name: str) -> List[str]:
        """프리셋 이름으로 규칙 조합 가져오기"""
        return cls.RULE_PRESETS.get(preset_name, cls.RULE_PRESETS['minimal'])
    
    @classmethod
    def build_prompt(cls, template_type: str, **kwargs) -> str:
        """동적 프롬프트 생성"""
        if template_type == "genre_refine":
            return cls.get_genre_refine_prompt(kwargs.get('genres_list', ''))
        elif template_type == "direct_recommendation":
            return cls.get_direct_recommendation_prompt(kwargs.get('title', ''), kwargs.get('artist', ''))
        elif template_type == "custom":
            # 커스텀 프롬프트 생성
            rule_keys = kwargs.get('rules', cls.RULE_PRESETS['minimal'])
            content = kwargs.get('content', '')
            return f"""{cls.ROLE} {content}

{cls.build_rules_section(rule_keys)}

{cls.OUTPUT_FORMAT}

응답:"""
        else:
            raise ValueError(f"Unknown template type: {template_type}")
    
    @classmethod
    def get_genre_refine_prompt(cls, genres_list: str, rule_preset: str = 'genre_refine') -> str:
        """장르 리스트 기반 추천 프롬프트 생성"""
        rule_keys = cls.get_rules_by_preset(rule_preset)
        
        return f"""🎯 **CRITICAL RULES - MUST FOLLOW EXACTLY:**

📋 **INPUT GENRES:** {genres_list}

🚨 **MANDATORY PROCESSING RULES:**
1. **AFROBEATS/AMAPIANO = TOP PRIORITY** - If present, MUST be first or second
2. **COMPLETELY EXCLUDE THESE GENRES (NEVER USE THEM):**
   - Southern Hip Hop / southern hip hop → EXCLUDE
   - East Coast Hip Hop / east coast hip hop → EXCLUDE  
   - West Coast Hip Hop / west coast hip hop → EXCLUDE
   - Midwest Hip Hop / midwest hip hop → EXCLUDE
   - Southern → EXCLUDE (standalone regional term)
   - East Coast → EXCLUDE (standalone regional term)
   - West Coast → EXCLUDE (standalone regional term)
   - Midwest → EXCLUDE (standalone regional term)
3. **SPLIT COMPOUND GENRES:**
   - Hardcore Hip Hop → Hip Hop + Hardcore  
   - Alternative R&B → R&B (remove Alternative)
   - Contemporary R&B → R&B (remove Contemporary)
4. **REMOVE MEANINGLESS WORDS:** Alternative, Contemporary, Modern, New, Current, Recent, Latest, Music, Urban
5. **MAX 4 GENRES** separated by " / "

🔥 **EXACT EXAMPLES:**
- Input: 'afrobeats', 'alternative r&b', 'alté', 'neo soul' → OUTPUT: Afrobeats / R&B / Neo Soul / Alté
- Input: 'east coast hip hop', 'hip hop', 'pop rap' → OUTPUT: Hip Hop / Pop Rap
- Input: 'Hip Hop', 'Southern', 'Trap', 'West Coast' → OUTPUT: Hip Hop / Trap
- Input: 'hip hop', 'southern', 'trap', 'west coast' → OUTPUT: Hip Hop / Trap

⚠️ **NEVER INCLUDE: Southern, East Coast, West Coast, Midwest in output**

OUTPUT (genres only):"""
    
    @classmethod
    def get_direct_recommendation_prompt(cls, title: str, artist: str, rule_preset: str = 'direct_recommendation') -> str:
        """곡 정보 기반 추천 프롬프트 생성"""
        rule_keys = cls.get_rules_by_preset(rule_preset)
        
        return f"""🎯 **DJ GENRE ANALYSIS - ACCURACY FIRST:**

🎵 **SONG:** {title} by {artist}

🚨 **CRITICAL RULES:**
1. **ACCURACY IS PARAMOUNT** - Only suggest genres that actually match the song
2. **NO FORCED GENRES** - Don't add Afrobeats/Latin/Dancehall unless the song actually is that genre
3. **COMPLETELY EXCLUDE ALL REGIONAL TERMS (NEVER USE THEM):**
   - Southern Hip Hop / southern hip hop → EXCLUDE
   - East Coast Hip Hop / east coast hip hop → EXCLUDE  
   - West Coast Hip Hop / west coast hip hop → EXCLUDE
   - Midwest Hip Hop / midwest hip hop → EXCLUDE
   - Southern → EXCLUDE (standalone regional term)
   - East Coast → EXCLUDE (standalone regional term)
   - West Coast → EXCLUDE (standalone regional term)
   - Midwest → EXCLUDE (standalone regional term)
4. **SPLIT COMPOUND GENRES:**
   - Hardcore Hip Hop → Hip Hop / Hardcore
   - Alternative R&B → R&B (remove Alternative)
   - Contemporary R&B → R&B (remove Contemporary)
5. **REMOVE MEANINGLESS WORDS:** Alternative, Contemporary, Modern, New, Current, Recent, Latest, Music, Urban
6. **MAX 4 GENRES** separated by " / "

🎯 **GENRE SELECTION PRIORITY:**
1. **Listen to the song style first** - What does it actually sound like?
2. Main genre categories: Hip Hop, R&B, Pop, EDM, Rock, Jazz, Blues, Country
3. Specific subgenres: Trap, Boom Bap, House, Techno, Neo Soul, etc.
4. Allowed regional modifiers: UK Drill, K-Pop, K-Rap, Latin, Afrobeats (only if accurate)

🔥 **EXACT EXAMPLES:**
- Input song from West Coast → OUTPUT: Hip Hop / G-Funk (NOT West Coast Hip Hop)
- Input song from South → OUTPUT: Hip Hop / Trap (NOT Southern Hip Hop)
- Input song from East Coast → OUTPUT: Hip Hop / Boom Bap (NOT East Coast Hip Hop)

⚠️ **NEVER INCLUDE: Southern, East Coast, West Coast, Midwest, Southern Hip Hop, East Coast Hip Hop, West Coast Hip Hop, Midwest Hip Hop in output**

OUTPUT (genres only):"""
    
    @classmethod
    def update_rule(cls, rule_key: str, new_content: str):
        """규칙 업데이트 (런타임 중)"""
        if rule_key in cls.RULES:
            cls.RULES[rule_key] = new_content
        else:
            print(f"Warning: Rule '{rule_key}' not found")
    
    @classmethod
    def add_custom_preset(cls, preset_name: str, rule_keys: List[str]):
        """커스텀 규칙 프리셋 추가"""
        # 유효한 규칙 키들만 필터링
        valid_keys = [key for key in rule_keys if key in cls.RULES]
        cls.RULE_PRESETS[preset_name] = valid_keys
    
    @classmethod
    def get_available_presets(cls) -> List[str]:
        """사용 가능한 프리셋 목록 반환"""
        return list(cls.RULE_PRESETS.keys())
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> bool:
        """프롬프트 유효성 검사"""
        required_elements = [cls.ROLE, cls.MAX_TAGS, "🎯", "📋"]
        return all(element in prompt for element in required_elements)

# 편의를 위한 전역 인스턴스
prompt_manager = PromptManager()

# =============================================================================
# 사용 예시 (주석으로 보관)
# =============================================================================
"""
# 기본 사용법
prompt1 = prompt_manager.get_genre_refine_prompt("Hip Hop, Trap, Southern Hip Hop")
prompt2 = prompt_manager.get_direct_recommendation_prompt("Song Title", "Artist Name")

# 다른 프리셋 사용
strict_prompt = prompt_manager.get_genre_refine_prompt("genres...", rule_preset='strict')
minimal_prompt = prompt_manager.get_direct_recommendation_prompt("title", "artist", rule_preset='minimal')

# 커스텀 프리셋 생성
prompt_manager.add_custom_preset('experimental', ['main_genre_required', 'compound_processing'])
experimental_prompt = prompt_manager.get_genre_refine_prompt("genres...", rule_preset='experimental')

# 동적 프롬프트 생성
custom_prompt = prompt_manager.build_prompt(
    "custom", 
    content="다음 플레이리스트에 적합한 장르를 추천하세요:",
    rules=['main_genre_required', 'practicality']
)

# 규칙 업데이트 (런타임 중)
prompt_manager.update_rule('main_genre_required', "메인 장르 1개는 반드시 포함해야 합니다")

# 사용 가능한 프리셋 확인
available_presets = prompt_manager.get_available_presets()
print(f"Available presets: {available_presets}")

# 프롬프트 유효성 검사
is_valid = prompt_manager.validate_prompt(some_prompt)
"""

# =============================================================================
# 프롬프트 헬퍼 함수들
# =============================================================================

def create_gpt_request(prompt: str, system_message: str = None) -> Dict:
    """GPT 요청 생성 헬퍼"""
    return {
        "model": prompt_manager.MODEL_CONFIG["model"],
        "messages": [
            {"role": "system", "content": system_message or prompt_manager.SYSTEM_MESSAGE},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": prompt_manager.MODEL_CONFIG["max_tokens"],
        "temperature": prompt_manager.MODEL_CONFIG["temperature"]
    }

def get_custom_genre_prompt(content: str, rules: List[str] = None) -> str:
    """커스텀 장르 프롬프트 생성"""
    return prompt_manager.build_prompt(
        "custom", 
        content=content, 
        rules=rules or prompt_manager.RULE_PRESETS['minimal']
    )

# =============================================================================
# 유틸리티 함수들
# =============================================================================

def clean_title(title):
    """곡명에서 마지막 괄호/대괄호 정보를 반복적으로 제거"""
    while True:
        new_title = re.sub(r'\s*[\(\[].*?[\)\]]\s*$', '', title).strip()
        if new_title == title:
            break
        title = new_title
    return title

def clean_artist(artist):
    """아티스트명에서 피처링 정보(ft, feat, featuring, with 등) 이후를 모두 제거"""
    return re.split(r'\b(ft\.?|feat\.?|featuring|with)\b', artist, flags=re.IGNORECASE)[0].strip()

def filter_artist_in_genres(genres, artist):
    """장르 리스트에서 아티스트명(혹은 주요 단어)이 포함된 장르명을 제거"""
    artist_words = set(artist.lower().replace('.', '').replace('-', ' ').split())
    filtered = []
    for g in genres:
        g_lower = g.lower()
        # 아티스트명 전체 또는 단어가 장르명에 포함되면 제외
        if artist.lower() in g_lower:
            continue
        if any(word in g_lower for word in artist_words if len(word) > 2):  # 너무 짧은 단어는 무시
            continue
        filtered.append(g)
    return filtered

def filter_decade_genres(genres):
    """연도/시대 관련 정보가 포함된 장르를 제외"""
    decade_pattern = re.compile(r'(\b(19|20)\d{2}s\b|\b\d{2}s\b|\bdecade\b|\bera\b)', re.IGNORECASE)
    return [g for g in genres if not decade_pattern.search(g)]

def get_discogs_genres(title, artist):
    """Discogs에서 곡/아티스트/릴리즈 장르/스타일 정보 추출 (429 Rate Limit 대응)"""
    genres = []
    try:
        d = discogs_client.Client('SmartGenreTagger/1.0', user_token=config.discogs_token)
        query = f'{title} {artist}'
        try_count = 0
        while try_count < 2:
            try:
                results = d.search(query, type='release', per_page=5)
                for release in results:
                    if hasattr(release, 'genres') and release.genres:
                        genres.extend(release.genres)
                    if hasattr(release, 'styles') and release.styles:
                        genres.extend(release.styles)
                artist_results = d.search(artist, type='artist', per_page=2)
                for a in artist_results:
                    if hasattr(a, 'genres') and a.genres:
                        genres.extend(a.genres)
                    if hasattr(a, 'styles') and a.styles:
                        genres.extend(a.styles)
                genres = list(dict.fromkeys(genres))
                print(f"🎧 Discogs 결과: {title} - {artist} -> {genres}")
                time.sleep(2)
                return genres
            except Exception as e:
                if '429' in str(e):
                    print("🎧 Discogs 429 Rate Limit! 10초 대기 후 재시도...")
                    time.sleep(5)
                    try_count += 1
                    continue
                else:
                    print(f"🎧 Discogs 검색 오류: {e}")
                    return []
        print("🎧 Discogs 429 Rate Limit 2회 초과, 스킵")
        return ['Rate Limited']
    except Exception as e:
        print(f"🎧 Discogs 검색 오류: {e}")
        return []

def clean_compound_genres(genre_string):
    """복합 장르에서 수식어만 추출하고 정리 (하이픈 처리 포함, 특별 예외 처리)"""
    if not genre_string:
        return genre_string
    
    # 특별 변환 규칙 (하이픈 변환 전에 먼저 처리)
    special_conversions = {
        'korean hip hop': 'K-Rap',
        'korean rap': 'K-Rap',
        'k rap': 'K-Rap',
        'k-rap': 'K-Rap'
    }
    
    # 하이픈 유지 예외 목록 (복합 장르 처리에서도 제외)
    hyphen_exceptions = ['k-pop', 'j-pop', 'c-pop', 'k-rap']
    
    # 제외할 의미 없는 태그들
    meaningless_tags = ['contemporary', 'modern', 'new', 'current', 'recent', 'latest', 'music']
    
    genres = [g.strip() for g in genre_string.split('/')]
    processed_genres = []
    special_genres = []  # 특별 처리된 장르들을 따로 보관
    
    for genre in genres:
        genre_lower = genre.lower().strip()
        
        # 빈 문자열 제거
        if not genre_lower:
            continue
            
        # 의미 없는 태그 필터링
        if genre_lower in meaningless_tags:
            continue
            
        # 특별 변환 규칙 적용
        converted = False
        for key, value in special_conversions.items():
            if key in genre_lower:
                special_genres.append(value)
                converted = True
                break
        
        if converted:
            continue
            
        # 하이픈 예외 처리: K-Pop, J-Pop 등은 하이픈 유지하고 특별 처리
        if genre_lower in hyphen_exceptions:
            formatted_genre = genre.title()
            special_genres.append(formatted_genre)  # K-Pop, J-Pop 등으로 정리
        else:
            # 일반적인 하이픈을 띄어쓰기로 변환
            genre = re.sub(r'-', ' ', genre)
            genre = ' '.join(genre.split())  # 여러 공백을 하나로 정리
            processed_genres.append(genre)
    
    # 대분류 키워드들
    main_genres = ['Hip Hop', 'R&B', 'Rock', 'Pop', 'EDM', 'Electronic', 'Jazz', 'Blues', 'Country', 'Folk']
    
    cleaned_genres = []
    main_genre_found = None
    
    # 일반 장르들만 복합 장르 처리
    for genre in processed_genres:
        # 대분류 장르 찾기
        found_main = False
        for main in main_genres:
            if main.lower() in genre.lower():
                if not main_genre_found:
                    main_genre_found = main
                    cleaned_genres.append(main)
                # 복합 장르에서 수식어 추출
                modifier = genre.replace(main, '').strip()
                if modifier and modifier.lower() not in meaningless_tags:
                    cleaned_genres.append(modifier)
                found_main = True
                break
        
        if not found_main:
            # 대분류가 포함되지 않은 순수 세부 장르
            cleaned_genres.append(genre)
    
    # 특별 처리된 장르들을 마지막에 추가
    cleaned_genres.extend(special_genres)
    
    # 중복 제거하면서 순서 유지
    unique_genres = []
    for g in cleaned_genres:
        g = g.strip()
        if g and g not in unique_genres and g.lower() not in meaningless_tags:
            unique_genres.append(g)
    
    result = ' / '.join(unique_genres[:4])  # 최대 4개로 제한
    return result

def titlecase_keep_separators(s):
    """장르 문자열의 각 단어를 대문자로 시작하도록 변경"""
    import re
    
    # GPT 결과는 이미 잘 정리되어 있으므로 clean_compound_genres 적용하지 않음
    # 단순히 첫 글자만 대문자로 변경
    result = re.sub(r'\w+', lambda m: m.group(0).capitalize(), s)
    return result

def gpt_genre_refine(genres_list, title="", artist=""):
    genres_str = ', '.join([f"'{g}'" for g in genres_list if g])
    
    song_info = f"{title} - {artist}" if title and artist else "Unknown Song"
    print(f"🤖 GPT 장르 분석 시작: {song_info}")
    print(f"🤖 입력 장르들: {genres_str}")
    
    prompt = prompt_manager.get_genre_refine_prompt(genres_str)
    request_config = create_gpt_request(prompt)
    
    client = openai.OpenAI(api_key=config.openai_api_key)
    response = client.chat.completions.create(**request_config)
    result = response.choices[0].message.content.strip()
    
    # 지역 장르 후처리 필터링 적용
    filtered_result = filter_regional_genres(result)
    final_result = titlecase_keep_separators(filtered_result)
    
    if result != filtered_result:
        print(f"🤖 GPT 원본 결과: {result}")
        print(f"🚫 지역 장르 필터링 후: {filtered_result}")
    
    print(f"🤖 GPT 장르 분석 완료: {song_info} -> {final_result}")
    return final_result

def filter_regional_genres(genre_result):
    """지역 장르 후처리 필터링"""
    regional_terms = [
        "Southern Hip Hop", "southern hip hop",
        "East Coast Hip Hop", "east coast hip hop", 
        "West Coast Hip Hop", "west coast hip hop",
        "Midwest Hip Hop", "midwest hip hop",
        "Southern", "East Coast", "West Coast", "Midwest"
    ]
    
    genres = [g.strip() for g in genre_result.split('/')]
    filtered_genres = []
    
    for genre in genres:
        # 지역 장르가 포함되어 있으면 제외
        is_regional = False
        for regional in regional_terms:
            if regional.lower() in genre.lower():
                print(f"🚫 지역 장르 필터링: '{genre}' 제외됨")
                is_regional = True
                break
        
        if not is_regional:
            filtered_genres.append(genre)
    
    # 필터링 후 장르가 부족하면 기본 장르 추가
    if len(filtered_genres) < 2:
        if "Hip Hop" not in ' / '.join(filtered_genres):
            filtered_genres.insert(0, "Hip Hop")
    
    result = ' / '.join(filtered_genres[:4])  # 최대 4개로 제한
    return result

def gpt_direct_recommendation(title, artist):
    print(f"🤖 GPT 단독 추천 시작: {title} - {artist}")
    prompt = prompt_manager.get_direct_recommendation_prompt(title, artist)
    
    # 직접 추천에서는 정확성 우선 시스템 메시지 사용
    request_config = create_gpt_request(prompt, prompt_manager.SYSTEM_MESSAGE_DIRECT)
    
    client = openai.OpenAI(api_key=config.openai_api_key)
    response = client.chat.completions.create(**request_config)
    result = response.choices[0].message.content.strip()
    
    # 지역 장르 후처리 필터링 적용
    filtered_result = filter_regional_genres(result)
    final_result = titlecase_keep_separators(filtered_result)
    
    if result != filtered_result:
        print(f"🤖 GPT 원본 결과: {result}")
        print(f"🚫 지역 장르 필터링 후: {filtered_result}")
    
    print(f"🤖 GPT 단독 추천 완료: {title} - {artist} -> {final_result}")
    return final_result

CACHE_FILE = ".genre_cache.pkl"

class PersistentGenreCache:
    def __init__(self, cache_file=CACHE_FILE):
        self.cache_file = cache_file
        self.lock = threading.Lock()
        self._cache = self._load_cache()
    
    def _load_cache(self):
        try:
            with open(self.cache_file, "rb") as f:
                print(f"[캐시] 파일에서 캐시 로드: {self.cache_file}")
                return pickle.load(f)
        except Exception:
            print(f"[캐시] 새 캐시 생성: {self.cache_file}")
            return {}
    
    def save(self):
        with self.lock:
            try:
                with open(self.cache_file, "wb") as f:
                    pickle.dump(self._cache, f)
                print(f"[캐시] 파일로 저장 완료: {self.cache_file}")
            except Exception as e:
                print(f"[캐시] 저장 실패: {e}")
    
    def get(self, key):
        return self._cache.get(key)
    
    def set(self, key, value):
        self._cache[key] = value
    
    def __contains__(self, key):
        return key in self._cache

class MusicGenreService:
    """MusicBrainz + Discogs API를 사용한 장르 정보 서비스 (지속성 캐시 지원)"""
    
    def __init__(self):
        musicbrainzngs.set_useragent("SmartGenreTagger", "1.0", "contact@example.com")
        musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)
        self._genre_cache = PersistentGenreCache()
        self._save_counter = 0

    def get_cached_genre(self, title, artist, year=None):
        key = (title.strip().lower(), artist.strip().lower(), str(year) if year else "")
        result = self._genre_cache.get(key)
        return result

    def set_cached_genre(self, title, artist, year, genre):
        key = (title.strip().lower(), artist.strip().lower(), str(year) if year else "")
        self._genre_cache.set(key, genre)
        self._save_counter += 1
        if self._save_counter % 100 == 0:
            self._genre_cache.save()

    def save_cache(self):
        self._genre_cache.save()

    def get_genre_recommendation(self, title, artist, year=None, original_genre=None):
        try:
            print(f"🎵 ===== 장르 추천 시작 =====")
            print(f"🎵 곡명: {title}")
            print(f"🎵 아티스트: {artist}")
            print(f"🎵 연도: {year}")
            
            cache_hit = self.get_cached_genre(title, artist, year)
            if cache_hit:
                print(f"⚡️ 캐시 적중: {title} - {artist} ({year}) -> {cache_hit}")
                print(f"🎵 ===== 장르 추천 완료 (캐시) =====\n")
                return cache_hit
            print(f"🔍 장르 검색 시작 연도 {year}: {title} - {artist}")
            clean = clean_title(title)
            if clean != title:
                print(f"  ⮕ 전처리된 곡명: {clean}")
            title_for_search = clean
            artist_clean = clean_artist(artist)
            if artist_clean != artist:
                print(f"  ⮕ 전처리된 아티스트명: {artist_clean}")
            artist_for_search = artist_clean
            
            if year and str(year).isdigit() and int(year) <= 2023:
                print(f"🎯 구곡(GPT 단독 추천): {title} - {artist} ({year})")
                # GPT 단독 추천에서는 원본 아티스트명 사용 (피처링 정보 포함)
                result = gpt_direct_recommendation(title_for_search, artist)
                print(f"🎯 GPT 단독 추천 결과: {result}")
                self.set_cached_genre(title, artist, year, result)
                print(f"🎵 ===== 장르 추천 완료 (구곡) =====")
                print(f"🎵 최종 결과: {title} - {artist} -> {result}")
                print(f"🎵 =====================================\n")
                return result
            mb_genres = self._search_musicbrainz(title_for_search, artist_for_search)
            if len(mb_genres) >= 3:
                final_genres = mb_genres
                print(f"🎼 MusicBrainz만으로 충분: {title} - {artist} -> {final_genres}")
            else:
                discogs_genres = get_discogs_genres(title_for_search, artist_for_search)
                final_genres = list(dict.fromkeys(mb_genres + discogs_genres))
                print(f"🎼 통합 장르 리스트: {title} - {artist} -> {final_genres}")
            if final_genres:
                try:
                    gpt_result = gpt_genre_refine(final_genres, title_for_search, artist_for_search)
                    print(f"🤖 GPT 최종 장르 추천: {gpt_result}")
                    self.set_cached_genre(title, artist, year, gpt_result)
                    print(f"🎵 ===== 장르 추천 완료 (신곡) =====")
                    print(f"🎵 최종 결과: {title} - {artist} -> {gpt_result}")
                    print(f"🎵 =====================================\n")
                    return gpt_result
                except Exception as gpt_err:
                    print(f"GPT 호출 오류: {gpt_err}")
            print(f"❌ 장르 정보를 찾을 수 없음")
            if original_genre:
                print(f"➡️ 기존 장르 정보로 대체: {original_genre}")
                self.set_cached_genre(title, artist, year, original_genre)
                print(f"🎵 ===== 장르 추천 완료 (기존) =====")
                print(f"🎵 최종 결과: {title} - {artist} -> {original_genre}")
                print(f"🎵 =====================================\n")
                return original_genre
            print(f"🎵 ===== 장르 추천 완료 (Unknown) =====")
            print(f"🎵 최종 결과: {title} - {artist} -> Unknown Genre")
            print(f"🎵 =====================================\n")
            return "Unknown Genre"
        except Exception as e:
            print(f"❌ 장르 검색 오류: {e}")
            if original_genre:
                print(f"➡️ 기존 장르 정보로 대체: {original_genre}")
                self.set_cached_genre(title, artist, year, original_genre)
                return original_genre
            return f"검색 오류: {str(e)}"
    
    def _search_musicbrainz(self, title, artist):
        """MusicBrainz에서 장르 정보 검색 (429 Rate Limit 대응)"""
        genres = []
        try:
            print(f"📀 MusicBrainz 검색: {title} - {artist}")
            query = f'recording:"{title}" AND artist:"{artist}"'
            try_count = 0
            while try_count < 2:
                try:
                    result = musicbrainzngs.search_recordings(query=query, limit=3)
                    for recording in result.get('recording-list', []):
                        if 'tag-list' in recording:
                            for tag in recording['tag-list']:
                                tag_name = tag['name'].strip()
                                genres.append(tag_name)
                        if 'artist-credit' in recording:
                            for artist_credit in recording['artist-credit']:
                                if isinstance(artist_credit, dict) and 'artist' in artist_credit:
                                    artist_id = artist_credit['artist']['id']
                                    try:
                                        artist_info = musicbrainzngs.get_artist_by_id(artist_id, includes=['tags'])
                                        if 'tag-list' in artist_info['artist']:
                                            for tag in artist_info['artist']['tag-list']:
                                                tag_name = tag['name'].strip()
                                                genres.append(tag_name)
                                    except:
                                        continue
                    genres = list(dict.fromkeys(genres))
                    print(f"📀 MusicBrainz 결과: {title} - {artist} -> {genres}")
                    time.sleep(1)
                    return genres
                except Exception as e:
                    if '429' in str(e):
                        print("📀 MusicBrainz 429 Rate Limit! 10초 대기 후 재시도...")
                        time.sleep(5)
                        try_count += 1
                        continue
                    else:
                        print(f"📀 MusicBrainz 검색 오류: {e}")
                        return []
            print("📀 MusicBrainz 429 Rate Limit 2회 초과, 스킵")
            return ['Rate Limited']
        except Exception as e:
            print(f"📀 MusicBrainz 검색 오류: {e}")
            return []
    
    def _combine_genres(self, mb_genres, discogs_genres, artist=None):
        """MusicBrainz와 Discogs 장르 정보를 단순히 합쳐 중복만 제거"""
        return list(dict.fromkeys(mb_genres + discogs_genres))
    


# 전역 서비스 인스턴스
music_genre_service = MusicGenreService() 