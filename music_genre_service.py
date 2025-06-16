import musicbrainzngs
import discogs_client
import time
import re
from config import config
import openai

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
    """Discogs에서 곡/아티스트/릴리즈 장르/스타일 정보 추출"""
    genres = []
    try:
        d = discogs_client.Client('SmartGenreTagger/1.0', user_token=config.discogs_token)
        query = f'{title} {artist}'
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
        print(f"🎧 Discogs 결과: {genres}")
        time.sleep(2)
        return genres
    except Exception as e:
        print(f"🎧 Discogs 검색 오류: {e}")
        return []

prompt_template = '''
너는 장르 큐레이션에 능한 베테랑 DJ다.

아래는 한 곡에 대해 MusicBrainz와 Discogs에서 수집한 장르 리스트다:

{genres_list}

이 리스트만 참고해서, DJing에 적합하게 장르를 정리해줘.  
아래 조건을 반드시 지켜:

---

🎧 분류 기준

1. **Genre (필수)**: 전체 분위기를 대표하는 포괄 장르 최대 3개 (예: Hip Hop, Pop, Rock, R&B, EDM 등)
2. **Style (선택)**: DJing에 유용한 세부 스타일 1~2개 (예: Trap, Pop Rap, Amapiano 등)
3. **Region (선택)**: 지역 특성이 있으면 포함 (예: Southern, West Coast, Afrobeat 등)
4. **Audience (선택)**: 대상 기반 장르가 있을 경우 포함 (예: LGBTQ, K-pop Fandom 등)
5. 검색한 곡과 어울리지 않거나 관련도가 낮은 장르는 반드시 제외해라.
6. 하나의 곡에 너무 다양한 장르를 억지로 섞지 말고, 곡 분위기와 아티스트 스타일에 맞는 핵심 장르 위주로 뽑아라. (예: "Grove St. Party" 같은 곡에는 Rock, Reggae, Pop Rap 같은 장르는 부적절하다.

---

🚫 절대 금지

- 리스트에 없는 장르 추가 금지
- 'alternative', 'contemporary', 'experimental', '5th gen' 등 **불필요한 수식어 제거**
- 'Soul', 'Funk', 'R&B'는 비슷한 계열이므로 **중복 최소화** (예: 둘 중 하나만 선택)
- Audience 태그(K-pop Fandom, LGBTQ 등)는 **곡 전체 분위기와 아티스트 특성에 부합할 때만 포함**해라.
- '1990s', '2000s', '2010s', '2020s' 등 **연대 기반 태그는 절대 포함하지 마라.**
- 'era', 'decade', 'generation' 관련 단어도 결과에 나오면 안 된다.
- 단순히 장르 리스트에 'K-pop'이 존재한다고 무조건 포함하지 말고, **실제 K-pop 아티스트나 한국 음악일 때만** 넣어라.
- Chris Brown, Lil Nas X, CKay 같은 글로벌 아티스트는 K-pop이 아님.
- **최종 결과는 반드시 6개 이하로만 구성**해야 하며, 초과 시 오답 처리됨
- 최종 출력은 **한 줄**, 항목은 `/` 로 구분, 정제된 형태로 출력

---

📌 출력 예시  
Pop / Dance-pop / House / K-pop Fandom  
Hip Hop / Trap / Pop Rap / LGBTQ  

---

자, 위 기준을 지켜서 아래 장르 리스트를 정리해줘:  
{genres_list}
'''

def gpt_genre_refine(genres_list):
    genres_str = ', '.join([f"'{g}'" for g in genres_list if g])
    
    print(f"🤖 GPT 장르 분석 시작genres_str: {genres_str}")
    
    prompt = prompt_template.replace('{genres_list}', genres_str)
    client = openai.OpenAI(api_key=config.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional DJ and music genre expert."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=256,
        temperature=0.3,
    )
    result = response.choices[0].message.content.strip()
    def titlecase_keep_separators(s):
        import re
        return re.sub(r'\w+', lambda m: m.group(0).capitalize(), s)
    return titlecase_keep_separators(result)

