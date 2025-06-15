import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import eyed3
import openai
from dotenv import load_dotenv
import logging

# eyed3 로그 레벨 설정 (경고 메시지 숨기기)
logging.getLogger("eyed3").setLevel(logging.ERROR)

# 환경변수 로드
load_dotenv()

# OpenAI API 키를 환경변수에서 가져오기
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    messagebox.showerror("오류", "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.\n.env 파일을 확인해주세요.")
    exit()

client = openai.OpenAI(api_key=api_key)

# 🔍 GPT로 장르 추론 함수
def get_genre_from_gpt(title, artist):
    try:
        prompt = f"노래 제목이 '{title}', 아티스트가 '{artist}'인 MP3의 장르를 대분류/지역/스타일 형식으로 최대 4개까지 추천해줘."
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "음악전문가로서 노래 장르를 추천해줘. 절대 금지 단어: USA, America, American, India, Indian, Canada, Canadian, Japan, Japanese, China, Chinese, Korea, Korean, Britain, British, France, French, Germany, German, Australia, Australian - 이런 국가명/국적 단어는 절대 사용하지 마! 허용되는 지역 표기는 오직 K-Pop, East Coast, West Coast, UK, Latin만 가능. 형식: 대분류/지역/스타일 (최대 4개). 예시 1:Hip Hop / East Coast / Trap, 예시 2: Pop / Ballad 예시 3: Rock / Alternative / Indie"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"GPT 오류: {str(e)}"

