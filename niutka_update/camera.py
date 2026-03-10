import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import sqlite3
import os
import json
import shutil
import sys
import zipfile
import cv2
import time
from datetime import datetime
from PIL import Image, ImageTk
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# --- EXE PATH LOGIC ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
DB_NAME = os.path.join(BASE_DIR, "medical_data.db")
MEDIA_FOLDER = os.path.join(BASE_DIR, "patient_media")

# --- PDF CONFIGURATION ---
TOP_MARGIN_PTS = 4 * 28.3465  # 4 cm
FONT_SIZE = 11

if not os.path.exists(MEDIA_FOLDER):
    os.makedirs(MEDIA_FOLDER)

class MedicalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Medical Management System Pro")
        self.root.geometry("1200x900")

        self.current_patient_id = None
        self.image_paths = [None] * 9 
        
        self.init_db()
        self.setup_ui()
        self.refresh_records_table()

    def init_db(self):
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, age TEXT, date TEXT,
                meds TEXT, notes TEXT, images TEXT,
                image_desc TEXT
            )''')

    def setup_ui(self):
        self.tabs = ctk.CTkTabview(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_form = self.tabs.add("New Patient")
        self.tab_images = self.tabs.add("Patient Images")
        self.tab_records = self.tabs.add("Patient Records")

        # --- TAB 1: FORM ---
        header_frame = ctk.CTkFrame(self.tab_form, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=20)
        
        self.ent_name = ctk.CTkEntry(header_frame, placeholder_text="Name", width=400)
        self.ent_name.pack(side="left", padx=(0, 20))
        self.ent_age = ctk.CTkEntry(header_frame, placeholder_text="Age", width=100)
        self.ent_age.pack(side="left", padx=(0, 20))
        self.ent_date = ctk.CTkEntry(header_frame, width=150)
        self.ent_date.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.ent_date.pack(side="right")

        self.txt_meds = ctk.CTkTextbox(self.tab_form, height=300)
        self.txt_meds.pack(fill="x", padx=20, pady=5)
        self.txt_notes = ctk.CTkTextbox(self.tab_form, height=100)
        self.txt_notes.pack(fill="x", padx=20, pady=5)

        btn_row = ctk.CTkFrame(self.tab_form, fg_color="transparent")
        btn_row.pack(pady=20)
        ctk.CTkButton(btn_row, text="Save Patient", fg_color="#27ae60", command=self.save_patient).pack(side="left", padx=10)
        ctk.CTkButton(btn_row, text="Print Patient PDF", fg_color="#2980b9", command=self.generate_patient_pdf).pack(side="left", padx=10)
        ctk.CTkButton(btn_row, text="Clear Form", fg_color="#c0392b", command=self.clear_form).pack(side="left", padx=10)

        # --- TAB 2: IMAGES ---
        img_info_bar = ctk.CTkFrame(self.tab_images, fg_color="#333")
        img_info_bar.pack(fill="x", padx=20, pady=10)
        self.lbl_img_patient = ctk.CTkLabel(img_info_bar, text="Current Patient: None Selected", font=("Helvetica", 14, "bold"))
        self.lbl_img_patient.pack(side="left", padx=20, pady=10)

        self.img_grid = ctk.CTkFrame(self.tab_images)
        self.img_grid.pack(pady=5, padx=20, fill="both", expand=True)
        self.image_labels = []
        for i in range(9):
            r, c = divmod(i, 3)
            slot = ctk.CTkFrame(self.img_grid, border_width=1, border_color="#555")
            slot.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            lbl = ctk.CTkLabel(slot, text=f"Slot {i+1}")
            lbl.pack(expand=True, pady=5)
            self.image_labels.append(lbl)
            b_frame = ctk.CTkFrame(slot, fg_color="transparent")
            b_frame.pack(side="bottom", fill="x")
            ctk.CTkButton(b_frame, text="File", width=35, command=lambda idx=i: self.add_image_file(idx)).pack(side="left", padx=2, pady=2)
            ctk.CTkButton(b_frame, text="Cam", width=35, fg_color="#8e44ad", command=lambda idx=i: self.capture_camera(idx)).pack(side="left", padx=2, pady=2)
            ctk.CTkButton(b_frame, text="Delete", width=35, fg_color="#c0392b", command=lambda idx=i: self.remove_image(idx)).pack(side="right", padx=2, pady=2)

        self.img_grid.grid_columnconfigure((0,1,2), weight=1)
        self.img_grid.grid_rowconfigure((0,1,2), weight=1)

        self.txt_img_desc = ctk.CTkTextbox(self.tab_images, height=100)
        self.txt_img_desc.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(self.tab_images, text="Print Image PDF", fg_color="#2980b9", command=self.generate_image_pdf).pack(pady=10)

        # --- TAB 3: RECORDS ---
        top_bar = ctk.CTkFrame(self.tab_records); top_bar.pack(fill="x", padx=10, pady=10)
        self.ent_search = ctk.CTkEntry(top_bar, placeholder_text="Search Name...", width=300); self.ent_search.pack(side="left", padx=10)
        self.ent_search.bind("<KeyRelease>", self.refresh_records_table)
        self.tree = ttk.Treeview(self.tab_records, columns=("ID", "Name", "Age", "Date"), show="headings")
        for col in ("ID", "Name", "Age", "Date"): self.tree.heading(col, text=col)
        self.tree.column("ID", width=50); self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(self.tab_records, text="Load Selected Patient", height=50, fg_color="#27ae60", command=self.load_selected).pack(pady=10)

    # --- CAMERA LOGIC (NO-FREEZE VERSION) ---
    def capture_camera(self, idx):
        # 1. Initialize with DirectShow
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            # Try index 1 if 0 is blocked
            cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
            if not cap.isOpened():
                messagebox.showerror("Connection Error", "Camera not found. Check USB connection.")
                return

        # 2. Warm-up sequence to prevent freezing
        # This keeps the main GUI from thinking the app is "Not Responding"
        time.sleep(1.5) 

        # 3. Apply stability settings
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while True:
            # Clear hardware buffer
            cap.grab()
            ret, frame = cap.retrieve()
            
            if not ret or frame is None:
                continue
            
            cv2.imshow("Preview (SPACE: Snapshot, ESC: Exit)", frame)
            key = cv2.waitKey(1)
            
            if key == 27: break # ESC
            elif key == 32: # SPACE / Pedal
                filename = f"CAM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{idx}.jpg"
                dest = os.path.join(MEDIA_FOLDER, filename)
                cv2.imwrite(dest, frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
                self.image_paths[idx] = filename
                self.update_thumbnail(idx, dest)
                break
        
        cap.release()
        cv2.destroyAllWindows()

    def update_thumbnail(self, idx, path):
        img = Image.open(path)
        img.thumbnail((110, 110))
        photo = ImageTk.PhotoImage(img)
        self.image_labels[idx].configure(image=photo, text="")
        self.image_labels[idx].image = photo

    def add_image_file(self, idx):
        path = filedialog.askopenfilename()
        if path:
            filename = f"IMG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{idx}_{os.path.basename(path)}"
            dest = os.path.join(MEDIA_FOLDER, filename)
            shutil.copy2(path, dest)
            self.image_paths[idx] = filename
            self.update_thumbnail(idx, dest)

    def remove_image(self, idx):
        self.image_paths[idx] = None
        self.image_labels[idx].configure(text=f"Slot {idx+1}", image="")

    def save_patient(self):
        name = self.ent_name.get()
        if not name: return messagebox.showerror("Error", "Patient name required")
        data = (name, self.ent_age.get(), self.ent_date.get(), self.txt_meds.get("1.0", "end-1c"), 
                self.txt_notes.get("1.0", "end-1c"), json.dumps(self.image_paths), self.txt_img_desc.get("1.0", "end-1c"))
        with sqlite3.connect(DB_NAME) as conn:
            if self.current_patient_id:
                conn.execute("UPDATE patients SET name=?, age=?, date=?, meds=?, notes=?, images=?, image_desc=? WHERE id=?", (*data, self.current_patient_id))
            else:
                cursor = conn.execute("INSERT INTO patients (name, age, date, meds, notes, images, image_desc) VALUES (?,?,?,?,?,?,?)", data)
                self.current_patient_id = cursor.lastrowid
        messagebox.showinfo("Status", "Saved successfully.")
        self.refresh_records_table()

    def load_selected(self):
        selection = self.tree.selection()
        if not selection: return
        p_id = self.tree.item(selection[0])['values'][0]
        with sqlite3.connect(DB_NAME) as conn:
            row = conn.execute("SELECT * FROM patients WHERE id=?", (p_id,)).fetchone()
        if row:
            self.clear_form()
            self.current_patient_id, name, age, date, _, notes, imgs, img_desc = row
            self.ent_name.insert(0, str(name)); self.ent_age.insert(0, str(age))
            self.ent_date.delete(0, "end"); self.ent_date.insert(0, str(date))
            self.txt_notes.insert("1.0", notes if notes else ""); self.txt_img_desc.insert("1.0", img_desc if img_desc else "")
            self.image_paths = json.loads(imgs)
            for i, fname in enumerate(self.image_paths):
                if fname:
                    fpath = os.path.join(MEDIA_FOLDER, fname)
                    if os.path.exists(fpath): self.update_thumbnail(i, fpath)
            self.tabs.set("New Patient")

    def generate_patient_pdf(self):
        filename = os.path.join(BASE_DIR, f"Record_{self.ent_name.get()}.pdf")
        c = canvas.Canvas(filename, pagesize=letter); w, h = letter
        y = h - TOP_MARGIN_PTS
        c.setFont("Helvetica", FONT_SIZE)
        c.drawString(50, y, f"Patient: {self.ent_name.get()}"); y -= 20
        for line in self.txt_meds.get("1.0", "end-1c").split('\n'):
            if y < 50: c.showPage(); y = h - 50
            c.drawString(50, y, line); y -= 15
        c.save(); os.startfile(filename)

    def generate_image_pdf(self):
        filename = os.path.join(BASE_DIR, f"Analysis_{self.ent_name.get()}.pdf")
        c = canvas.Canvas(filename, pagesize=letter); w, h = letter
        c.setFont("Helvetica", FONT_SIZE); c.drawString(50, h-50, f"Patient: {self.ent_name.get()}")
        y_grid = h - 100
        for i, fname in enumerate(self.image_paths):
            if fname:
                fpath = os.path.join(MEDIA_FOLDER, fname)
                if os.path.exists(fpath):
                    row, col = divmod(i, 3); ix, iy = 50 + (col*185), y_grid - 160 - (row*165)
                    c.drawImage(fpath, ix, iy, width=175, height=155, preserveAspectRatio=True)
        c.save(); os.startfile(filename)

    def clear_form(self):
        self.current_patient_id = None
        self.ent_name.delete(0, "end"); self.ent_age.delete(0, "end")
        self.txt_meds.delete("1.0", "end"); self.txt_notes.delete("1.0", "end")
        self.image_paths = [None] * 9
        for lbl in self.image_labels: lbl.configure(text="Slot", image=""); lbl.image = None

    def refresh_records_table(self, event=None):
        for i in self.tree.get_children(): self.tree.delete(i)
        with sqlite3.connect(DB_NAME) as conn:
            rows = conn.execute("SELECT id, name, age, date FROM patients WHERE name LIKE ?", (f"%{self.ent_search.get()}%",)).fetchall()
            for r in rows: self.tree.insert("", "end", values=r)

if __name__ == "__main__":
    root = ctk.CTk()
    app = MedicalApp(root)
    root.mainloop()