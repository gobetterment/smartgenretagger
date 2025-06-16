import platform
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget, QPushButton, 
                               QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView, 
                               QSlider, QLineEdit, QMenu, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction


class SortableTreeWidgetItem(QTreeWidgetItem):
    """정렬 가능한 트리 위젯 아이템 (연도 컬럼 숫자 정렬 지원)"""
    
    def __lt__(self, other):
        """정렬 비교 연산자"""
        column = self.treeWidget().sortColumn()
        
        # 연도 컬럼(2번)의 경우 숫자로 정렬
        if column == 2:
            try:
                # ✓ 표시 제거 후 숫자로 변환
                self_year = self.text(column).replace(" ✓", "").strip()
                other_year = other.text(column).replace(" ✓", "").strip()
                
                # 빈 값은 가장 뒤로
                if not self_year and not other_year:
                    return False
                elif not self_year:
                    return False  # 빈 값은 뒤로
                elif not other_year:
                    return True   # 빈 값은 뒤로
                
                # 숫자로 비교
                return int(self_year) < int(other_year)
            except (ValueError, TypeError):
                # 숫자가 아닌 경우 문자열로 비교
                return self.text(column) < other.text(column)
        
        # 다른 컬럼은 기본 문자열 정렬
        return self.text(column) < other.text(column)

class EditableTreeWidget(QTreeWidget):
    """편집 가능한 트리 위젯"""
    
    # 시그널 정의
    year_edit_requested = Signal(int, QTreeWidgetItem, int)
    gpt_edit_requested = Signal(int, QTreeWidgetItem, int)
    copy_requested = Signal(str, str)  # (텍스트, 필드명)
    context_menu_requested = Signal(QTreeWidgetItem, int, object)  # (아이템, 컬럼, 위치)
    
    def __init__(self):
        super().__init__()
        self.setup_tree()
    
    def setup_tree(self):
        """트리 위젯 설정"""
        self.setHeaderLabels(["Title", "Artist", "Year", "Genre", "Suggested Genre / Edit"])
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setRootIsDecorated(False)
        
        # 정렬 기능 활성화
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)  # 기본적으로 Title 컬럼으로 오름차순 정렬
        
        # 컬럼 너비 설정
        header = self.header()
        header.resizeSection(0, 250)  # Title
        header.resizeSection(1, 180)  # Artist
        header.resizeSection(2, 70)   # Year
        header.resizeSection(3, 250)  # Genre
        header.resizeSection(4, 320)  # Suggested Genre
        
        # 헤더 클릭 가능하게 설정
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        
        # 이벤트 연결
        self.itemDoubleClicked.connect(self._on_double_click)
        
        # 우클릭 컨텍스트 메뉴 설정
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
    
    def _on_double_click(self, item, column):
        """더블클릭 이벤트 처리"""
        index = self.indexOfTopLevelItem(item)
        if index >= 0:
            if column == 0:  # Title 컬럼
                text = item.text(column)
                if text:
                    self.copy_requested.emit(text, "제목")
            elif column == 1:  # Artist 컬럼
                text = item.text(column)
                if text:
                    self.copy_requested.emit(text, "아티스트")
            elif column == 2:  # Year 컬럼
                self.year_edit_requested.emit(index, item, column)
            elif column == 3:  # Genre 컬럼
                text = item.text(column)
                if text:
                    self.copy_requested.emit(text, "장르")
            elif column == 4:  # GPT 추천 컬럼
                self.gpt_edit_requested.emit(index, item, column)
    
    def _on_context_menu(self, position):
        """우클릭 컨텍스트 메뉴 이벤트 처리"""
        item = self.itemAt(position)
        if item:
            # 클릭된 컬럼 찾기
            column = self.columnAt(position.x())
            # 복사 가능한 컬럼(Title, Artist, Genre)인 경우만 메뉴 표시
            if column in [0, 1, 3]:
                self.context_menu_requested.emit(item, column, self.mapToGlobal(position))
    
    def add_mp3_item(self, title, artist, year, genre, data_index=None):
        """MP3 아이템을 트리에 추가"""
        item = SortableTreeWidgetItem([title, artist, year, genre, ""])
        if data_index is not None:
            item.setData(0, Qt.UserRole, data_index)  # 데이터 인덱스 저장
        self.addTopLevelItem(item)
        return item


