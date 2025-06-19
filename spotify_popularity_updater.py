#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spotify 인기도 업데이터
CSV 파일의 곡 목록에 Spotify 인기도 정보를 추가하는 스크립트

사용법:
1. .env 파일에 Spotify API 키 설정
2. python spotify_popularity_updater.py 실행
3. CSV 파일 선택
4. 결과 파일 저장 위치 선택

필요한 패키지:
pip install spotipy python-dotenv pandas
"""

import os
import sys
import csv
import time
import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    print("❌ spotipy 패키지가 설치되지 않았습니다.")
    print("다음 명령어로 설치해주세요: pip install spotipy")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ python-dotenv 패키지가 설치되지 않았습니다.")
    print("다음 명령어로 설치해주세요: pip install python-dotenv")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("❌ pandas 패키지가 설치되지 않았습니다.")
    print("다음 명령어로 설치해주세요: pip install pandas")
    sys.exit(1)


class SpotifyPopularityUpdater:
    """Spotify 인기도 업데이터 클래스"""
    
    def __init__(self):
        self.spotify = None
        self.cache = {}  # 검색 결과 캐시
        self.processed_count = 0
        self.total_count = 0
        self.is_cancelled = False
        
        # GUI 컴포넌트
        self.root = None
        self.progress_var = None
        self.status_var = None
        self.progress_bar = None
        
    def load_spotify_credentials(self) -> bool:
        """Spotify API 인증 정보 로드"""
        try:
            # .env 파일 로드
            load_dotenv()
            
            client_id = os.getenv('SPOTIFY_CLIENT_ID')
            client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                print("❌ .env 파일에서 Spotify API 키를 찾을 수 없습니다.")
                print("다음 변수들을 .env 파일에 추가해주세요:")
                print("SPOTIFY_CLIENT_ID=your_client_id")
                print("SPOTIFY_CLIENT_SECRET=your_client_secret")
                return False
            
            # Spotify 클라이언트 초기화
            credentials = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            self.spotify = spotipy.Spotify(client_credentials_manager=credentials)
            
            # 연결 테스트
            test_result = self.spotify.search(q="test", type="track", limit=1)
            print("✅ Spotify API 연결 성공!")
            return True
            
        except Exception as e:
            print(f"❌ Spotify API 초기화 실패: {e}")
            return False
    
    def clean_search_query(self, title: str, artist: str) -> str:
        """검색 쿼리 정리 - 더 정교한 정리"""
        # 제목 정리
        title_clean = title.strip()
        
        # Clean/Dirty, Remix, Extended 등 제거
        title_clean = re.sub(r'\s*\((Clean|Dirty|Explicit|Radio Edit|Album Version|Extended|Main)\)\s*', '', title_clean, flags=re.IGNORECASE)
        title_clean = re.sub(r'\s*(Clean|Dirty|Explicit|Radio Edit|Album Version|Extended|Main)\s*', '', title_clean, flags=re.IGNORECASE)
        
        # Remix 관련 제거
        title_clean = re.sub(r'\s*\((.*?Remix.*?|.*?Edit.*?)\)\s*', '', title_clean, flags=re.IGNORECASE)
        title_clean = re.sub(r'\s*(Remix|Edit)\s*', '', title_clean, flags=re.IGNORECASE)
        
        # 기타 괄호 내용 제거
        title_clean = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', title_clean).strip()
        
        # 특수문자 정리 (더 보수적으로)
        title_clean = re.sub(r'[^\w\s가-힣\'-]', ' ', title_clean).strip()
        title_clean = re.sub(r'\s+', ' ', title_clean).strip()
        
        # 아티스트 정리
        artist_clean = artist.strip()
        
        # ft, feat 등과 그 뒤의 내용 모두 제거
        artist_clean = re.split(r'\s+(ft\.?|feat\.?|featuring|with|&|\+)\s+', artist_clean, flags=re.IGNORECASE)[0].strip()
        
        # 괄호 내용 제거
        artist_clean = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', artist_clean).strip()
        
        # 특수문자 정리
        artist_clean = re.sub(r'[^\w\s가-힣\'-]', ' ', artist_clean).strip()
        artist_clean = re.sub(r'\s+', ' ', artist_clean).strip()
        
        return f"{title_clean} {artist_clean}".strip()
    
    def search_spotify_track(self, title: str, artist: str) -> Optional[Dict]:
        """Spotify에서 트랙 검색 - 다단계 검색 전략"""
        # 캐시 확인
        cache_key = f"{title.lower()}|{artist.lower()}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # 검색 전략들을 순서대로 시도
            search_strategies = [
                # 1. 기본 검색 (제목 + 아티스트)
                lambda: self.clean_search_query(title, artist),
                # 2. Spotify 고급 검색 문법 사용
                lambda: f'track:"{title.split("(")[0].strip()}" artist:"{artist.split("ft")[0].split("feat")[0].strip()}"',
                # 3. 제목만 검색
                lambda: title.split("(")[0].strip(),
                # 4. 제목에서 특수문자 모두 제거
                lambda: re.sub(r'[^\w\s가-힣]', ' ', title).strip(),
                # 5. 아티스트만 검색
                lambda: artist.split("ft")[0].split("feat")[0].strip(),
                # 6. 제목의 첫 단어들만 검색
                lambda: ' '.join(title.split()[:3]) if len(title.split()) > 2 else title
            ]
            
            for i, strategy in enumerate(search_strategies):
                query = strategy()
                if not query or len(query.strip()) < 2:
                    continue
                
                # Spotify 검색 (더 많은 결과 요청)
                results = self.spotify.search(q=query, type="track", limit=20)
                tracks = results.get('tracks', {}).get('items', [])
                
                if tracks:
                    # 가장 적합한 트랙 찾기
                    best_match = self.find_best_match(tracks, title, artist)
                    if best_match:
                        # 캐시에 저장
                        self.cache[cache_key] = best_match
                        return best_match
                
                # Rate Limit 방지
                time.sleep(0.05)
            
            # 모든 전략 실패
            self.cache[cache_key] = None
            return None
            
        except Exception as e:
            print(f"🔍 검색 오류 ({title} - {artist}): {e}")
            self.cache[cache_key] = None
            return None
    
    def find_best_match(self, tracks: List[Dict], target_title: str, target_artist: str) -> Optional[Dict]:
        """가장 적합한 트랙 찾기 - 더 관대한 매칭"""
        if not tracks:
            return None
        
        # 타겟 정보 정리
        target_title_clean = self.normalize_text(target_title)
        target_artist_clean = self.normalize_text(target_artist)
        
        best_score = 0
        best_track = None
        
        for track in tracks:
            track_title = self.normalize_text(track['name'])
            track_artists = [self.normalize_text(artist['name']) for artist in track['artists']]
            
            # 제목 유사도 계산
            title_score = self.calculate_similarity(target_title_clean, track_title)
            
            # 아티스트 유사도 계산 (모든 아티스트 중 가장 높은 점수)
            artist_score = 0
            for track_artist in track_artists:
                score = self.calculate_similarity(target_artist_clean, track_artist)
                artist_score = max(artist_score, score)
            
            # 전체 점수 계산 (제목 60%, 아티스트 40%)
            total_score = title_score * 0.6 + artist_score * 0.4
            
            # 더 관대한 매칭 기준 (40% → 30%)
            if total_score > best_score and total_score > 0.3:
                best_score = total_score
                best_track = {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'popularity': track['popularity'],
                    'external_urls': track['external_urls']['spotify'],
                    'similarity_score': total_score
                }
        
        return best_track
    
    def normalize_text(self, text: str) -> str:
        """텍스트 정규화 - 비교를 위한 표준화"""
        if not text:
            return ""
        
        # 소문자 변환
        text = text.lower().strip()
        
        # Clean/Dirty 등 제거
        text = re.sub(r'\s*\((clean|dirty|explicit|radio edit|album version|extended|main)\)\s*', '', text)
        text = re.sub(r'\s+(clean|dirty|explicit|radio edit|album version|extended|main)\s*', '', text)
        
        # feat, ft 등 제거
        text = re.split(r'\s+(ft\.?|feat\.?|featuring|with|&|\+)\s+', text)[0].strip()
        
        # 괄호 내용 제거
        text = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', text).strip()
        
        # 특수문자를 공백으로 변환
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        
        # 연속된 공백을 하나로
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """문자열 유사도 계산 - 개선된 알고리즘"""
        if not str1 or not str2:
            return 0.0
        
        # 완전 일치
        if str1 == str2:
            return 1.0
        
        # 포함 관계 확인 (더 관대하게)
        if str1 in str2 or str2 in str1:
            shorter = min(len(str1), len(str2))
            longer = max(len(str1), len(str2))
            return max(0.7, shorter / longer)  # 최소 70% 점수 보장
        
        # 단어 기반 유사도
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard 유사도
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        jaccard = intersection / union if union > 0 else 0.0
        
        # 부분 문자열 매칭도 고려
        partial_score = 0.0
        for word1 in words1:
            for word2 in words2:
                if len(word1) >= 3 and len(word2) >= 3:  # 3글자 이상만 비교
                    if word1 in word2 or word2 in word1:
                        partial_score = max(partial_score, 0.5)
        
        # 최종 점수 (Jaccard + 부분 매칭)
        return max(jaccard, partial_score)
    
    def process_csv(self, input_file: str, output_file: str) -> bool:
        """CSV 파일 처리"""
        try:
            # CSV 파일 읽기
            df = pd.read_csv(input_file, encoding='utf-8-sig')
            
            # 필수 컬럼 확인
            required_columns = ['제목', '아티스트']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                messagebox.showerror("오류", f"필수 컬럼이 없습니다: {', '.join(missing_columns)}")
                return False
            
            # 새 컬럼들 추가
            df['Spotify_인기도'] = ''
            df['Spotify_URL'] = ''
            df['검색_결과'] = ''
            
            self.total_count = len(df)
            self.processed_count = 0
            
            # 각 행 처리
            for index, row in df.iterrows():
                if self.is_cancelled:
                    break
                
                title = str(row['제목']).strip()
                artist = str(row['아티스트']).strip()
                
                if not title or not artist or title == 'nan' or artist == 'nan':
                    df.at[index, '검색_결과'] = '정보 부족'
                    self.processed_count += 1
                    self.update_progress()
                    continue
                
                # Spotify 검색
                track_info = self.search_spotify_track(title, artist)
                
                if track_info:
                    df.at[index, 'Spotify_인기도'] = track_info['popularity']
                    df.at[index, 'Spotify_URL'] = track_info['external_urls']
                    df.at[index, '검색_결과'] = f"발견 (유사도: {track_info['similarity_score']:.2f})"
                    print(f"✅ {title} - {artist}")
                    print(f"   → 발견: {track_info['name']} - {', '.join(track_info['artists'])}")
                    print(f"   → 인기도: {track_info['popularity']}, 유사도: {track_info['similarity_score']:.2f}")
                else:
                    df.at[index, '검색_결과'] = '찾을 수 없음'
                    print(f"❌ {title} - {artist} → 모든 검색 전략 실패")
                
                self.processed_count += 1
                self.update_progress()
            
            # 결과 저장
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            if not self.is_cancelled:
                found_count = len(df[df['Spotify_인기도'] != ''])
                messagebox.showinfo("완료", 
                    f"처리 완료!\n\n"
                    f"전체 곡 수: {self.total_count}개\n"
                    f"발견된 곡: {found_count}개\n"
                    f"성공률: {found_count/self.total_count*100:.1f}%\n\n"
                    f"결과 파일: {output_file}")
            
            return True
            
        except Exception as e:
            messagebox.showerror("오류", f"CSV 처리 중 오류 발생:\n{str(e)}")
            return False
    
    def update_progress(self):
        """진행률 업데이트"""
        if self.progress_var and self.status_var:
            progress = (self.processed_count / self.total_count) * 100
            self.progress_var.set(progress)
            self.status_var.set(f"처리 중... {self.processed_count}/{self.total_count}")
            
            if self.root:
                self.root.update()
    
    def select_input_file(self) -> Optional[str]:
        """입력 CSV 파일 선택"""
        return filedialog.askopenfilename(
            title="처리할 CSV 파일 선택",
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")]
        )
    
    def select_output_file(self, input_file: str) -> Optional[str]:
        """출력 CSV 파일 선택"""
        # 기본 파일명 생성
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{base_name}_with_spotify_popularity_{timestamp}.csv"
        
        return filedialog.asksaveasfilename(
            title="결과 파일 저장 위치",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")]
        )
    
    def create_gui(self):
        """GUI 생성"""
        self.root = tk.Tk()
        self.root.title("Spotify 인기도 업데이터")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 제목
        title_label = ttk.Label(main_frame, text="🎵 Spotify 인기도 업데이터", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 설명
        desc_label = ttk.Label(main_frame, 
            text="CSV 파일의 곡 목록에 Spotify 인기도 정보를 추가합니다.\n"
                 "CSV 파일에는 '제목'과 '아티스트' 컬럼이 필요합니다.",
            justify=tk.CENTER)
        desc_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # 시작 버튼
        start_button = ttk.Button(main_frame, text="📁 CSV 파일 선택 및 시작", command=self.start_processing)
        start_button.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        # 진행률 바
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 상태 레이블
        self.status_var = tk.StringVar(value="대기 중...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=4, column=0, columnspan=2)
        
        # 취소 버튼
        cancel_button = ttk.Button(main_frame, text="❌ 취소", command=self.cancel_processing)
        cancel_button.grid(row=5, column=0, columnspan=2, pady=(20, 0))
        
        # 그리드 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
    
    def start_processing(self):
        """처리 시작"""
        # 입력 파일 선택
        input_file = self.select_input_file()
        if not input_file:
            return
        
        # 출력 파일 선택
        output_file = self.select_output_file(input_file)
        if not output_file:
            return
        
        # Spotify API 초기화
        if not self.load_spotify_credentials():
            messagebox.showerror("오류", "Spotify API 초기화에 실패했습니다.\n.env 파일의 API 키를 확인해주세요.")
            return
        
        # 백그라운드에서 처리
        self.is_cancelled = False
        self.status_var.set("처리 중...")
        
        def process_thread():
            self.process_csv(input_file, output_file)
            if not self.is_cancelled:
                self.status_var.set("완료!")
            else:
                self.status_var.set("취소됨")
        
        thread = threading.Thread(target=process_thread)
        thread.daemon = True
        thread.start()
    
    def cancel_processing(self):
        """처리 취소"""
        self.is_cancelled = True
        self.status_var.set("취소 중...")
    
    def run(self):
        """메인 실행"""
        print("🎵 Spotify 인기도 업데이터 시작")
        print("=" * 50)
        
        self.create_gui()
        self.root.mainloop()


def main():
    """메인 함수"""
    try:
        updater = SpotifyPopularityUpdater()
        updater.run()
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main() 