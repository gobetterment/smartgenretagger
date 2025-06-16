import os
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, 
                               QFileDialog, QApplication, QLabel, QMenu, QProgressDialog,
                               QSplitter, QTextEdit, QPushButton)
from PySide6.QtCore import QTimer, Qt, QThread, Signal

from ui_components import (EditableTreeWidget, ControlButtonsWidget, 
                          AudioControlWidget, InlineEditor)
from audio_manager import AudioFileProcessor, AudioPlayer
from gpt_service import gpt_service


class DetailedAnalysisThread(QThread):
    """상세 분석을 위한 스레드"""
    analysis_completed = Signal(str)
    analysis_error = Signal(str)
    
    def __init__(self, title, artist, year=None):
        super().__init__()
        self.title = title
        self.artist = artist
        self.year = year
    
    def run(self):
        try:
            result = gpt_service.get_detailed_genre_analysis(self.title, self.artist, self.year)
            self.analysis_completed.emit(result)
        except Exception as e:
            self.analysis_error.emit(str(e))


class SmartGenreTaggerMainWindow(QMainWindow):
    """SmartGenreTagger 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartGenreTagger - AI 기반 MP3 장르 태그 편집기")
        self.setGeometry(100, 100, 1400, 700)
        
        # 데이터 저장
        self.file_list = []
        self.mp3_data = []
        
        # GPT 추천 중지 플래그
        self.gpt_stop_requested = False
        
        # 오디오 플레이어
        self.audio_player = AudioPlayer()
        
        # UI 컴포넌트들
        self.tree = None
        self.control_buttons = None
        self.audio_control = None
        self.status_label = None
        
        # 편집 관련
        self.inline_editor = None
        
        # 상세 정보 패널
        self.detail_panel = None
        self.detail_text = None
        self.analyze_button = None
        self.current_analysis_thread = None
        self.current_selected_data = None
        
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
        self.control_buttons.gpt_selected_requested.connect(self.get_selected_gpt_suggestions)
        self.control_buttons.gpt_all_requested.connect(self.get_all_gpt_suggestions)
        self.control_buttons.gpt_stop_requested.connect(self.stop_gpt_recommendations)
        self.control_buttons.gpt_clear_requested.connect(self.clear_gpt_recommendations)
        self.control_buttons.save_selected_requested.connect(self.save_selected_items)
        self.control_buttons.save_all_requested.connect(self.save_all_changes)
        main_layout.addWidget(self.control_buttons)
        
        # 메인 컨텐츠 영역 (스플리터 사용)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 왼쪽: 트리 위젯
        self.tree = EditableTreeWidget()
        self.tree.year_edit_requested.connect(self.edit_year)
        self.tree.gpt_edit_requested.connect(self.edit_gpt_suggestion)
        self.tree.copy_requested.connect(self.copy_to_clipboard)
        self.tree.context_menu_requested.connect(self.show_copy_context_menu)
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        main_splitter.addWidget(self.tree)
        
        # 오른쪽: 상세 정보 패널
        self.setup_detail_panel()
        main_splitter.addWidget(self.detail_panel)
        
        # 스플리터 비율 설정 (왼쪽 65%, 오른쪽 35%)
        main_splitter.setSizes([910, 490])
        main_layout.addWidget(main_splitter)
        
        # 인라인 편집기 설정
        self.inline_editor = InlineEditor(self.tree)
        
        # 오디오 컨트롤
        self.audio_control = AudioControlWidget()
        self.audio_control.play_pause_requested.connect(self.toggle_play_pause)
        self.audio_control.seek_position_changed.connect(self.on_seekbar_change)
        self.audio_control.seek_started.connect(self.on_seekbar_press)
        self.audio_control.seek_finished.connect(self.on_seekbar_release)
        main_layout.addWidget(self.audio_control)
        
        # 상태바
        self.status_label = QLabel("총 0개의 MP3 파일")
        main_layout.addWidget(self.status_label)
    
    def setup_detail_panel(self):
        """상세 정보 패널 설정"""
        self.detail_panel = QWidget()
        detail_layout = QVBoxLayout(self.detail_panel)
        
        # 제목
        title_label = QLabel("🎵 곡 상세 정보")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        detail_layout.addWidget(title_label)
        
        # 분석 버튼
        self.analyze_button = QPushButton("🔍 스마트 분석")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self.analyze_selected_song)
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        detail_layout.addWidget(self.analyze_button)
        
        # 상세 정보 텍스트
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("곡을 선택하고 '🔍 스마트 분석' 버튼을 클릭하세요.")
        self.detail_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                font-family: 'SF Pro Display', 'Segoe UI', 'Malgun Gothic', sans-serif;
                font-size: 13px;
                line-height: 1.6;
                background-color: #fafafa;
                color: #333;
            }
            QTextEdit:focus {
                border: 2px solid #007acc;
                background-color: #ffffff;
            }
        """)
        detail_layout.addWidget(self.detail_text)
    
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
        """모든 파일 로드"""
        # 기존 데이터 클리어
        self.tree.clear()
        self.mp3_data.clear()
        
        total_files = len(self.file_list)
        if total_files == 0:
            return
        
        # 진행 상황 다이얼로그 생성
        progress = QProgressDialog("MP3 파일을 로드하는 중...", "취소", 0, total_files, self)
        progress.setWindowTitle("파일 로딩")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)  # 즉시 표시
        progress.setValue(0)
        
        # 팝업창 크기 고정
        progress.setFixedSize(400, 120)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        
        try:
            for i, file_path in enumerate(self.file_list):
                # 취소 버튼 확인
                if progress.wasCanceled():
                    print("파일 로딩이 사용자에 의해 취소되었습니다.")
                    break
                
                # 진행 상황 업데이트
                progress.setLabelText(f"MP3 파일을 로드하는 중... ({i+1}/{total_files})")
                progress.setValue(i)
                
                # UI 업데이트
                QApplication.processEvents()
                
                # 메타데이터 추출
                data = AudioFileProcessor.extract_metadata(file_path)
                self.mp3_data.append(data)
                
                # 트리에 아이템 추가 (데이터 인덱스 포함)
                self.tree.add_mp3_item(data['title'], data['artist'], 
                                      data['year'], data['genre'], i)
            
            # 완료
            progress.setValue(total_files)
            
        except Exception as e:
            print(f"파일 로딩 중 오류 발생: {e}")
            QMessageBox.critical(self, "오류", f"파일 로딩 중 오류가 발생했습니다:\n{str(e)}")
        
        finally:
            progress.close()
            
            # 로딩 완료 후 상태 업데이트
            loaded_count = len(self.mp3_data)
            if loaded_count > 0:
                self.status_label.setText(f"✅ {loaded_count}개 파일 로딩 완료")
                # 3초 후 원래 상태로 복원
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
    
    def edit_gpt_suggestion(self, index, item, column):
        """GPT 추천 편집"""
        # 정렬된 상태에서도 올바른 데이터 인덱스 사용
        data_index = self.get_data_index_from_item(item)
        if data_index is None:
            data_index = index  # 폴백
        
        current_value = self.mp3_data[data_index]['gpt_suggestion']
        
        # 편집 시작
        edit_widget = self.inline_editor.start_edit(data_index, item, column, current_value)
        
        # 이벤트 연결
        edit_widget.returnPressed.connect(lambda: self.finish_gpt_edit(data_index, item))
        edit_widget.editingFinished.connect(lambda: self.finish_gpt_edit(data_index, item))
    
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
    
    def finish_gpt_edit(self, data_index, item):
        """GPT 추천 편집 완료"""
        if not self.inline_editor.edit_widget:
            return
        
        try:
            new_value = self.inline_editor.get_edit_value()
            
            # 편집 위젯 정리
            self.inline_editor.finish_current_edit()
            
            # 데이터 업데이트
            self.mp3_data[data_index]['gpt_suggestion'] = new_value
            
            # 트리 아이템 업데이트
            item.setText(4, new_value)
            
        except Exception as e:
            print(f"Error in finish_gpt_edit: {e}")
    
    def get_all_gpt_suggestions(self):
        """모든 파일에 대해 GPT 장르 추천"""
        if not self.mp3_data:
            QMessageBox.information(self, "알림", "먼저 MP3 파일을 로드해주세요.")
            return
        
        # 중지 플래그 초기화 및 버튼 상태 변경
        self.gpt_stop_requested = False
        self.control_buttons.set_gpt_buttons_enabled(False)
        
        total_files = len(self.mp3_data)
        completed_count = 0
        
        try:
            for i, data in enumerate(self.mp3_data):
                # 중지 요청 확인
                if self.gpt_stop_requested:
                    print("GPT 추천이 사용자에 의해 중지되었습니다.")
                    break
                
                try:
                    # 상태 업데이트
                    self.status_label.setText(f"GPT 추천 진행 중... ({i+1}/{total_files})")
                    
                    # GPT 추천 받기
                    suggestion = gpt_service.get_genre_recommendation(data['title'], data['artist'])
                    data['gpt_suggestion'] = suggestion
                    
                    # 정렬된 상태에서 올바른 트리 아이템 찾기
                    item = self.find_tree_item_by_data_index(i)
                    if item:
                        item.setText(4, suggestion)
                    
                    completed_count += 1
                    
                    # UI 업데이트
                    QApplication.processEvents()
                    
                    print(f"GPT 추천 완료 ({i+1}/{total_files}): {data['filename']} -> {suggestion}")
                    
                except Exception as e:
                    print(f"GPT 추천 오류 {data['filename']}: {e}")
        
        finally:
            # 버튼 상태 복원 및 상태 업데이트
            self.control_buttons.set_gpt_buttons_enabled(True)
            self.update_status()
            
            if self.gpt_stop_requested:
                QMessageBox.information(self, "중지됨", f"GPT 추천이 중지되었습니다.\n완료된 파일: {completed_count}개")
            else:
                QMessageBox.information(self, "완료", f"총 {completed_count}개 파일의 장르 추천이 완료되었습니다.")
    
    def get_selected_gpt_suggestions(self):
        """선택된 파일들에 대해 GPT 장르 추천"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "알림", "추천받을 항목을 선택해주세요.")
            return
        
        # 중지 플래그 초기화 및 버튼 상태 변경
        self.gpt_stop_requested = False
        self.control_buttons.set_gpt_buttons_enabled(False)
        
        total_selected = len(selected_items)
        completed_count = 0
        
        try:
            for i, item in enumerate(selected_items):
                # 중지 요청 확인
                if self.gpt_stop_requested:
                    print("GPT 추천이 사용자에 의해 중지되었습니다.")
                    break
                
                # 정렬된 상태에서도 올바른 데이터 인덱스 사용
                data_index = self.get_data_index_from_item(item)
                if data_index is not None:
                    data = self.mp3_data[data_index]
                    
                    try:
                        # 상태 업데이트
                        self.status_label.setText(f"선택 항목 GPT 추천 진행 중... ({i+1}/{total_selected})")
                        
                        # GPT 추천 받기
                        suggestion = gpt_service.get_genre_recommendation(data['title'], data['artist'])
                        data['gpt_suggestion'] = suggestion
                        
                        # 트리 아이템 업데이트
                        item.setText(4, suggestion)
                        
                        completed_count += 1
                        
                        # UI 업데이트
                        QApplication.processEvents()
                        
                        print(f"GPT 추천 완료 ({i+1}/{total_selected}): {data['filename']} -> {suggestion}")
                        
                    except Exception as e:
                        print(f"GPT 추천 오류 {data['filename']}: {e}")
        
        finally:
            # 버튼 상태 복원 및 상태 업데이트
            self.control_buttons.set_gpt_buttons_enabled(True)
            self.update_status()
            
            if self.gpt_stop_requested:
                QMessageBox.information(self, "중지됨", f"선택 항목 GPT 추천이 중지되었습니다.\n완료된 파일: {completed_count}개")
            else:
                QMessageBox.information(self, "완료", f"선택된 {completed_count}개 파일의 장르 추천이 완료되었습니다.")
    
    def save_all_changes(self):
        """모든 변경사항을 저장"""
        saved_count = 0
        error_count = 0
        
        for i, data in enumerate(self.mp3_data):
            # GPT 추천이 있거나 연도가 변경된 경우만 저장
            has_gpt_suggestion = bool(data['gpt_suggestion'])
            year_changed = data.get('year_added', False) or (data['year'].replace(" ✓", "") != data['original_year'])
            
            if has_gpt_suggestion or year_changed:
                if AudioFileProcessor.save_metadata(data):
                    saved_count += 1
                    # 정렬된 상태에서 올바른 트리 아이템 찾기
                    item = self.find_tree_item_by_data_index(i)
                    if item:
                        item.setText(3, data['genre'])  # 장르 컬럼 업데이트
                else:
                    error_count += 1
        
        # 결과 메시지
        if saved_count > 0:
            message = f"총 {saved_count}개 파일이 저장되었습니다."
            if error_count > 0:
                message += f"\n{error_count}개 파일에서 오류가 발생했습니다."
            QMessageBox.information(self, "저장 완료", message)
        else:
            QMessageBox.information(self, "저장 완료", "저장할 변경사항이 없습니다.")
    
    def save_selected_items(self):
        """선택된 항목들 저장"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "알림", "저장할 항목을 선택해주세요.")
            return
        
        saved_count = 0
        error_count = 0
        
        for item in selected_items:
            # 정렬된 상태에서도 올바른 데이터 인덱스 사용
            data_index = self.get_data_index_from_item(item)
            if data_index is not None:
                data = self.mp3_data[data_index]
                
                # GPT 추천이 있거나 연도가 변경된 경우만 저장
                has_gpt_suggestion = bool(data['gpt_suggestion'])
                year_changed = data.get('year_added', False) or (data['year'].replace(" ✓", "") != data['original_year'])
                
                if has_gpt_suggestion or year_changed:
                    if AudioFileProcessor.save_metadata(data):
                        saved_count += 1
                        # 트리 아이템 업데이트
                        item.setText(3, data['genre'])  # 장르 컬럼 업데이트
                    else:
                        error_count += 1
        
        # 결과 메시지
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
    
    def stop_gpt_recommendations(self):
        """GPT 추천 중지"""
        self.gpt_stop_requested = True
        print("GPT 추천 중지 요청됨")
    
    def clear_gpt_recommendations(self):
        """GPT 추천 정보 초기화"""
        if not self.mp3_data:
            QMessageBox.information(self, "알림", "로드된 파일이 없습니다.")
            return
        
        # 확인 대화상자
        reply = QMessageBox.question(self, "확인", 
                                   "모든 GPT 추천 정보를 초기화하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 데이터에서 GPT 추천 정보 제거
            cleared_count = 0
            for data in self.mp3_data:
                if data['gpt_suggestion']:
                    data['gpt_suggestion'] = ""
                    cleared_count += 1
            
            # 트리에서 GPT 추천 컬럼 초기화
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                item.setText(4, "")  # GPT 추천 컬럼 비우기
            
            QMessageBox.information(self, "완료", f"{cleared_count}개의 GPT 추천 정보가 초기화되었습니다.")
            print(f"GPT 추천 정보 초기화 완료: {cleared_count}개")
    
    def update_status(self):
        """상태바 업데이트"""
        file_count = len(self.mp3_data)
        self.status_label.setText(f"총 {file_count}개의 MP3 파일")
    
    def on_selection_changed(self):
        """선택 항목 변경 시 호출"""
        selected_items = self.tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            data_index = self.get_data_index_from_item(item)
            if data_index is not None and data_index < len(self.mp3_data):
                # 분석 버튼 활성화
                self.analyze_button.setEnabled(True)
                
                # 현재 선택된 데이터 저장
                self.current_selected_data = self.mp3_data[data_index]
                
                # 기본 정보 표시
                data = self.mp3_data[data_index]
                basic_info = f"""선택된 곡: {data['title']}
아티스트: {data['artist']}
연도: {data['year'] if data['year'] else '정보 없음'}
현재 장르: {data['genre'] if data['genre'] else '정보 없음'}

"""
                self.detail_text.setText(basic_info)
        else:
            # 선택 해제 시
            self.analyze_button.setEnabled(False)
            self.current_selected_data = None
            self.detail_text.clear()
            self.detail_text.setPlaceholderText("곡을 선택하고 '🔍 스마트 분석' 버튼을 클릭하세요.")
    
    def analyze_selected_song(self):
        """선택된 곡 상세 분석"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        data_index = self.get_data_index_from_item(item)
        if data_index is None or data_index >= len(self.mp3_data):
            return
        
        data = self.mp3_data[data_index]
        title = data['title']
        artist = data['artist']
        year_str = data.get('year', '').replace(' ✓', '').strip()
        year = None
        
        # 연도 정보 파싱
        if year_str and year_str.isdigit():
            year = int(year_str)
        
        if not title or not artist:
            QMessageBox.warning(self, "경고", "제목과 아티스트 정보가 필요합니다.")
            return
        
        # 분석 중 상태로 변경
        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("🔄 분석 중...")
        
        # 분석 방식 미리보기 (항상 Google Search + GPT-3.5 사용)
        self.detail_text.setText("🤖 분석 중...\n잠시만 기다려주세요.")
        
        # 분석 스레드 시작
        self.current_analysis_thread = DetailedAnalysisThread(title, artist, year)
        self.current_analysis_thread.analysis_completed.connect(self.on_analysis_completed)
        self.current_analysis_thread.analysis_error.connect(self.on_analysis_error)
        self.current_analysis_thread.start()
    
    def on_analysis_completed(self, result):
        """분석 완료 시 호출"""
        self.detail_text.setText(result)
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("🔍 스마트 분석")
        
        # 스레드 정리
        if self.current_analysis_thread:
            self.current_analysis_thread.deleteLater()
            self.current_analysis_thread = None
    
    def on_analysis_error(self, error_msg):
        """분석 오류 시 호출"""
        self.detail_text.setText(f"분석 중 오류가 발생했습니다:\n{error_msg}")
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("🔍 스마트 분석")
        
        # 스레드 정리
        if self.current_analysis_thread:
            self.current_analysis_thread.deleteLater()
            self.current_analysis_thread = None
    
 