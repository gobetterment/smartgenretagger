import os
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, 
                               QFileDialog, QApplication, QLabel, QMenu, QProgressDialog, QPushButton)
from PySide6.QtCore import QTimer, Qt
from concurrent.futures import ThreadPoolExecutor, as_completed

from ui_components import (EditableTreeWidget, ControlButtonsWidget, 
                          AudioControlWidget, InlineEditor)
from audio_manager import AudioFileProcessor, AudioPlayer
from music_genre_service import music_genre_service


class SmartGenreTaggerMainWindow(QMainWindow):
    """SmartGenreTagger 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartGenreTagger - AI 기반 MP3 장르 태그 편집기")
        self.setGeometry(100, 100, 1200, 600)
        
        # 데이터 저장
        self.file_list = []
        self.mp3_data = []
        
        # 페이징 상태
        self.current_page = 0
        self.page_size = 100
        
        # 장르 추천 중지 플래그
        self.genre_stop_requested = False
        
        # 오디오 플레이어
        self.audio_player = AudioPlayer()
        
        # UI 컴포넌트들
        self.tree = None
        self.control_buttons = None
        self.audio_control = None
        self.status_label = None
        
        # 페이징 컨트롤
        self.page_label = None
        self.prev_page_btn = None
        self.next_page_btn = None
        
        # 편집 관련
        self.inline_editor = None
        
        # UI 구성
        self.setup_ui()
        
        # 타이머 설정 (시크바 업데이트용)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_seekbar)
        self.timer.start(100)  # 100ms마다 업데이트
    
    def setup_ui(self):
        """UI 설정"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # 상단 컨트롤 버튼들
        self.control_buttons = ControlButtonsWidget()
        self.control_buttons.folder_select_requested.connect(self.select_folder)
        self.control_buttons.gpt_selected_requested.connect(self.get_selected_genre_suggestions)
        self.control_buttons.gpt_all_requested.connect(self.get_all_genre_suggestions)
        self.control_buttons.gpt_stop_requested.connect(self.stop_genre_recommendations)
        self.control_buttons.gpt_clear_requested.connect(self.clear_genre_recommendations)
        self.control_buttons.save_selected_requested.connect(self.save_selected_items)
        self.control_buttons.save_all_requested.connect(self.save_all_changes)
        main_layout.addWidget(self.control_buttons)
        
        # 트리 위젯
        self.tree = EditableTreeWidget()
        self.tree.year_edit_requested.connect(self.edit_year)
        self.tree.gpt_edit_requested.connect(self.edit_genre_suggestion)
        self.tree.copy_requested.connect(self.copy_to_clipboard)
        self.tree.context_menu_requested.connect(self.show_copy_context_menu)
        main_layout.addWidget(self.tree)
        
        # 페이징 컨트롤
        paging_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton("이전")
        self.prev_page_btn.clicked.connect(self.go_prev_page)
        self.next_page_btn = QPushButton("다음")
        self.next_page_btn.clicked.connect(self.go_next_page)
        self.page_label = QLabel("")
        paging_layout.addWidget(self.prev_page_btn)
        paging_layout.addWidget(self.page_label)
        paging_layout.addWidget(self.next_page_btn)
        main_layout.addLayout(paging_layout)
        
        # 인라인 편집기 설정
        self.inline_editor = InlineEditor(self.tree)
        
        # 오디오 컨트롤
        self.audio_control = AudioControlWidget()
        self.audio_control.play_pause_requested.connect(self.toggle_play_pause)
        self.audio_control.seek_position_changed.connect(self.on_seekbar_change)
        self.audio_control.seek_started.connect(self.on_seekbar_press)
        self.audio_control.seek_finished.connect(self.on_seekbar_release)
        self.audio_control.copy_filename_requested.connect(self.copy_current_filename)
        main_layout.addWidget(self.audio_control)
        
        # 상태바
        self.status_label = QLabel("총 0개의 MP3 파일")
        main_layout.addWidget(self.status_label)
        
        self.update_page_label()
        self.update_paging_buttons()
    
    def select_folder(self):
        """폴더 선택"""
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            # 상태 업데이트
            self.status_label.setText("📁 폴더 스캔 중...")
            QApplication.processEvents()
            
            self.file_list = AudioFileProcessor.get_mp3_files(folder)
            if self.file_list:
                self.load_all_files()
                # update_status는 load_all_files에서 처리됨
            else:
                QMessageBox.information(self, "알림", "선택한 폴더에 MP3 파일이 없습니다.")
                self.status_label.setText("총 0개의 MP3 파일")
    
    def load_all_files(self):
        """모든 파일 로드 (페이징 적용, None 체크)"""
        self.tree.clear()
        self.mp3_data.clear()
        total_files = len(self.file_list)
        if total_files == 0:
            return
        progress = QProgressDialog("MP3 파일을 로드하는 중...", "취소", 0, total_files, self)
        progress.setWindowTitle("파일 로딩")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setFixedSize(400, 120)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        try:
            for i, file_path in enumerate(self.file_list):
                if progress.wasCanceled():
                    print("파일 로딩이 사용자에 의해 취소되었습니다.")
                    break
                progress.setLabelText(f"MP3 파일을 로드하는 중... ({i+1}/{total_files})")
                progress.setValue(i)
                QApplication.processEvents()
                data = AudioFileProcessor.extract_metadata(file_path)
                if data is not None:
                    self.mp3_data.append(data)
            progress.setValue(total_files)
        except Exception as e:
            print(f"파일 로딩 중 오류 발생: {e}")
            QMessageBox.critical(self, "오류", f"파일 로딩 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            progress.close()
            loaded_count = len(self.mp3_data)
            if loaded_count > 0:
                self.show_page(0)
                self.status_label.setText(f"✅ {loaded_count}개 파일 로딩 완료")
                QTimer.singleShot(3000, self.update_status)
            else:
                self.status_label.setText("❌ 로딩된 파일이 없습니다.")
    
    def get_data_index_from_item(self, item):
        """트리 아이템에서 데이터 인덱스 가져오기"""
        return item.data(0, Qt.UserRole)
    
    def find_tree_item_by_data_index(self, data_index):
        """데이터 인덱스로 트리 아이템 찾기"""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if self.get_data_index_from_item(item) == data_index:
                return item
        return None
    
    def edit_year(self, index, item, column):
        """연도 편집"""
        # 정렬된 상태에서도 올바른 데이터 인덱스 사용
        data_index = self.get_data_index_from_item(item)
        if data_index is None:
            data_index = index  # 폴백
        
        # 현재 값 가져오기 (✓ 표시 제거)
        current_value = self.mp3_data[data_index]['year'].replace(" ✓", "") if self.mp3_data[data_index]['year'] else ""
        
        # 편집 시작
        edit_widget = self.inline_editor.start_edit(data_index, item, column, current_value)
        
        # 이벤트 연결
        edit_widget.returnPressed.connect(lambda: self.finish_year_edit(data_index, item))
        edit_widget.editingFinished.connect(lambda: self.finish_year_edit(data_index, item))
    
    def edit_genre_suggestion(self, index, item, column):
        """장르 추천 편집"""
        # 정렬된 상태에서도 올바른 데이터 인덱스 사용
        data_index = self.get_data_index_from_item(item)
        if data_index is None:
            data_index = index  # 폴백
        
        current_value = self.mp3_data[data_index]['genre_suggestion']
        
        # 편집 시작
        edit_widget = self.inline_editor.start_edit(data_index, item, column, current_value)
        
        # 이벤트 연결
        edit_widget.returnPressed.connect(lambda: self.finish_genre_edit(data_index, item))
        edit_widget.editingFinished.connect(lambda: self.finish_genre_edit(data_index, item))
    
    def finish_year_edit(self, data_index, item):
        """연도 편집 완료"""
        if not self.inline_editor.edit_widget:
            return
        
        try:
            new_value = self.inline_editor.get_edit_value()
            
            # 편집 위젯 정리
            self.inline_editor.finish_current_edit()
            
            # 데이터 업데이트
            data = self.mp3_data[data_index]
            print(f"Debug: 편집 완료 - 파일: {data['filename']}, 입력값: '{new_value}', 원본: '{data['original_year']}'")
            
            # 연도 변경 감지 및 표시 설정
            if new_value and new_value.isdigit():
                # 연도는 4자리 숫자만 허용
                if len(new_value) != 4:
                    QMessageBox.critical(self, "입력 오류", "연도는 4자리 숫자만 입력 가능합니다.\n예: 2023")
                    return
                
                # 원래 비어있던 경우 또는 값이 변경된 경우
                if not data['original_year'] or new_value != data['original_year']:
                    data['year_added'] = True
                    data['year'] = new_value + " ✓"  # 수정/추가된 연도에 체크 표시
                    print(f"Debug: 연도 수정/추가됨 - {data['year']}")
                else:
                    data['year_added'] = False
                    data['year'] = new_value
                    print(f"Debug: 연도 동일함 - {data['year']}")
            elif new_value and not new_value.isdigit():
                QMessageBox.critical(self, "입력 오류", "연도는 4자리 숫자만 입력 가능합니다.\n예: 2023")
                return
            else:
                data['year_added'] = False
                data['year'] = new_value
                print(f"Debug: 연도 비어있음 - {data['year']}")
            
            # 트리 아이템 업데이트
            item.setText(2, data['year'])
            
        except Exception as e:
            print(f"Error in finish_year_edit: {e}")
    
    def finish_genre_edit(self, data_index, item):
        """장르 추천 편집 완료 (strip 적용)"""
        if not self.inline_editor.edit_widget:
            return
        try:
            new_value = self.inline_editor.get_edit_value().strip()
            self.inline_editor.finish_current_edit()
            self.mp3_data[data_index]['genre_suggestion'] = new_value
            item.setText(4, new_value)
        except Exception as e:
            print(f"Error in finish_genre_edit: {e}")
    
    def get_all_genre_suggestions(self):
        """모든 파일에 대해 장르 추천 (3개 병렬, 캐시 활용, UI는 트리 순서대로, 중간 저장)"""
        if not self.mp3_data:
            QMessageBox.information(self, "알림", "먼저 MP3 파일을 로드해주세요.")
            return
        
        self.genre_stop_requested = False
        self.control_buttons.set_gpt_buttons_enabled(False)
        
        total_files = self.tree.topLevelItemCount()
        progress = QProgressDialog("장르 추천 중...", "취소", 0, total_files, self)
        progress.setWindowTitle("장르 추천 진행중")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setFixedSize(400, 120)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        QApplication.setOverrideCursor(Qt.ArrowCursor)
        
        result_list = [None] * total_files
        done_count = 0
        
        def recommend_worker(i, data_index, data):
            suggestion = music_genre_service.get_genre_recommendation(
                data['title'],
                data['artist'],
                year=data.get('year', None),
                original_genre=data['genre']
            )
            return (i, data_index, suggestion)
        
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for i in range(total_files):
                    item = self.tree.topLevelItem(i)
                    data_index = self.get_data_index_from_item(item)
                    if data_index is None:
                        continue
                    data = self.mp3_data[data_index]
                    futures.append(executor.submit(recommend_worker, i, data_index, data))
                for future in as_completed(futures):
                    if self.genre_stop_requested or progress.wasCanceled():
                        print("장르 추천이 사용자에 의해 중지되었습니다.")
                        self.genre_stop_requested = True
                        break
                    i, data_index, suggestion = future.result()
                    result_list[i] = (data_index, suggestion)
                    done_count += 1
                    if done_count % 100 == 0:
                        music_genre_service.save_cache()
                        print(f"[중간 저장] {done_count}곡 캐시 저장 완료")
                    progress.setLabelText(f"장르 추천 중... ({done_count}/{total_files})")
                    progress.setValue(done_count)
                    QApplication.processEvents()
            # UI는 항상 순서대로만 채움
            for i in range(total_files):
                if result_list[i] is not None:
                    data_index, suggestion = result_list[i]
                    def update_ui(idx=i, d_idx=data_index, sugg=suggestion):
                        item = self.tree.topLevelItem(idx)
                        if item and d_idx is not None:
                            self.mp3_data[d_idx]['genre_suggestion'] = sugg
                            item.setText(4, sugg)
                            print(f"장르 추천(순서대로) 반영: {self.mp3_data[d_idx]['filename']} -> {sugg}")
                    QTimer.singleShot(0, update_ui)
            progress.setValue(total_files)
        finally:
            music_genre_service.save_cache()
            progress.close()
            QApplication.restoreOverrideCursor()
            self.control_buttons.set_gpt_buttons_enabled(True)
            self.update_status()
            if self.genre_stop_requested:
                QMessageBox.information(self, "중지됨", f"장르 추천이 중지되었습니다.\n완료된 파일: {done_count}개")
            else:
                QMessageBox.information(self, "완료", f"총 {done_count}개 파일의 장르 추천이 완료되었습니다.")
    
    def get_selected_genre_suggestions(self):
        """선택된 파일들에 대해 장르 추천 (3개 병렬, 캐시 활용, UI는 트리 순서대로, 중간 저장)"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "알림", "추천받을 항목을 선택해주세요.")
            return
        
        self.genre_stop_requested = False
        self.control_buttons.set_gpt_buttons_enabled(False)
        
        total_selected = len(selected_items)
        progress = QProgressDialog("선택 항목 장르 추천 중...", "취소", 0, total_selected, self)
        progress.setWindowTitle("장르 추천 진행중")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setFixedSize(400, 120)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        QApplication.setOverrideCursor(Qt.ArrowCursor)
        
        result_list = [None] * total_selected
        done_count = 0
        
        def recommend_worker(i, data_index, data):
            suggestion = music_genre_service.get_genre_recommendation(
                data['title'],
                data['artist'],
                year=data.get('year', None),
                original_genre=data['genre']
            )
            return (i, data_index, suggestion)
        
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for i, item in enumerate(selected_items):
                    data_index = self.get_data_index_from_item(item)
                    if data_index is None:
                        continue
                    data = self.mp3_data[data_index]
                    futures.append(executor.submit(recommend_worker, i, data_index, data))
                for future in as_completed(futures):
                    if self.genre_stop_requested or progress.wasCanceled():
                        print("장르 추천이 사용자에 의해 중지되었습니다.")
                        self.genre_stop_requested = True
                        break
                    i, data_index, suggestion = future.result()
                    result_list[i] = (data_index, suggestion)
                    done_count += 1
                    if done_count % 100 == 0:
                        music_genre_service.save_cache()
                        print(f"[중간 저장] {done_count}곡 캐시 저장 완료")
                    progress.setLabelText(f"선택 항목 장르 추천 중... ({done_count}/{total_selected})")
                    progress.setValue(done_count)
                    QApplication.processEvents()
            # UI는 항상 순서대로만 채움
            for i in range(total_selected):
                if result_list[i] is not None:
                    data_index, suggestion = result_list[i]
                    def update_ui(idx=i, d_idx=data_index, sugg=suggestion):
                        item = selected_items[idx]
                        if item and d_idx is not None:
                            self.mp3_data[d_idx]['genre_suggestion'] = sugg
                            item.setText(4, sugg)
                            print(f"장르 추천(순서대로) 반영: {self.mp3_data[d_idx]['filename']} -> {sugg}")
                    QTimer.singleShot(0, update_ui)
            progress.setValue(total_selected)
        finally:
            music_genre_service.save_cache()
            progress.close()
            QApplication.restoreOverrideCursor()
            self.control_buttons.set_gpt_buttons_enabled(True)
            self.update_status()
            if self.genre_stop_requested:
                QMessageBox.information(self, "중지됨", f"선택 항목 장르 추천이 중지되었습니다.\n완료된 파일: {done_count}개")
            else:
                QMessageBox.information(self, "완료", f"선택된 {done_count}개 파일의 장르 추천이 완료되었습니다.")
    
    def save_all_changes(self):
        """모든 변경사항을 저장 (장르/연도 조건별 저장, 저장 후 연도 체크 제거, 추천장르 저장 시 컬럼 비움, strip 비교)"""
        saved_count = 0
        error_count = 0
        for i, data in enumerate(self.mp3_data):
            genre_suggestion = (data.get('genre_suggestion', '') or '').strip()
            genre = (data.get('genre', '') or '').strip()
            year = data.get('year', '')
            original_year = data.get('original_year', '')
            year_changed = (year.replace(" ✓", "") != (original_year or ""))
            if genre_suggestion and genre_suggestion != genre:
                if AudioFileProcessor.save_metadata(data):
                    saved_count += 1
                    data['genre'] = genre_suggestion
                    data['genre_suggestion'] = ""
                    clean_year = year.replace(" ✓", "")
                    data['year'] = clean_year
                    data['original_year'] = clean_year
                    item = self.find_tree_item_by_data_index(i)
                    if item:
                        item.setText(3, data['genre'])
                        item.setText(2, clean_year)
                        item.setText(4, "")
                else:
                    error_count += 1
            elif year_changed:
                if AudioFileProcessor.save_metadata(data):
                    saved_count += 1
                    clean_year = year.replace(" ✓", "")
                    data['year'] = clean_year
                    data['original_year'] = clean_year
                    item = self.find_tree_item_by_data_index(i)
                    if item:
                        item.setText(2, clean_year)
                else:
                    error_count += 1
        if saved_count > 0:
            message = f"총 {saved_count}개 파일이 저장되었습니다."
            if error_count > 0:
                message += f"\n{error_count}개 파일에서 오류가 발생했습니다."
            QMessageBox.information(self, "저장 완료", message)
        else:
            QMessageBox.information(self, "저장 완료", "저장할 변경사항이 없습니다.")
    
    def save_selected_items(self):
        """선택된 항목들 저장 (장르/연도 조건별 저장, 저장 후 연도 체크 제거, 추천장르 저장 시 컬럼 비움, strip 비교)"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "알림", "저장할 항목을 선택해주세요.")
            return
        saved_count = 0
        error_count = 0
        for item in selected_items:
            data_index = self.get_data_index_from_item(item)
            if data_index is not None:
                data = self.mp3_data[data_index]
                genre_suggestion = (data.get('genre_suggestion', '') or '').strip()
                genre = (data.get('genre', '') or '').strip()
                year = data.get('year', '')
                original_year = data.get('original_year', '')
                year_changed = (year.replace(" ✓", "") != (original_year or ""))
                if genre_suggestion and genre_suggestion != genre:
                    if AudioFileProcessor.save_metadata(data):
                        saved_count += 1
                        data['genre'] = genre_suggestion
                        data['genre_suggestion'] = ""
                        clean_year = year.replace(" ✓", "")
                        data['year'] = clean_year
                        data['original_year'] = clean_year
                        item.setText(3, data['genre'])
                        item.setText(2, clean_year)
                        item.setText(4, "")
                    else:
                        error_count += 1
                elif year_changed:
                    if AudioFileProcessor.save_metadata(data):
                        saved_count += 1
                        clean_year = year.replace(" ✓", "")
                        data['year'] = clean_year
                        data['original_year'] = clean_year
                        item.setText(2, clean_year)
                    else:
                        error_count += 1
        if saved_count > 0:
            message = f"선택된 {saved_count}개 파일이 저장되었습니다."
            if error_count > 0:
                message += f"\n{error_count}개 파일에서 오류가 발생했습니다."
            QMessageBox.information(self, "저장 완료", message)
        else:
            QMessageBox.information(self, "저장 완료", "선택된 항목에 저장할 변경사항이 없습니다.")
    
    def get_selected_item_path(self):
        """현재 선택된 항목의 파일 경로 반환"""
        current_item = self.tree.currentItem()
        if current_item:
            # 정렬된 상태에서도 올바른 데이터 인덱스 사용
            data_index = self.get_data_index_from_item(current_item)
            if data_index is not None:
                return self.mp3_data[data_index]['path']
        return None
    
    def toggle_play_pause(self):
        """재생/일시정지 토글"""
        selected_path = self.get_selected_item_path()
        
        if not selected_path:
            QMessageBox.information(self, "알림", "재생할 파일을 선택해주세요.")
            return
        
        try:
            if self.audio_player.is_playing and self.audio_player.current_file == selected_path:
                # 현재 재생 중인 파일을 일시정지
                self.audio_player.pause()
                self.audio_control.update_play_button(False)
            else:
                # 새 파일 재생 또는 재개
                if self.audio_player.current_file != selected_path:
                    # 새 파일 재생
                    if self.audio_player.play(selected_path):
                        filename = os.path.basename(selected_path)
                        self.audio_control.update_current_file(filename)
                        
                        # 시크바 설정
                        if self.audio_player.song_length > 0:
                            self.audio_control.update_seekbar(0, self.audio_player.song_length)
                            total_time = AudioPlayer.format_time(self.audio_player.song_length)
                            self.audio_control.update_time_display("00:00", total_time)
                else:
                    # 일시정지된 파일 재개
                    self.audio_player.resume()
                
                self.audio_control.update_play_button(True)
                
        except Exception as e:
            QMessageBox.critical(self, "재생 오류", f"파일 재생 중 오류가 발생했습니다:\n{str(e)}")
            print(f"재생 오류: {e}")
    
    def on_seekbar_change(self, value):
        """시크바 값 변경 시 호출"""
        if self.audio_player.seeking and self.audio_player.song_length > 0:
            self.audio_player.current_pos = value
    
    def on_seekbar_press(self):
        """시크바 클릭 시작"""
        self.audio_player.seeking = True
    
    def on_seekbar_release(self):
        """시크바 클릭 종료"""
        if self.audio_player.seeking and self.audio_player.current_file:
            self.audio_player.set_position(self.audio_player.current_pos)
        self.audio_player.seeking = False
    
    def update_seekbar(self):
        """시크바 업데이트 (타이머에서 호출)"""
        if (self.audio_player.is_playing and 
            not self.audio_player.seeking and 
            self.audio_player.song_length > 0):
            
            self.audio_control.update_seekbar(int(self.audio_player.current_pos))
            current_time = AudioPlayer.format_time(self.audio_player.current_pos)
            total_time = AudioPlayer.format_time(self.audio_player.song_length)
            self.audio_control.update_time_display(current_time, total_time)
    
    def copy_to_clipboard(self, text, field_name):
        """텍스트를 클립보드에 복사"""
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            # 상태표시줄에 복사 완료 메시지 표시
            self.status_label.setText(f"📋 {field_name} 복사됨: {text}")
            print(f"{field_name} 복사됨: {text}")
            
            # 3초 후 원래 상태로 복원
            QTimer.singleShot(3000, self.update_status)
        else:
            self.status_label.setText(f"❌ {field_name} 정보가 없습니다.")
            print(f"{field_name} 정보가 없습니다.")
            # 3초 후 원래 상태로 복원
            QTimer.singleShot(3000, self.update_status)
    
    def show_copy_context_menu(self, item, column, position):
        """복사 컨텍스트 메뉴 표시"""
        text = item.text(column)
        if not text:
            return
        
        # 컬럼별 필드명 매핑
        field_names = {
            0: "제목",
            1: "아티스트", 
            3: "장르"
        }
        
        field_name = field_names.get(column, "정보")
        
        # 컨텍스트 메뉴 생성
        menu = QMenu(self)
        copy_action = menu.addAction(f"📋 {field_name} 복사")
        copy_action.triggered.connect(lambda: self.copy_to_clipboard(text, field_name))
        
        # 메뉴 표시
        menu.exec_(position)
    
    def stop_genre_recommendations(self):
        """장르 추천 중지"""
        self.genre_stop_requested = True
        print("장르 추천 중지 요청됨")
    
    def clear_genre_recommendations(self):
        """장르 추천 정보 초기화"""
        if not self.mp3_data:
            QMessageBox.information(self, "알림", "로드된 파일이 없습니다.")
            return
        
        # 확인 대화상자
        reply = QMessageBox.question(self, "확인", 
                                   "모든 장르 추천 정보를 초기화하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 데이터에서 장르 추천 정보 제거
            cleared_count = 0
            for data in self.mp3_data:
                if data.get('genre_suggestion', ''):
                    data['genre_suggestion'] = ""
                    cleared_count += 1
            
            # 트리에서 장르 추천 컬럼 초기화
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                item.setText(4, "")  # 장르 추천 컬럼 비우기
            
            QMessageBox.information(self, "완료", f"{cleared_count}개의 장르 추천 정보가 초기화되었습니다.")
            print(f"장르 추천 정보 초기화 완료: {cleared_count}개")
    
    def update_status(self):
        """상태바 업데이트"""
        file_count = len(self.mp3_data)
        self.status_label.setText(f"총 {file_count}개의 MP3 파일")
        self.update_page_label()
        self.update_paging_buttons()
    
    def show_page(self, page_num):
        self.tree.clear()
        start = page_num * self.page_size
        end = min(start + self.page_size, len(self.mp3_data))
        for i in range(start, end):
            data = self.mp3_data[i]
            if data is None:
                continue
            self.tree.add_mp3_item(data['title'], data['artist'], data['year'], data['genre'], i)
        self.current_page = page_num
        self.update_page_label()
        self.update_paging_buttons()

    def update_page_label(self):
        total_pages = max(1, (len(self.mp3_data) + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"페이지 {self.current_page + 1} / {total_pages}")

    def update_paging_buttons(self):
        total_pages = max(1, (len(self.mp3_data) + self.page_size - 1) // self.page_size)
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < total_pages - 1)

    def go_prev_page(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def go_next_page(self):
        total_pages = max(1, (len(self.mp3_data) + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages - 1:
            self.show_page(self.current_page + 1)

    def copy_current_filename(self):
        """현재 재생 중인 파일명을 .mp3 확장자 전까지만 클립보드에 복사"""
        filename = os.path.basename(self.audio_player.current_file) if self.audio_player.current_file else ""
        if filename:
            # .mp3 확장자 전까지만 추출
            if filename.lower().endswith('.mp3'):
                filename_no_ext = filename[:-4]
            else:
                filename_no_ext = filename
            clipboard = QApplication.clipboard()
            clipboard.setText(filename_no_ext)
            self.status_label.setText(f"📋 파일명 복사됨: {filename_no_ext}")
            QTimer.singleShot(3000, self.update_status)
        else:
            self.status_label.setText("❌ 재생 중인 파일이 없습니다.")
            QTimer.singleShot(3000, self.update_status)

 