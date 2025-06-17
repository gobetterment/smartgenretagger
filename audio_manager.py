import os
import eyed3
import pygame
import threading
from typing import List, Dict, Optional
from mutagen.id3 import ID3, ID3NoHeaderError, Encoding, TYER
from mutagen.mp3 import MP3

class AudioFileProcessor:
    """MP3 파일 처리 클래스"""
    
    @staticmethod
    def extract_metadata(file_path: str) -> Dict:
        """MP3 파일에서 메타데이터 추출 (상세 로그 추가)"""
        try:
            print(f"extract_metadata: 파일 로드 시도 - {file_path}")
            audio = eyed3.load(file_path)
            if not audio or not audio.tag:
                print(f"extract_metadata: 태그 없음 - {file_path}")
                return AudioFileProcessor._create_empty_metadata(file_path)
            title = audio.tag.title or os.path.basename(file_path)
            artist = audio.tag.artist or "Unknown Artist"
            genre = audio.tag.genre.name if audio.tag.genre else ""
            year, original_year = AudioFileProcessor._extract_year_info(audio.tag)
            if year:
                print(f"extract_metadata: 연도 발견 - 파일: {os.path.basename(file_path)}, 연도: {year}")
            else:
                print(f"extract_metadata: 연도 없음 - 파일: {os.path.basename(file_path)}")
            print(f"extract_metadata: 메타데이터 추출 성공 - {file_path}")
            return {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'title': title,
                'artist': artist,
                'year': year,
                'original_year': original_year,
                'year_added': False,
                'genre': genre,
                'genre_suggestion': ""
            }
        except Exception as e:
            print(f"extract_metadata: 파일 로드 오류 {file_path}: {e}")
            return None
    
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
            'genre_suggestion': ""
        }
    
    @staticmethod
    def upgrade_id3_to_v23_utf16(file_path: str):
        """ID3 태그를 v2.3(UTF-16)으로 강제 변환 (latin-1 오류 방지)"""
        try:
            audio = MP3(file_path)
            try:
                tags = ID3(file_path)
            except ID3NoHeaderError:
                tags = ID3()
            tags.update_to_v23()
            for frame in tags.values():
                if hasattr(frame, 'encoding'):
                    frame.encoding = Encoding.UTF16
            tags.save(file_path, v2_version=3)
            print(f"ID3 태그를 v2.3(UTF-16)으로 변환 완료: {file_path}")
        except Exception as e:
            print(f"ID3 변환 오류: {e}")

    @staticmethod
    def ensure_year_tyer(file_path: str, year: str):
        """mutagen으로 TYER(Year) 프레임에 연도 저장"""
        try:
            tags = ID3(file_path)
            tags.delall('TYER')
            tags.add(TYER(encoding=3, text=str(year)))
            tags.save(file_path, v2_version=3)
            print(f"TYER(Year) 프레임에 연도 저장 완료: {year}")
        except Exception as e:
            print(f"TYER 저장 오류: {e}")

    @staticmethod
    def save_metadata(data: Dict) -> bool:
        """메타데이터를 MP3 파일에 저장 (ID3 v2.3, UTF-16 강제, mutagen 변환, TYER 동기화)"""
        path = data['path']
        try:
            AudioFileProcessor.upgrade_id3_to_v23_utf16(path)
            import eyed3
            audio = eyed3.load(path)
            if not audio.tag:
                audio.initTag()
            if audio.tag.version != (2, 3, 0):
                audio.tag.version = (2, 3, 0)
            if data.get('genre_suggestion', ''):
                audio.tag.genre = data['genre_suggestion']
                data['genre'] = data['genre_suggestion']
            year_value = data['year'].replace(" ✓", "") if data['year'] else ""
            original_year = data['original_year'] if data['original_year'] else ""
            if original_year != year_value:
                if year_value and year_value.isdigit():
                    year_int = int(year_value)
                    audio.tag.original_release_date = eyed3.core.Date(year_int)
                    print(f"Debug: 연도 저장됨 - {data['filename']}: {year_value}")
                else:
                    audio.tag.original_release_date = None
                    print(f"Debug: 연도 삭제됨 - {data['filename']}")
            audio.tag.save()
            # mutagen으로 TYER 프레임에도 연도 저장
            if year_value and year_value.isdigit():
                AudioFileProcessor.ensure_year_tyer(path, year_value)
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