class ControlButtonsWidget(QWidget):
    """상단 컨트롤 버튼들"""
    
    # 시그널 정의
    folder_select_requested = Signal()
    gpt_selected_requested = Signal()
    gpt_all_requested = Signal()
    gpt_stop_requested = Signal()
    gpt_clear_requested = Signal()
    save_selected_requested = Signal()
    save_all_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QHBoxLayout(self)
        
        # 폴더 선택 버튼
        self.btn_select_folder = QPushButton("📁 폴더 선택")
        self.btn_select_folder.clicked.connect(self.folder_select_requested.emit)
        layout.addWidget(self.btn_select_folder)
        
        # AI 추천 관련 버튼들
        self.btn_gpt_selected = QPushButton("🤖 선택 추천")
        self.btn_gpt_selected.clicked.connect(self.gpt_selected_requested.emit)
        layout.addWidget(self.btn_gpt_selected)
        
        self.btn_gpt_all = QPushButton("🤖 전체 추천")
        self.btn_gpt_all.clicked.connect(self.gpt_all_requested.emit)
        layout.addWidget(self.btn_gpt_all)
        
        self.btn_gpt_stop = QPushButton("⏹️ 추천 중지")
        self.btn_gpt_stop.clicked.connect(self.gpt_stop_requested.emit)
        self.btn_gpt_stop.setEnabled(False)  # 기본적으로 비활성화
        layout.addWidget(self.btn_gpt_stop)
        
        self.btn_gpt_clear = QPushButton("🗑️ 추천 초기화")
        self.btn_gpt_clear.clicked.connect(self.gpt_clear_requested.emit)
        layout.addWidget(self.btn_gpt_clear)
        
        # 저장 관련 버튼들
        self.btn_save_selected = QPushButton("💾 선택 저장")
        self.btn_save_selected.clicked.connect(self.save_selected_requested.emit)
        layout.addWidget(self.btn_save_selected)
        
        self.btn_save_all = QPushButton("💾 전체 저장")
        self.btn_save_all.clicked.connect(self.save_all_requested.emit)
        layout.addWidget(self.btn_save_all)
        
        layout.addStretch()
    
    def set_gpt_buttons_enabled(self, enabled):
        """GPT 추천 버튼들 활성화/비활성화"""
        self.btn_gpt_selected.setEnabled(enabled)
        self.btn_gpt_all.setEnabled(enabled)
        self.btn_gpt_stop.setEnabled(not enabled)  # 중지 버튼은 반대로


class AudioControlWidget(QWidget):
    """오디오 컨트롤 위젯"""
    
    # 시그널 정의
    play_pause_requested = Signal()
    seek_position_changed = Signal(int)
    seek_started = Signal()
    seek_finished = Signal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        
        # 현재 재생 중인 파일 정보 라벨
        self.current_file_label = QLabel("재생 중인 파일 없음")
        layout.addWidget(self.current_file_label)
        
        # 시간 정보와 시크바를 담을 프레임
        time_frame = QWidget()
        time_layout = QHBoxLayout(time_frame)
        
        # 재생/일시정지 버튼
        self.btn_play_pause = QPushButton("▶️")
        self.btn_play_pause.setFixedWidth(40)
        self.btn_play_pause.clicked.connect(self.play_pause_requested.emit)
        time_layout.addWidget(self.btn_play_pause)
        
        # 현재 시간 라벨
        self.current_time_label = QLabel("00:00")
        time_layout.addWidget(self.current_time_label)
        
        # 시크바
        self.seekbar = QSlider(Qt.Horizontal)
        self.seekbar.setRange(0, 100)
        self.seekbar.valueChanged.connect(self.seek_position_changed.emit)
        self.seekbar.sliderPressed.connect(self.seek_started.emit)
        self.seekbar.sliderReleased.connect(self.seek_finished.emit)
        time_layout.addWidget(self.seekbar)
        
        # 총 시간 라벨
        self.total_time_label = QLabel("00:00")
        time_layout.addWidget(self.total_time_label)
        
        layout.addWidget(time_frame)
    
    def update_current_file(self, filename):
        """현재 파일 정보 업데이트"""
        self.current_file_label.setText(f"재생 중: {filename}")
    
    def update_play_button(self, is_playing):
        """재생 버튼 상태 업데이트"""
        self.btn_play_pause.setText("⏸️" if is_playing else "▶️")
    
    def update_time_display(self, current_time, total_time):
        """시간 표시 업데이트"""
        self.current_time_label.setText(current_time)
        self.total_time_label.setText(total_time)
    
    def update_seekbar(self, position, maximum=None):
        """시크바 업데이트"""
        if maximum is not None:
            self.seekbar.setRange(0, int(maximum))
        self.seekbar.setValue(int(position))