# MP3 처리 GUI 클래스
class MP3EditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartGenreTagger - AI 기반 MP3 장르 태그 편집기")
        self.root.geometry("1200x600")
        self.root.configure(bg="#ffffff")
        self.file_list = []
        self.mp3_data = []

        # UI 구성
        # 상단 버튼 프레임
        top_frame = tk.Frame(root, bg="#e8e8e8")
        top_frame.pack(pady=15, padx=10, fill=tk.X)

        # 버튼 스타일 설정
        button_style = {
            "font": ("SF Pro Display", 11, "normal"),
            "relief": "flat",
            "borderwidth": 0,
            "padx": 20,
            "pady": 8,
            "cursor": "hand2"
        }

        # 폴더 선택 버튼
        self.btn_select_folder = tk.Button(
            top_frame, 
            text="📁 폴더 선택", 
            command=self.select_folder,
            bg=top_frame.cget("bg"), 
            fg="black",
            activebackground=top_frame.cget("bg"),
            activeforeground="black",
            **button_style
        )
        self.btn_select_folder.pack(side=tk.LEFT, padx=8)

        # 구분선
        separator1 = tk.Frame(top_frame, width=1, height=30, bg="#999999")
        separator1.pack(side=tk.LEFT, padx=10)
                        
        # AI 추천 관련 버튼들
        self.btn_gpt_selected = tk.Button(
            top_frame, 
            text="🤖 선택 추천", 
            command=self.get_selected_gpt_suggestions,
            bg=top_frame.cget("bg"), 
            fg="black",
            activebackground=top_frame.cget("bg"),
            activeforeground="black",
            **button_style
        )
        self.btn_gpt_selected.pack(side=tk.LEFT, padx=8)

        self.btn_gpt_all = tk.Button(
            top_frame, 
            text="🤖 전체 추천", 
            command=self.get_all_gpt_suggestions,
            bg=top_frame.cget("bg"), 
            fg="black",
            activebackground=top_frame.cget("bg"),
            activeforeground="black",
            **button_style
        )
        self.btn_gpt_all.pack(side=tk.LEFT, padx=8)
        
        # 구분선
        separator2 = tk.Frame(top_frame, width=1, height=30, bg="#999999")
        separator2.pack(side=tk.LEFT, padx=10)

        # 저장 관련 버튼들
        self.btn_save_selected = tk.Button(
            top_frame, 
            text="💾 선택 저장", 
            command=self.save_selected_items,
            bg=top_frame.cget("bg"), 
            fg="black",
            activebackground=top_frame.cget("bg"),
            activeforeground="black",
            **button_style
        )
        self.btn_save_selected.pack(side=tk.LEFT, padx=8)

        self.btn_save_all = tk.Button(
            top_frame, 
            text="💾 전체 저장", 
            command=self.save_all_changes,
            bg=top_frame.cget("bg"), 
            fg="black",
            activebackground=top_frame.cget("bg"),
            activeforeground="black",
            **button_style
        )
        self.btn_save_all.pack(side=tk.LEFT, padx=8)

       

        

        # 테이블 프레임
        table_frame = tk.Frame(root, bg="#ffffff", relief="solid", borderwidth=1)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))

        # 트리뷰 (테이블) 생성 - 다중 선택 가능
        columns = ("Title", "Artist", "Year", "Genre", "Suggested Genre / Edit")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20, selectmode="extended")

        # 컬럼 설정
        self.tree.heading("Title", text="Title")
        self.tree.heading("Artist", text="Artist")
        self.tree.heading("Year", text="Year")
        self.tree.heading("Genre", text="Genre")
        self.tree.heading("Suggested Genre / Edit", text="Suggested Genre / Edit")

        # 컬럼 너비 설정
        self.tree.column("Title", width=250)
        self.tree.column("Artist", width=180)
        self.tree.column("Year", width=70, anchor="center")
        self.tree.column("Genre", width=250)
        self.tree.column("Suggested Genre / Edit", width=320)

        # 스크롤바
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 트리뷰 이벤트 바인딩
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-1>", self.on_single_click)
        


    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.file_list = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".mp3")]
            if self.file_list:
                self.load_all_files()
            else:
                messagebox.showinfo("알림", "MP3 파일이 없습니다.")

    def load_all_files(self):
        # 기존 데이터 클리어
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.mp3_data.clear()

        # 모든 MP3 파일 로드
        for i, path in enumerate(self.file_list):
            audio = eyed3.load(path)
            if not audio:
                continue

            tag = audio.tag
            if not tag:
                audio.initTag()
                tag = audio.tag

            # 연도 정보 추출 (여러 방법 시도)
            year = ""
            if tag.original_release_date:
                year = str(tag.original_release_date.year)
            elif tag.release_date:
                year = str(tag.release_date.year)
            elif tag.recording_date:
                year = str(tag.recording_date.year)
            elif hasattr(tag, 'date') and tag.date:
                year = str(tag.date.year)

            # 데이터 저장
            file_data = {
                'path': path,
                'filename': os.path.basename(path),
                'title': tag.title or "",
                'artist': tag.artist or "",
                'genre': tag.genre.name if tag.genre else "",
                'year': year,
                'original_year': year,  # 원본 연도 저장
                'year_added': False,  # 연도 추가 여부 추적
                'gpt_suggestion': ""
            }
            self.mp3_data.append(file_data)

            # 트리뷰에 추가
            self.tree.insert("", tk.END, values=(
                file_data['title'],
                file_data['artist'],
                file_data['year'],
                file_data['genre'],
                file_data['gpt_suggestion']
            ))

    def on_double_click(self, event):
        # 더블클릭한 위치 확인
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            if item:
                index = self.tree.index(item)
                if column == "#1":  # 타이틀 컬럼 (1번째)
                    self.copy_to_clipboard(self.mp3_data[index]['title'], "제목")
                    return "break"  # 이벤트 전파 중단
                elif column == "#2":  # 아티스트 컬럼 (2번째)
                    self.copy_to_clipboard(self.mp3_data[index]['artist'], "아티스트")
                    return "break"  # 이벤트 전파 중단
                elif column == "#3":  # 연도 컬럼 (3번째)
                    self.edit_year(index, event)
                elif column == "#4":  # 장르 컬럼 (4번째)
                    self.copy_to_clipboard(self.mp3_data[index]['genre'], "장르")
                    return "break"  # 이벤트 전파 중단
                elif column == "#5":  # 장르 제안 컬럼 (5번째)
                    self.edit_gpt_suggestion(index, event)

    def on_single_click(self, event):
        # 단순클릭한 위치 확인 (현재는 특별한 동작 없음)
        pass

    def edit_year(self, index, event):
        # 기존 Entry가 있다면 먼저 정리
        if hasattr(self, 'edit_entry'):
            try:
                self.edit_entry.destroy()
                delattr(self, 'edit_entry')
            except:
                pass
        
        # 편집할 셀의 위치 계산
        item = self.tree.get_children()[index]
        bbox = self.tree.bbox(item, "#3")  # 연도 컬럼
        
        if bbox:
            # 현재 값 가져오기 (✓ 표시 제거)
            current_value = self.mp3_data[index]['year'].replace(" ✓", "") if self.mp3_data[index]['year'] else ""
            
            # Entry 위젯 생성
            self.edit_entry = tk.Entry(self.tree, font=("Arial", 9), relief="solid", borderwidth=1)
            self.edit_entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
            self.edit_entry.insert(0, current_value)
            self.edit_entry.select_range(0, tk.END)
            self.edit_entry.focus()
            
            # 편집 완료 이벤트 바인딩
            self.edit_entry.bind("<Return>", lambda e: self.finish_year_edit(index))
            self.edit_entry.bind("<Escape>", lambda e: self.cancel_edit())
            self.edit_entry.bind("<FocusOut>", lambda e: self.finish_year_edit(index))
            
            # 현재 편집 중인 인덱스 저장
            self.editing_index = index

    def edit_gpt_suggestion(self, index, event):
        # 기존 Entry가 있다면 먼저 정리
        if hasattr(self, 'edit_entry'):
            try:
                self.edit_entry.destroy()
                delattr(self, 'edit_entry')
            except:
                pass
        
        # 편집할 셀의 위치 계산
        item = self.tree.get_children()[index]
        bbox = self.tree.bbox(item, "#5")  # GPT 추천 컬럼
        
        if bbox:
            # 현재 값 가져오기
            current_value = self.mp3_data[index]['gpt_suggestion']
            
            # Entry 위젯 생성
            self.edit_entry = tk.Entry(self.tree, font=("Arial", 9), relief="solid", borderwidth=1)
            self.edit_entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
            self.edit_entry.insert(0, current_value)
            self.edit_entry.select_range(0, tk.END)
            self.edit_entry.focus()
            
            # 편집 완료 이벤트 바인딩
            self.edit_entry.bind("<Return>", lambda e: self.finish_edit(index))
            self.edit_entry.bind("<Escape>", lambda e: self.cancel_edit())
            self.edit_entry.bind("<FocusOut>", lambda e: self.finish_edit(index))
            
            # 현재 편집 중인 인덱스 저장
            self.editing_index = index

    def finish_year_edit(self, index):
        if hasattr(self, 'edit_entry'):
            try:
                # Entry가 존재하는지 확인
                if self.edit_entry.winfo_exists():
                    new_value = self.edit_entry.get().strip()
                else:
                    new_value = ""
                
                # Entry 정리
                try:
                    self.edit_entry.destroy()
                except:
                    pass
                delattr(self, 'edit_entry')
                
                # 데이터 업데이트
                data = self.mp3_data[index]
                print(f"Debug: 편집 완료 - 파일: {data['filename']}, 입력값: '{new_value}', 원본: '{data['original_year']}'")
                
                # 연도 변경 감지 및 표시 설정
                if new_value and new_value.isdigit():
                    # 연도는 4자리 숫자만 허용
                    if len(new_value) != 4:
                        messagebox.showerror("입력 오류", "연도는 4자리 숫자만 입력 가능합니다.\n예: 2023")
                        return
                    
                    # 원래 비어있던 경우 또는 값이 변경된 경우
                    if not data['original_year'] or new_value != data['original_year']:
                        data['year_added'] = True
                        data['year'] = new_value + " ✓"  # 수정/추가된 연도에 초록 원 표시
                        print(f"Debug: 연도 수정/추가됨 - {data['year']}")
                    else:
                        data['year_added'] = False
                        data['year'] = new_value
                        print(f"Debug: 연도 동일함 - {data['year']}")
                elif new_value and not new_value.isdigit():
                    messagebox.showerror("입력 오류", "연도는 4자리 숫자만 입력 가능합니다.\n예: 2023")
                    return
                else:
                    data['year_added'] = False
                    data['year'] = new_value
                    print(f"Debug: 연도 비어있음 - {data['year']}")
                
                # 트리뷰 업데이트
                item = self.tree.get_children()[index]
                self.tree.item(item, values=(
                    data['title'],
                    data['artist'],
                    data['year'],
                    data['genre'],
                    data['gpt_suggestion']
                ))
                
                # 트리뷰 새로고침
                self.tree.update()
                
            except Exception as e:
                print(f"Error in finish_year_edit: {e}")
                # Entry 정리
                if hasattr(self, 'edit_entry'):
                    try:
                        self.edit_entry.destroy()
                    except:
                        pass
                    try:
                        delattr(self, 'edit_entry')
                    except:
                        pass

    def finish_edit(self, index):
        if hasattr(self, 'edit_entry'):
            try:
                # Entry가 존재하는지 확인
                if self.edit_entry.winfo_exists():
                    new_value = self.edit_entry.get().strip()
                else:
                    new_value = ""
                
                # Entry 정리
                try:
                    self.edit_entry.destroy()
                except:
                    pass
                delattr(self, 'edit_entry')
                
                # 데이터 업데이트
                self.mp3_data[index]['gpt_suggestion'] = new_value
                
                # 트리뷰 업데이트
                item = self.tree.get_children()[index]
                data = self.mp3_data[index]
                self.tree.item(item, values=(
                    data['title'],
                    data['artist'],
                    data['year'],
                    data['genre'],
                    data['gpt_suggestion']
                ))
                
                # 트리뷰 새로고침
                self.tree.update()
                
            except Exception as e:
                print(f"Error in finish_edit: {e}")
                # Entry 정리
                if hasattr(self, 'edit_entry'):
                    try:
                        self.edit_entry.destroy()
                    except:
                        pass
                    try:
                        delattr(self, 'edit_entry')
                    except:
                        pass

    def cancel_edit(self):
        if hasattr(self, 'edit_entry'):
            try:
                self.edit_entry.destroy()
            except:
                pass
            try:
                delattr(self, 'edit_entry')
            except:
                pass

    def copy_to_clipboard(self, text, field_name):
        """텍스트를 클립보드에 복사 (팝업 없이)"""
        if text:
            # 중복 복사 방지를 위한 간단한 체크
            current_clipboard = ""
            try:
                current_clipboard = self.root.clipboard_get()
            except:
                pass
            
            if current_clipboard != text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update()  # 클립보드 업데이트 확실히 하기
                print(f"{field_name} 복사됨: {text}")  # 콘솔에만 출력
        else:
            print(f"{field_name} 정보가 없습니다.")  # 콘솔에만 출력

    def save_individual_file(self, index):
        data = self.mp3_data[index]
        path = data['path']
        
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
                audio.tag.release_date = eyed3.core.Date(year_int)
                audio.tag.recording_date = eyed3.core.Date(year_int)
                print(f"Debug: 연도 저장됨 - {year_value} (원본: {original_year})")
            elif not year_value and original_year:
                # 연도 삭제 (빈 값으로 설정)
                audio.tag.original_release_date = None
                audio.tag.release_date = None
                audio.tag.recording_date = None
                print(f"Debug: 연도 삭제됨 (원본: {original_year})")
        
        # 저장
        audio.tag.save()
        
        # 저장 후 ✓ 표시 제거 및 원본 연도 업데이트
        year_value = data['year'].replace(" ✓", "") if data['year'] else ""
        data['year'] = year_value
        data['original_year'] = year_value  # 원본 연도를 현재 연도로 업데이트
        
        # 트리뷰 업데이트
        item = self.tree.get_children()[index]
        self.tree.item(item, values=(
            data['title'],
            data['artist'],
            data['year'],
            data['genre'],
            data['gpt_suggestion']
        ))
        
        # 저장 완료 메시지
        saved_info = []
        if data['gpt_suggestion']:
            saved_info.append("장르")
        year_value = data['year'].replace(" ✓", "") if data['year'] else ""
        original_year = data['original_year'] if data['original_year'] else ""
        if original_year != year_value:  # 연도 변경 (추가/수정/삭제 모두 포함)
            saved_info.append("연도")
        
        if saved_info:
            messagebox.showinfo("저장 완료", f"✅ {data['filename']}\n{', '.join(saved_info)} 저장 완료!")
        else:
            messagebox.showinfo("저장 완료", f"✅ {data['filename']}\n(변경사항 없음)")

    def save_all_changes(self):
        saved_count = 0
        for i, data in enumerate(self.mp3_data):
            path = data['path']
            audio = eyed3.load(path)
            if not audio.tag:
                audio.initTag()

            file_updated = False
            
            # GPT 추천이 있으면 장르에 적용
            if data['gpt_suggestion']:
                audio.tag.genre = data['gpt_suggestion']
                data['genre'] = data['gpt_suggestion']
                file_updated = True
            
            # 연도 정보 처리 (추가/수정/삭제)
            year_value = data['year'].replace(" ✓", "") if data['year'] else ""
            original_year = data['original_year'] if data['original_year'] else ""
            
            # 연도가 변경된 경우 (추가, 수정, 삭제 모두 포함)
            if original_year != year_value:
                if year_value and year_value.isdigit():
                    # 연도 추가/수정
                    year_int = int(year_value)
                    audio.tag.original_release_date = eyed3.core.Date(year_int)
                    audio.tag.release_date = eyed3.core.Date(year_int)
                    audio.tag.recording_date = eyed3.core.Date(year_int)
                    file_updated = True
                    print(f"Debug: 일괄저장 - 연도 저장됨 - {year_value} (원본: {original_year})")
                elif not year_value and original_year:
                    # 연도 삭제 (빈 값으로 설정)
                    audio.tag.original_release_date = None
                    audio.tag.release_date = None
                    audio.tag.recording_date = None
                    file_updated = True
                    print(f"Debug: 일괄저장 - 연도 삭제됨 (원본: {original_year})")
            
            if file_updated:
                saved_count += 1

            audio.tag.save()
            
            # 저장 후 ✓ 표시 제거 및 원본 연도 업데이트
            if file_updated:
                year_value = data['year'].replace(" ✓", "") if data['year'] else ""
                data['year'] = year_value
                data['original_year'] = year_value  # 원본 연도를 현재 연도로 업데이트

        # 트리뷰 전체 업데이트
        for i, item in enumerate(self.tree.get_children()):
            data = self.mp3_data[i]
            self.tree.item(item, values=(
                data['title'],
                data['artist'],
                data['year'],
                data['genre'],
                data['gpt_suggestion']
            ))

        messagebox.showinfo("저장 완료", f"✅ 일괄 저장 완료!\n총 {saved_count}개 파일이 업데이트되었습니다.")

    def save_selected_items(self):
        # 선택된 항목들 가져오기
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showwarning("선택 필요", "저장할 항목을 선택해주세요.\n(Ctrl+클릭으로 다중 선택 가능)")
            return
        
        saved_count = 0
        saved_files = []
        
        for item in selected_items:
            # 선택된 항목의 인덱스 찾기
            index = self.tree.index(item)
            data = self.mp3_data[index]
            path = data['path']
            
            audio = eyed3.load(path)
            if not audio.tag:
                audio.initTag()

            file_updated = False
            saved_info = []
            
            # GPT 추천이 있으면 장르에 적용
            if data['gpt_suggestion']:
                audio.tag.genre = data['gpt_suggestion']
                data['genre'] = data['gpt_suggestion']
                file_updated = True
                saved_info.append("장르")
            
            # 연도 정보 처리 (추가/수정/삭제)
            year_value = data['year'].replace(" ✓", "") if data['year'] else ""
            original_year = data['original_year'] if data['original_year'] else ""
            
            # 연도가 변경된 경우 (추가, 수정, 삭제 모두 포함)
            if original_year != year_value:
                if year_value and year_value.isdigit():
                    # 연도 추가/수정
                    year_int = int(year_value)
                    audio.tag.original_release_date = eyed3.core.Date(year_int)
                    audio.tag.release_date = eyed3.core.Date(year_int)
                    audio.tag.recording_date = eyed3.core.Date(year_int)
                    file_updated = True
                    saved_info.append("연도")
                    print(f"Debug: 선택저장 - 연도 저장됨 - {year_value} (원본: {original_year})")
                elif not year_value and original_year:
                    # 연도 삭제 (빈 값으로 설정)
                    audio.tag.original_release_date = None
                    audio.tag.release_date = None
                    audio.tag.recording_date = None
                    file_updated = True
                    saved_info.append("연도")
                    print(f"Debug: 선택저장 - 연도 삭제됨 (원본: {original_year})")
            
            if file_updated:
                saved_count += 1
                saved_files.append(f"{data['filename']} ({', '.join(saved_info)})")
                
                # 저장 후 ✓ 표시 제거 및 원본 연도 업데이트
                year_value = data['year'].replace(" ✓", "") if data['year'] else ""
                data['year'] = year_value
                data['original_year'] = year_value

            audio.tag.save()

        # 트리뷰 전체 업데이트
        for i, item in enumerate(self.tree.get_children()):
            data = self.mp3_data[i]
            self.tree.item(item, values=(
                data['title'],
                data['artist'],
                data['year'],
                data['genre'],
                data['gpt_suggestion']
            ))

        # 결과 메시지
        if saved_count > 0:
            files_info = "\n".join(saved_files[:5])  # 최대 5개까지만 표시
            if len(saved_files) > 5:
                files_info += f"\n... 외 {len(saved_files) - 5}개"
            messagebox.showinfo("저장 완료", f"✅ 선택된 항목 저장 완료!\n\n{files_info}\n\n총 {saved_count}개 파일 업데이트")
        else:
            messagebox.showinfo("저장 완료", f"✅ 선택된 {len(selected_items)}개 항목 처리 완료!\n(변경사항 없음)")

    def get_all_gpt_suggestions(self):
        if not self.mp3_data:
            messagebox.showwarning("경고", "먼저 폴더를 선택해주세요.")
            return
        
        # 진행 상황을 보여주기 위한 간단한 메시지
        total_files = len(self.mp3_data)
        messagebox.showinfo("시작", f"총 {total_files}개 파일의 장르를 추천받습니다. 시간이 걸릴 수 있습니다.")
        
        for i, data in enumerate(self.mp3_data):
            if not data['gpt_suggestion']:  # 이미 추천받지 않은 경우만
                title = data['title'] or data['filename']
                artist = data['artist'] or "Unknown"
                
                genre_suggestion = get_genre_from_gpt(title, artist)
                data['gpt_suggestion'] = genre_suggestion
                
                # 트리뷰 업데이트
                item = self.tree.get_children()[i]
                self.tree.item(item, values=(
                    data['title'],
                    data['artist'],
                    data['year'],
                    data['genre'],
                    data['gpt_suggestion']
                ))
                
                # UI 업데이트를 위해 잠시 대기
                self.root.update()

        messagebox.showinfo("완료", f"총 {total_files}개 파일의 장르 추천이 완료되었습니다!")

    def get_selected_gpt_suggestions(self):
        # 선택된 항목들 가져오기
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showwarning("선택 필요", "장르 추천을 받을 항목을 선택해주세요.\n(Ctrl+클릭으로 다중 선택 가능)")
            return
        
        # 진행 상황을 보여주기 위한 메시지
        total_selected = len(selected_items)
        messagebox.showinfo("시작", f"선택된 {total_selected}개 파일의 장르를 추천받습니다. 시간이 걸릴 수 있습니다.")
        
        processed_count = 0
        
        for item in selected_items:
            # 선택된 항목의 인덱스 찾기
            index = self.tree.index(item)
            data = self.mp3_data[index]
            
            # 이미 추천받지 않은 경우만 또는 덮어쓰기
            title = data['title'] or data['filename']
            artist = data['artist'] or "Unknown"
            
            genre_suggestion = get_genre_from_gpt(title, artist)
            data['gpt_suggestion'] = genre_suggestion
            processed_count += 1
            
            # 트리뷰 업데이트
            self.tree.item(item, values=(
                data['title'],
                data['artist'],
                data['year'],
                data['genre'],
                data['gpt_suggestion']
            ))
            
            # UI 업데이트를 위해 잠시 대기
            self.root.update()
            
            # 진행 상황 표시 (콘솔)
            print(f"진행: {processed_count}/{total_selected} - {data['filename']}")

        messagebox.showinfo("완료", f"✅ 선택된 항목 장르 추천 완료!\n총 {processed_count}개 파일 처리됨")

# 실행
if __name__ == "__main__":
    root = tk.Tk()
    app = MP3EditorApp(root)
    root.mainloop()