def gpt_direct_recommendation(title, artist):
    prompt = f"""
너는 장르 큐레이션에 능한 베테랑 DJ다.
아래 곡의 대표 장르를 DJing에 적합하게 추천해줘.

아티스트: {artist}
곡명: {title}

1. **Genre (필수)**: 전체 분위기를 대표하는 포괄 장르 최대 3개 (예: Hip Hop, Pop, Rock, R&B, EDM 등)
2. **Style (선택)**: DJing에 유용한 세부 스타일 1~2개 (예: Trap, Pop Rap, Amapiano 등)
3. **Region (선택)**: 지역 특성이 있으면 포함 (예: Southern, West Coast, Afrobeat 등)
4. **Audience (선택)**: 대상 기반 장르가 있을 경우 포함 (예: LGBTQ, K-pop Fandom 등)
5. 검색한 곡과 어울리지 않거나 관련도가 낮은 장르는 반드시 제외해라.
6. 하나의 곡에 너무 다양한 장르를 억지로 섞지 말고, 곡 분위기와 아티스트 스타일에 맞는 핵심 장르 위주로 뽑아라. (예: “Grove St. Party” 같은 곡에는 Rock, Reggae, Pop Rap 같은 장르는 부적절하다.

- 최종 출력은 한 줄, 항목은 /로 구분

예시)
Hip Hop / Trap / Southern / LGBTQ
"""
    client = openai.OpenAI(api_key=config.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional DJ and music genre expert."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=256,
        temperature=0.3,
    )
    result = response.choices[0].message.content.strip()
    def titlecase_keep_separators(s):
        import re
        return re.sub(r'\w+', lambda m: m.group(0).capitalize(), s)
    return titlecase_keep_separators(result)

class MusicGenreService:
    """MusicBrainz + Discogs API를 사용한 장르 정보 서비스"""
    
    def __init__(self):
        # MusicBrainz 설정
        musicbrainzngs.set_useragent("SmartGenreTagger", "1.0", "contact@example.com")
        musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)
    
    def get_genre_recommendation(self, title, artist, year=None, original_genre=None):
        """곡 제목과 아티스트로 장르 정보 가져오기"""
        try:
            print(f"🔍 장르 검색 시작 연도 {year}: {title} - {artist}")
            clean = clean_title(title)
            if clean != title:
                print(f"  ⮕ 전처리된 곡명: {clean}")
            title_for_search = clean
            artist_clean = clean_artist(artist)
            if artist_clean != artist:
                print(f"  ⮕ 전처리된 아티스트명: {artist_clean}")
            artist_for_search = artist_clean
            # 연도 기준 분기
            if year and str(year).isdigit() and int(year) <= 2023:
                print(f"🎯 구곡(GPT 단독 추천): {year}")
                return gpt_direct_recommendation(title_for_search, artist_for_search)
            # 최신곡 또는 연도 정보 없음: API+GPT
            mb_genres = self._search_musicbrainz(title_for_search, artist_for_search)
            if len(mb_genres) >= 6:
                final_genres = mb_genres
                print(f"🎼 MusicBrainz만으로 충분: {final_genres}")
            else:
                discogs_genres = get_discogs_genres(title_for_search, artist_for_search)
                final_genres = list(dict.fromkeys(mb_genres + discogs_genres))
                print(f"🎼 통합 장르 리스트: {final_genres}")
            if final_genres:
                try:
                    gpt_result = gpt_genre_refine(final_genres)
                    print(f"🤖 GPT 최종 장르 추천: {gpt_result}")
                    return gpt_result
                except Exception as gpt_err:
                    print(f"GPT 호출 오류: {gpt_err}")
            print(f"❌ 장르 정보를 찾을 수 없음")
            if original_genre:
                print(f"➡️ 기존 장르 정보로 대체: {original_genre}")
                return original_genre
            return "Unknown Genre"
        except Exception as e:
            print(f"❌ 장르 검색 오류: {e}")
            if original_genre:
                print(f"➡️ 기존 장르 정보로 대체: {original_genre}")
                return original_genre
            return f"검색 오류: {str(e)}"
    
    def _search_musicbrainz(self, title, artist):
        """MusicBrainz에서 장르 정보 검색"""
        genres = []
        try:
            print(f"📀 MusicBrainz 검색: {title} - {artist}")
            
            # 곡 검색
            query = f'recording:"{title}" AND artist:"{artist}"'
            result = musicbrainzngs.search_recordings(query=query, limit=5)
            
            for recording in result.get('recording-list', []):
                # 태그에서 장르 정보 추출
                if 'tag-list' in recording:
                    for tag in recording['tag-list']:
                        tag_name = tag['name'].strip()
                        genres.append(tag_name)
                
                # 아티스트 정보에서 장르 추출
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
            
            # 중복 제거 및 정리
            genres = list(dict.fromkeys(genres))  # 순서 유지하며 중복 제거
            print(f"📀 MusicBrainz 결과: {genres}")
            
            time.sleep(1)  # Rate limiting
            return genres
            
        except Exception as e:
            print(f"📀 MusicBrainz 검색 오류: {e}")
            return []
    
    def _combine_genres(self, mb_genres, discogs_genres, artist=None):
        """MusicBrainz와 Discogs 장르 정보를 단순히 합쳐 중복만 제거"""
        return list(dict.fromkeys(mb_genres + discogs_genres))
    


# 전역 서비스 인스턴스
music_genre_service = MusicGenreService() 