class EditContextMenu(QMenu):
    """편집용 컨텍스트 메뉴"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_mac = platform.system() == 'Darwin'
        self.setup_menu()
    
    def setup_menu(self):
        """메뉴 설정"""
        # 운영체제별 단축키 표시
        if self.is_mac:
            copy_action = self.addAction("복사 (⌘C)")
            paste_action = self.addAction("붙여넣기 (⌘V)")
            self.addSeparator()
            select_all_action = self.addAction("전체 선택 (⌘A)")
        else:
            copy_action = self.addAction("복사 (Ctrl+C)")
            paste_action = self.addAction("붙여넣기 (Ctrl+V)")
            self.addSeparator()
            select_all_action = self.addAction("전체 선택 (Ctrl+A)")
        
        # 액션들을 속성으로 저장
        self.copy_action = copy_action
        self.paste_action = paste_action
        self.select_all_action = select_all_action
    
    def connect_to_widget(self, widget):
        """위젯에 액션 연결"""
        self.copy_action.triggered.connect(widget.copy)
        self.paste_action.triggered.connect(widget.paste)
        self.select_all_action.triggered.connect(widget.selectAll)


class InlineEditor:
    """인라인 편집 관리 클래스"""
    
    def __init__(self, tree_widget):
        self.tree = tree_widget
        self.edit_widget = None
        self.editing_index = -1
        self.is_mac = platform.system() == 'Darwin'
    
    def start_edit(self, index, item, column, current_value=""):
        """편집 시작"""
        # 기존 편집 위젯이 있다면 정리
        self.finish_current_edit()
        
        # 편집 위젯 생성
        self.edit_widget = QLineEdit(current_value)
        self.editing_index = index
        
        # 컨텍스트 메뉴 설정
        self.setup_context_menu()
        
        # 트리에 위젯 설정
        self.tree.setItemWidget(item, column, self.edit_widget)
        self.edit_widget.selectAll()
        self.edit_widget.setFocus()
        
        return self.edit_widget
    
    def setup_context_menu(self):
        """컨텍스트 메뉴 설정"""
        if not self.edit_widget:
            return
        
        self.edit_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.edit_widget.customContextMenuRequested.connect(self._show_context_menu)
    
    def _show_context_menu(self, position):
        """컨텍스트 메뉴 표시"""
        if not self.edit_widget:
            return
        
        menu = EditContextMenu(self.edit_widget)
        menu.connect_to_widget(self.edit_widget)
        menu.exec_(self.edit_widget.mapToGlobal(position))
    
    def finish_current_edit(self):
        """현재 편집 종료"""
        if self.edit_widget:
            current_item = self.tree.currentItem()
            current_column = self.tree.currentColumn()
            if current_item:
                self.tree.setItemWidget(current_item, current_column, None)
            self.edit_widget = None
            self.editing_index = -1
    
    def get_edit_value(self):
        """편집된 값 가져오기"""
        if self.edit_widget:
            return self.edit_widget.text().strip()
        return "" 