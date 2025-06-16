import os
import json
import hashlib
from datetime import datetime, timedelta


class AnalysisCache:
    """분석 결과 캐싱 매니저"""
    
    def __init__(self, cache_dir="cache", cache_duration_days=30):
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(days=cache_duration_days)
        
        # 캐시 디렉토리 생성
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _get_cache_key(self, title, artist):
        """캐시 키 생성"""
        # 제목과 아티스트를 정규화하여 일관된 키 생성
        normalized_title = title.lower().strip()
        normalized_artist = artist.lower().strip()
        cache_string = f"{normalized_artist}_{normalized_title}"
        
        # SHA256 해시로 파일명 생성
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key):
        """캐시 파일 경로 생성"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def get_cached_analysis(self, title, artist):
        """캐시된 분석 결과 가져오기"""
        try:
            cache_key = self._get_cache_key(title, artist)
            cache_file = self._get_cache_file_path(cache_key)
            
            if not os.path.exists(cache_file):
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 캐시 만료 확인
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > self.cache_duration:
                # 만료된 캐시 삭제
                os.remove(cache_file)
                return None
            
            return cache_data['analysis']
            
        except Exception as e:
            print(f"캐시 읽기 오류: {e}")
            return None
    
    def save_analysis_to_cache(self, title, artist, analysis, model_used):
        """분석 결과를 캐시에 저장"""
        try:
            cache_key = self._get_cache_key(title, artist)
            cache_file = self._get_cache_file_path(cache_key)
            
            cache_data = {
                'title': title,
                'artist': artist,
                'analysis': analysis,
                'model_used': model_used,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"캐시 저장 오류: {e}")
    
    def clear_cache(self):
        """캐시 전체 삭제"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            print("캐시가 모두 삭제되었습니다.")
        except Exception as e:
            print(f"캐시 삭제 오류: {e}")
    
    def get_cache_stats(self):
        """캐시 통계 정보"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
            total_files = len(cache_files)
            
            gpt4o_count = 0
            gpt35_count = 0
            
            for filename in cache_files:
                try:
                    with open(os.path.join(self.cache_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('model_used') == 'gpt-4o':
                            gpt4o_count += 1
                        else:
                            gpt35_count += 1
                except:
                    continue
            
            return {
                'total_cached': total_files,
                'gpt4o_cached': gpt4o_count,
                'gpt35_cached': gpt35_count
            }
        except:
            return {'total_cached': 0, 'gpt4o_cached': 0, 'gpt35_cached': 0}


# 전역 캐시 매니저 인스턴스
analysis_cache = AnalysisCache() 