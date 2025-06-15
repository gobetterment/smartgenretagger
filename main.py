import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import eyed3
import openai
from dotenv import load_dotenv

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
                {"role": "system", "content": "음악 장르만 추천해줘. 절대 금지 단어: USA, America, American, India, Indian, Canada, Canadian, Japan, Japanese, China, Chinese, Korea, Korean, Britain, British, France, French, Germany, German, Australia, Australian - 이런 국가명/국적 단어는 절대 사용하지 마! 허용되는 지역 표기는 오직 K-Pop, East Coast, West Coast, UK, Latin만 가능. 형식: 대분류/지역/스타일 (최대 4개). 예시 1:Hip Hop / East Coast / Trap, 예시 2: Pop / Ballad, 예시 3: Rock / Alternative / Indie."},
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
        self.root.geometry("1200x700")
        self.file_list = []
        self.mp3_data = []

        # UI 구성
        # 상단 버튼 프레임
        top_frame = tk.Frame(root)
        top_frame.pack(pady=10)

        self.btn_select_folder = tk.Button(top_frame, text="폴더 선택", command=self.select_folder, font=("Arial", 12))
        self.btn_select_folder.pack(side=tk.LEFT, padx=5)

        self.btn_save_all = tk.Button(top_frame, text="모든 변경사항 저장", command=self.save_all_changes, font=("Arial", 12))
        self.btn_save_all.pack(side=tk.LEFT, padx=5)

        self.btn_gpt_all = tk.Button(top_frame, text="전체 GPT 장르 추천", command=self.get_all_gpt_suggestions, font=("Arial", 12))
        self.btn_gpt_all.pack(side=tk.LEFT, padx=5)

        # 테이블 프레임
        table_frame = tk.Frame(root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 트리뷰 (테이블) 생성
        columns = ("제목", "아티스트", "장르", "연도", "GPT 추천", "저장")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        # 컬럼 설정
        self.tree.heading("제목", text="제목")
        self.tree.heading("아티스트", text="아티스트")
        self.tree.heading("장르", text="장르")
        self.tree.heading("연도", text="연도")
        self.tree.heading("GPT 추천", text="GPT 추천")
        self.tree.heading("저장", text="저장")

        # 컬럼 너비 설정
        self.tree.column("제목", width=250)
        self.tree.column("아티스트", width=180)
        self.tree.column("장르", width=200)
        self.tree.column("연도", width=80)
        self.tree.column("GPT 추천", width=280)
        self.tree.column("저장", width=80)

        # 스크롤바
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 편집 프레임
        edit_frame = tk.Frame(root)
        edit_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(edit_frame, text="선택된 파일 편집:", font=("Arial", 12, "bold")).pack(anchor=tk.W)

        # 편집 필드들
        fields_frame = tk.Frame(edit_frame)
        fields_frame.pack(fill=tk.X, pady=5)

        tk.Label(fields_frame, text="장르:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.entry_genre = tk.Entry(fields_frame, width=40)
        self.entry_genre.grid(row=0, column=1, padx=5)

        tk.Label(fields_frame, text="연도:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.entry_year = tk.Entry(fields_frame, width=10)
        self.entry_year.grid(row=0, column=3, padx=5)

        # 버튼 프레임
        btn_frame = tk.Frame(edit_frame)
        btn_frame.pack(pady=5)

        self.btn_gpt = tk.Button(btn_frame, text="GPT로 장르 추천", command=self.get_gpt_suggestion)
        self.btn_gpt.pack(side=tk.LEFT, padx=5)

        self.btn_save = tk.Button(btn_frame, text="선택된 파일 저장", command=self.save_selected)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        # 트리뷰 선택 이벤트
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_double_click)

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
                'gpt_suggestion': ""
            }
            self.mp3_data.append(file_data)

            # 트리뷰에 추가
            self.tree.insert("", tk.END, values=(
                file_data['title'],
                file_data['artist'],
                file_data['genre'],
                file_data['year'],
                file_data['gpt_suggestion'],
                "저장"
            ))

    def on_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            index = self.tree.index(item)
            
            # 선택된 파일의 정보를 편집 필드에 표시
            data = self.mp3_data[index]
            
            self.entry_genre.delete(0, tk.END)
            self.entry_genre.insert(0, data['genre'])
            
            self.entry_year.delete(0, tk.END)
            self.entry_year.insert(0, data['year'])

    def get_selected_index(self):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            return self.tree.index(item)
        return None

    def save_selected(self):
        index = self.get_selected_index()
        if index is None:
            messagebox.showwarning("경고", "파일을 선택해주세요.")
            return

        data = self.mp3_data[index]
        path = data['path']
        audio = eyed3.load(path)
        if not audio.tag:
            audio.initTag()

        genre = self.entry_genre.get().strip()
        year = self.entry_year.get().strip()

        if genre:
            audio.tag.genre = genre
            data['genre'] = genre
        if year.isdigit():
            audio.tag.original_release_date = eyed3.core.Date(int(year))
            data['year'] = year

        audio.tag.save()

        # 트리뷰 업데이트
        item = self.tree.get_children()[index]
        self.tree.item(item, values=(
            data['title'],
            data['artist'],
            data['genre'],
            data['year'],
            data['gpt_suggestion'],
            "저장"
        ))

        messagebox.showinfo("저장", f"{data['filename']} 저장 완료!")

    def get_gpt_suggestion(self):
        index = self.get_selected_index()
        if index is None:
            messagebox.showwarning("경고", "파일을 선택해주세요.")
            return

        data = self.mp3_data[index]
        title = data['title'] or data['filename']
        artist = data['artist'] or "Unknown"

        genre_suggestion = get_genre_from_gpt(title, artist)
        data['gpt_suggestion'] = genre_suggestion
        
        # 트리뷰 업데이트
        item = self.tree.get_children()[index]
        self.tree.item(item, values=(
            data['title'],
            data['artist'],
            data['genre'],
            data['year'],
            data['gpt_suggestion'],
            "저장"
        ))

        # 편집 필드에도 반영
        self.entry_genre.delete(0, tk.END)
        self.entry_genre.insert(0, genre_suggestion)

    def save_all_changes(self):
        saved_count = 0
        for i, data in enumerate(self.mp3_data):
            path = data['path']
            audio = eyed3.load(path)
            if not audio.tag:
                audio.initTag()

            # GPT 추천이 있으면 장르에 적용
            if data['gpt_suggestion'] and not data['genre']:
                audio.tag.genre = data['gpt_suggestion']
                data['genre'] = data['gpt_suggestion']
                saved_count += 1

            audio.tag.save()

        # 트리뷰 전체 업데이트
        for i, item in enumerate(self.tree.get_children()):
            data = self.mp3_data[i]
            self.tree.item(item, values=(
                data['title'],
                data['artist'],
                data['genre'],
                data['year'],
                data['gpt_suggestion'],
                "저장"
            ))

        messagebox.showinfo("저장 완료", f"총 {saved_count}개 파일의 장르가 업데이트되었습니다.")

    def on_double_click(self, event):
        # 더블클릭한 위치 확인
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x, event.y)
            item = self.tree.identify_row(event.y)
            if item:
                index = self.tree.index(item)
                if column == "#5":  # GPT 추천 컬럼 (5번째)
                    self.edit_gpt_suggestion(index, event)
                elif column == "#6":  # 저장 컬럼 (6번째)
                    self.save_individual_file(index)

    def edit_gpt_suggestion(self, index, event):
        # 편집할 셀의 위치 계산
        item = self.tree.get_children()[index]
        bbox = self.tree.bbox(item, "#5")  # GPT 추천 컬럼
        
        if bbox:
            # 현재 값 가져오기
            current_value = self.mp3_data[index]['gpt_suggestion']
            
            # Entry 위젯 생성
            self.edit_entry = tk.Entry(self.tree, font=("Arial", 9))
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

    def finish_edit(self, index):
        if hasattr(self, 'edit_entry'):
            new_value = self.edit_entry.get().strip()
            self.edit_entry.destroy()
            
            # 데이터 업데이트
            self.mp3_data[index]['gpt_suggestion'] = new_value
            
            # 트리뷰 업데이트
            item = self.tree.get_children()[index]
            data = self.mp3_data[index]
            self.tree.item(item, values=(
                data['title'],
                data['artist'],
                data['genre'],
                data['year'],
                data['gpt_suggestion'],
                "저장"
            ))

    def cancel_edit(self):
        if hasattr(self, 'edit_entry'):
            self.edit_entry.destroy()

    def save_individual_file(self, index):
        data = self.mp3_data[index]
        path = data['path']
        
        # GPT 추천이 있으면 장르에 적용
        if data['gpt_suggestion']:
            audio = eyed3.load(path)
            if not audio.tag:
                audio.initTag()
            
            audio.tag.genre = data['gpt_suggestion']
            data['genre'] = data['gpt_suggestion']
            audio.tag.save()
            
            # 트리뷰 업데이트
            item = self.tree.get_children()[index]
            self.tree.item(item, values=(
                data['title'],
                data['artist'],
                data['genre'],
                data['year'],
                data['gpt_suggestion'],
                "저장"
            ))
            
            messagebox.showinfo("저장", f"{data['filename']} 장르 저장 완료!")
        else:
            messagebox.showwarning("경고", "GPT 추천이 없습니다. 먼저 장르를 추천받아주세요.")

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
                    data['genre'],
                    data['year'],
                    data['gpt_suggestion'],
                    "저장"
                ))
                
                # UI 업데이트를 위해 잠시 대기
                self.root.update()
        
        messagebox.showinfo("완료", f"총 {total_files}개 파일의 장르 추천이 완료되었습니다!")

# 실행
if __name__ == "__main__":
    root = tk.Tk()
    app = MP3EditorApp(root)
    root.mainloop()