import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import sqlite3
import os
import json
import shutil
import sys
import zipfile
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

# --- PDF CONFIG ---
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

        ctk.CTkLabel(self.tab_form, text="Medications and Indications").pack(anchor="w", padx=20)
        self.txt_meds = ctk.CTkTextbox(self.tab_form, height=300)
        self.txt_meds.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(self.tab_form, text="Private Notes (Internal Only)").pack(anchor="w", padx=20)
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
        
        ctk.CTkButton(img_info_bar, text="Save Analysis", fg_color="#27ae60", width=120, command=self.save_patient).pack(side="right", padx=10)

        self.img_grid = ctk.CTkFrame(self.tab_images)
        self.img_grid.pack(pady=5, padx=20, fill="both", expand=True)
        self.image_labels = []
        for i in range(9):
            r, c = divmod(i, 3)
            slot = ctk.CTkFrame(self.img_grid, border_width=1, border_color="#555")
            slot.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            lbl = ctk.CTkLabel(slot, text=f"Empty ({r+1},{c+1})")
            lbl.pack(expand=True, pady=5)
            self.image_labels.append(lbl)
            b_frame = ctk.CTkFrame(slot, fg_color="transparent")
            b_frame.pack(side="bottom", fill="x")
            ctk.CTkButton(b_frame, text="Add", width=35, command=lambda idx=i: self.add_image(idx)).pack(side="left", padx=2, pady=2)
            ctk.CTkButton(b_frame, text="Del", width=35, fg_color="#c0392b", command=lambda idx=i: self.remove_image(idx)).pack(side="right", padx=2, pady=2)

        self.img_grid.grid_columnconfigure((0,1,2), weight=1)
        self.img_grid.grid_rowconfigure((0,1,2), weight=1)

        ctk.CTkLabel(self.tab_images, text="Image Analysis / Observations").pack(anchor="w", padx=20)
        self.txt_img_desc = ctk.CTkTextbox(self.tab_images, height=100)
        self.txt_img_desc.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(self.tab_images, text="Print Image PDF", fg_color="#2980b9", command=self.generate_image_pdf).pack(pady=10)

        # --- TAB 3: RECORDS ---
        top_bar = ctk.CTkFrame(self.tab_records)
        top_bar.pack(fill="x", padx=10, pady=10)
        self.ent_search = ctk.CTkEntry(top_bar, placeholder_text="Search Name...", width=300)
        self.ent_search.pack(side="left", padx=10)
        self.ent_search.bind("<KeyRelease>", self.refresh_records_table)

        # Re-added Export/Import and Repair
        ctk.CTkButton(top_bar, text="Export Data", fg_color="#8e44ad", command=self.export_data).pack(side="right", padx=5)
        ctk.CTkButton(top_bar, text="Import Data", fg_color="#d35400", command=self.import_data).pack(side="right", padx=5)
        ctk.CTkButton(top_bar, text="Repair DB", fg_color="#e67e22", command=self.repair_database).pack(side="right", padx=5)

        self.tree = ttk.Treeview(self.tab_records, columns=("ID", "Name", "Age", "Date"), show="headings")
        for col in ("ID", "Name", "Age", "Date"): self.tree.heading(col, text=col)
        self.tree.column("ID", width=50)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkButton(self.tab_records, text="Retrieve and Load Patient", height=50, fg_color="#27ae60", command=self.load_selected).pack(pady=10)

    # --- LOGIC ---
    def add_image(self, idx):
        path = filedialog.askopenfilename()
        if path:
            filename = f"IMG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{idx}_{os.path.basename(path)}"
            dest = os.path.join(MEDIA_FOLDER, filename)
            shutil.copy2(path, dest)
            self.image_paths[idx] = filename
            self.update_thumbnail(idx, dest)

    def remove_image(self, idx):
        self.image_paths[idx] = None
        self.image_labels[idx].configure(text="Empty", image="")

    def update_thumbnail(self, idx, path):
        img = Image.open(path)
        img.thumbnail((110, 110))
        photo = ImageTk.PhotoImage(img)
        self.image_labels[idx].configure(image=photo, text="")
        self.image_labels[idx].image = photo

    def save_patient(self):
        name = self.ent_name.get()
        if not name: return messagebox.showerror("Error", "Name required")
        data = (name, self.ent_age.get(), self.ent_date.get(), self.txt_meds.get("1.0", "end-1c"), 
                self.txt_notes.get("1.0", "end-1c"), json.dumps(self.image_paths), self.txt_img_desc.get("1.0", "end-1c"))
        with sqlite3.connect(DB_NAME) as conn:
            if self.current_patient_id:
                conn.execute("UPDATE patients SET name=?, age=?, date=?, meds=?, notes=?, images=?, image_desc=? WHERE id=?", (*data, self.current_patient_id))
            else:
                cursor = conn.execute("INSERT INTO patients (name, age, date, meds, notes, images, image_desc) VALUES (?,?,?,?,?,?,?)", data)
                self.current_patient_id = cursor.lastrowid
        self.lbl_img_patient.configure(text=f"Current Patient: {name} ({self.ent_age.get()})")
        messagebox.showinfo("Saved", "Database updated.")
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
            self.ent_name.insert(0, str(name))
            self.ent_age.insert(0, str(age))
            self.ent_date.delete(0, "end"); self.ent_date.insert(0, str(date))
            self.txt_notes.insert("1.0", notes if notes else "")
            self.txt_img_desc.insert("1.0", img_desc if img_desc else "")
            self.lbl_img_patient.configure(text=f"Current Patient: {name} ({age})")
            self.image_paths = json.loads(imgs)
            for i, fname in enumerate(self.image_paths):
                if fname:
                    fpath = os.path.join(MEDIA_FOLDER, fname)
                    if os.path.exists(fpath): self.update_thumbnail(i, fpath)
            self.tabs.set("New Patient")

    def export_data(self):
        path = filedialog.asksaveasfilename(defaultextension=".zip", initialdir=BASE_DIR)
        if not path: return
        with zipfile.ZipFile(path, 'w') as z:
            if os.path.exists(DB_NAME): z.write(DB_NAME, arcname=os.path.basename(DB_NAME))
            for f in os.listdir(MEDIA_FOLDER):
                z.write(os.path.join(MEDIA_FOLDER, f), arcname=os.path.join("patient_media", f))
        messagebox.showinfo("Export", "Data and Images exported successfully.")

    def import_data(self):
        path = filedialog.askopenfilename(filetypes=[("Zip", "*.zip")], initialdir=BASE_DIR)
        if path and messagebox.askyesno("Confirm", "Overwrite current data?"):
            with zipfile.ZipFile(path, 'r') as z:
                z.extractall(BASE_DIR)
            self.refresh_records_table()
            messagebox.showinfo("Import", "Data imported successfully.")

    def repair_database(self):
        with sqlite3.connect(DB_NAME) as conn:
            rows = conn.execute("SELECT id, images FROM patients").fetchall()
            for r_id, img_json in rows:
                paths = json.loads(img_json)
                fixed = [p if p and os.path.exists(os.path.join(MEDIA_FOLDER, p)) else None for p in paths]
                conn.execute("UPDATE patients SET images=? WHERE id=?", (json.dumps(fixed), r_id))
        messagebox.showinfo("Repair", "Sync complete.")

    def generate_patient_pdf(self):
        filename = os.path.join(BASE_DIR, f"Record_{self.ent_name.get()}.pdf")
        c = canvas.Canvas(filename, pagesize=letter)
        w, h = letter
        y = h - TOP_MARGIN_PTS
        c.setFont("Helvetica", FONT_SIZE)
        c.drawString(50, y, f"Patient: {self.ent_name.get()}")
        c.drawString(400, y, f"Age: {self.ent_age.get()}")
        c.drawRightString(w - 50, y, f"Date: {self.ent_date.get()}")
        y -= 30
        for line in self.txt_meds.get("1.0", "end-1c").split('\n'):
            if y < 50: c.showPage(); y = h - 50
            c.drawString(50, y, line); y -= 15
        c.save(); os.startfile(filename)

    def generate_image_pdf(self):
        filename = os.path.join(BASE_DIR, f"Analysis_{self.ent_name.get()}.pdf")
        c = canvas.Canvas(filename, pagesize=letter)
        w, h = letter
        c.setFont("Helvetica", FONT_SIZE)
        c.drawString(50, h-50, f"Patient: {self.ent_name.get()}")
        c.drawString(300, h-50, f"Age: {self.ent_age.get()}")
        c.drawRightString(w-50, h-50, f"Date: {self.ent_date.get()}")
        y = h-80
        for line in self.txt_img_desc.get("1.0", "end-1c").split('\n'):
            if y < 50: c.showPage(); y = h - 50
            c.drawString(50, y, line); y -= 15
        y_grid = y - 30
        for i, fname in enumerate(self.image_paths):
            if fname:
                fpath = os.path.join(MEDIA_FOLDER, fname)
                if os.path.exists(fpath):
                    row, col = divmod(i, 3)
                    ix, iy = 50 + (col*185), y_grid - 160 - (row*165)
                    if iy < 50: c.showPage(); y_grid = h - 50; iy = y_grid - 160
                    c.drawImage(fpath, ix, iy, width=175, height=155, preserveAspectRatio=True)
        c.save(); os.startfile(filename)

    def clear_form(self):
        self.current_patient_id = None
        self.ent_name.delete(0, "end"); self.ent_age.delete(0, "end")
        self.txt_meds.delete("1.0", "end"); self.txt_notes.delete("1.0", "end")
        self.txt_img_desc.delete("1.0", "end")
        self.lbl_img_patient.configure(text="Current Patient: None Selected")
        self.image_paths = [None] * 9
        for lbl in self.image_labels: lbl.configure(text="Empty", image=""); lbl.image = None

    def refresh_records_table(self, event=None):
        for i in self.tree.get_children(): self.tree.delete(i)
        with sqlite3.connect(DB_NAME) as conn:
            rows = conn.execute("SELECT id, name, age, date FROM patients WHERE name LIKE ?", (f"%{self.ent_search.get()}%",)).fetchall()
            for r in rows: self.tree.insert("", "end", values=r)

if __name__ == "__main__":
    root = ctk.CTk()
    app = MedicalApp(root)
    root.mainloop()