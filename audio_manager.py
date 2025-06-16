import os
import eyed3
import pygame
import threading
from typing import List, Dict, Optional

class AudioFileProcessor:
    """MP3 파일 처리 클래스"""
    
    @staticmethod
    def extract_metadata(file_path: str) -> Dict:
        """MP3 파일에서 메타데이터 추출"""
        try:
            audio = eyed3.load(file_path)
            if not audio or not audio.tag:
                return AudioFileProcessor._create_empty_metadata(file_path)
            
            title = audio.tag.title or os.path.basename(file_path)
            artist = audio.tag.artist or "Unknown Artist"
            genre = audio.tag.genre.name if audio.tag.genre else ""
            
            # 연도 정보 가져오기 (다양한 ID3 태그 필드 확인)
            year, original_year = AudioFileProcessor._extract_year_info(audio.tag)
            
            # 디버그 출력
            if year:
                print(f"Debug: 연도 발견 - 파일: {os.path.basename(file_path)}, 연도: {year}")
            else:
                print(f"Debug: 연도 없음 - 파일: {os.path.basename(file_path)}")
            
            return {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'title': title,
                'artist': artist,
                'year': year,
                'original_year': original_year,
                'year_added': False,
                'genre': genre,
                'gpt_suggestion': ""
            }
            
        except Exception as e:
            print(f"파일 로드 오류 {file_path}: {e}")
            return AudioFileProcessor._create_empty_metadata(file_path)
    
    @staticmethod
    def _extract_year_info(tag) -> tuple:
        """ID3 태그에서 연도 정보 추출"""
        year = ""
        original_year = ""
        
        # 1. original_release_date 확인
        if tag.original_release_date:
            year = str(tag.original_release_date.year)
            original_year = year
        # 2. release_date 확인
        elif tag.release_date:
            year = str(tag.release_date.year)
            original_year = year
        # 3. recording_date 확인
        elif tag.recording_date:
            year = str(tag.recording_date.year)
            original_year = year
        # 4. TYER (Year) 프레임 확인 (ID3v2.3)
        elif hasattr(tag, 'frame_set') and tag.frame_set.get(b'TYER'):
            tyer_frame = tag.frame_set[b'TYER'][0]
            if tyer_frame and tyer_frame.text:
                year = str(tyer_frame.text).strip()
                original_year = year
        # 5. TDRC (Recording time) 프레임 확인 (ID3v2.4)
        elif hasattr(tag, 'frame_set') and tag.frame_set.get(b'TDRC'):
            tdrc_frame = tag.frame_set[b'TDRC'][0]
            if tdrc_frame and tdrc_frame.text:
                year_text = str(tdrc_frame.text).strip()
                # YYYY-MM-DD 형식에서 연도만 추출
                if len(year_text) >= 4 and year_text[:4].isdigit():
                    year = year_text[:4]
                    original_year = year
        # 6. TDRL (Release time) 프레임 확인 (ID3v2.4)
        elif hasattr(tag, 'frame_set') and tag.frame_set.get(b'TDRL'):
            tdrl_frame = tag.frame_set[b'TDRL'][0]
            if tdrl_frame and tdrl_frame.text:
                year_text = str(tdrl_frame.text).strip()
                # YYYY-MM-DD 형식에서 연도만 추출
                if len(year_text) >= 4 and year_text[:4].isdigit():
                    year = year_text[:4]
                    original_year = year
        
        return year, original_year
    
    @staticmethod
    def _create_empty_metadata(file_path: str) -> Dict:
        """빈 메타데이터 생성"""
        return {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'title': os.path.basename(file_path),
            'artist': "Unknown Artist",
            'year': "",
            'original_year': "",
            'year_added': False,
            'genre': "",
            'gpt_suggestion': ""
        }
    
    @staticmethod
    def save_metadata(data: Dict) -> bool:
        """메타데이터를 MP3 파일에 저장"""
        path = data['path']
        
        try:
            audio = eyed3.load(path)
            if not audio.tag:
                audio.initTag()
            
            # GPT 추천이 있으면 장르에 적용
            if data['gpt_suggestion']:
                audio.tag.genre = data['gpt_suggestion']
                data['genre'] = data['gpt_suggestion']
            
            # 연도 정보 처리 (추가/수정/삭제)
            year_value = data['year'].replace(" ✓", "") if data['year'] else ""
            original_year = data['original_year'] if data['original_year'] else ""
            
            # 연도가 변경된 경우 (추가, 수정, 삭제 모두 포함)
            if original_year != year_value:
                if year_value and year_value.isdigit():
                    # 연도 추가/수정
                    year_int = int(year_value)
                    audio.tag.original_release_date = eyed3.core.Date(year_int)
                    print(f"Debug: 연도 저장됨 - {data['filename']}: {year_value}")
                else:
                    # 연도 삭제 (빈 값으로 설정)
                    audio.tag.original_release_date = None
                    print(f"Debug: 연도 삭제됨 - {data['filename']}")
            
            audio.tag.save()
            print(f"저장 완료: {data['filename']}")
            return True
            
        except Exception as e:
            print(f"저장 오류 {data['filename']}: {e}")
            return False
    
    @staticmethod
    def get_mp3_files(folder_path: str) -> List[str]:
        """폴더에서 MP3 파일 목록 가져오기"""
        return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".mp3")]
    
    @staticmethod
    def get_file_duration(file_path: str) -> float:
        """MP3 파일의 길이(초) 반환"""
        try:
            audio = eyed3.load(file_path)
            if audio and audio.info:
                return audio.info.time_secs
        except:
            pass
        return 0


class AudioPlayer:
    """오디오 재생 관리 클래스"""
    
    def __init__(self):
        pygame.mixer.init()
        self.is_playing = False
        self.current_file = None
        self.song_length = 0
        self.current_pos = 0
        self.seeking = False
        self._playback_thread = None
    
    def play(self, file_path: str) -> bool:
        """파일 재생"""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            self.current_file = file_path
            self.song_length = AudioFileProcessor.get_file_duration(file_path)
            self.current_pos = 0
            self.is_playing = True
            
            # 재생 모니터링 시작
            self._start_playback_monitoring()
            
            print(f"재생 시작: {os.path.basename(file_path)}")
            return True
            
        except Exception as e:
            print(f"재생 오류: {e}")
            return False
    
    def pause(self):
        """재생 일시정지"""
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            print("재생 일시정지")
    
    def resume(self):
        """재생 재개"""
        if not self.is_playing and self.current_file:
            pygame.mixer.music.unpause()
            self.is_playing = True
            print("재생 재개")
    
    def stop(self):
        """재생 중지"""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.current_pos = 0
        print("재생 중지")
    
    def set_position(self, position: float):
        """재생 위치 설정"""
        self.current_pos = position
        try:
            pygame.mixer.music.set_pos(position)
        except:
            # set_pos가 지원되지 않는 경우
            pass
    
    def _start_playback_monitoring(self):
        """재생 모니터링 시작"""
        if self._playback_thread and self._playback_thread.is_alive():
            return
        
        self._playback_thread = threading.Thread(target=self._monitor_playback, daemon=True)
        self._playback_thread.start()
    
    def _monitor_playback(self):
        """재생 상태 모니터링 (별도 스레드에서 실행)"""
        while self.is_playing and pygame.mixer.music.get_busy():
            if not self.seeking:
                self.current_pos += 0.1
            threading.Event().wait(0.1)
        
        # 재생 완료 시
        if self.is_playing:
            self.is_playing = False
            self.current_pos = 0
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """초를 MM:SS 형식으로 변환"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}" 