import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import sqlite3
import os
import sys
import json
import shutil
import webbrowser
from datetime import datetime
from PIL import Image, ImageTk
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DB_NAME = "medical_data.db"
MEDIA_FOLDER = "patient_media"
TOP_MARGIN_PTS = 3.5 * 28.3465 

if not os.path.exists(MEDIA_FOLDER):
    os.makedirs(MEDIA_FOLDER)

class MedicalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Medico")
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
        
        self.tab_form = self.tabs.add("Nuevo Paciente")
        self.tab_images = self.tabs.add("Imagenes")
        self.tab_records = self.tabs.add("Historial")

        # --- Pestaña Formulario ---
        f_header = ctk.CTkFrame(self.tab_form, fg_color="transparent")
        f_header.pack(fill="x", padx=20, pady=10)
        
        self.ent_name = ctk.CTkEntry(f_header, placeholder_text="Nombre", width=400)
        self.ent_name.pack(side="left", padx=5)
        self.ent_age = ctk.CTkEntry(f_header, placeholder_text="Edad", width=100)
        self.ent_age.pack(side="left", padx=5)
        self.ent_date = ctk.CTkEntry(f_header, width=150)
        self.ent_date.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.ent_date.pack(side="right", padx=5)

        ctk.CTkLabel(self.tab_form, text="Medicamentos").pack(anchor="w", padx=25)
        self.txt_meds = ctk.CTkTextbox(self.tab_form, height=250)
        self.txt_meds.pack(fill="x", padx=20, pady=5)

        self.txt_notes = ctk.CTkTextbox(self.tab_form, height=100)
        self.txt_notes.pack(fill="x", padx=20, pady=5)

        btn_f = ctk.CTkFrame(self.tab_form, fg_color="transparent")
        btn_f.pack(pady=10)
        ctk.CTkButton(btn_f, text="Guardar", command=self.save_patient).pack(side="left", padx=5)
        ctk.CTkButton(btn_f, text="PDF Receta", command=self.generate_patient_pdf).pack(side="left", padx=5)

        # --- Pestaña Imagenes ---
        img_bar = ctk.CTkFrame(self.tab_images, fg_color="transparent")
        img_bar.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(img_bar, text="Abrir Camara", command=self.open_camera_portal).pack(side="right")

        self.img_grid = ctk.CTkFrame(self.tab_images)
        self.img_grid.pack(fill="both", expand=True, padx=20)
        
        self.image_labels = []
        for i in range(9):
            r, c = divmod(i, 3)
            slot = ctk.CTkFrame(self.img_grid, border_width=1)
            slot.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
            lbl = ctk.CTkLabel(slot, text="Vacio")
            lbl.pack(expand=True)
            self.image_labels.append(lbl)
            ctk.CTkButton(slot, text="+", width=40, command=lambda idx=i: self.add_image(idx)).pack(pady=2)

        self.img_grid.grid_columnconfigure((0,1,2), weight=1)
        self.img_grid.grid_rowconfigure((0,1,2), weight=1)

        self.txt_img_desc = ctk.CTkTextbox(self.tab_images, height=80)
        self.txt_img_desc.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(self.tab_images, text="PDF Imagenes", command=self.generate_image_pdf).pack(pady=5)

        # --- Pestaña Historial ---
        self.tree = ttk.Treeview(self.tab_records, columns=("ID", "Nombre", "Fecha"), show="headings")
        self.tree.heading("ID", text="ID"); self.tree.heading("Nombre", text="Nombre"); self.tree.heading("Fecha", text="Fecha")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(self.tab_records, text="Cargar", command=self.load_selected).pack(pady=10)

    def open_camera_portal(self):
        path = resource_path("camera.html")
        if os.path.exists(path):
            webbrowser.open(f"file:///{path}")

    def add_image(self, idx):
        path = filedialog.askopenfilename(initialdir=os.path.expanduser("~/Downloads"))
        if path:
            fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.path.basename(path)}"
            dest = os.path.join(MEDIA_FOLDER, fname)
            shutil.copy2(path, dest)
            self.image_paths[idx] = fname
            self.update_thumbnail(idx, dest)

    def update_thumbnail(self, idx, path):
        img = Image.open(path)
        img.thumbnail((150, 150))
        photo = ImageTk.PhotoImage(img)
        self.image_labels[idx].configure(image=photo, text="")
        self.image_labels[idx].image = photo

    def save_patient(self):
        name = self.ent_name.get()
        if not name: return
        data = (name, self.ent_age.get(), self.ent_date.get(), self.txt_meds.get("1.0", "end-1c"), 
                self.txt_notes.get("1.0", "end-1c"), json.dumps(self.image_paths), self.txt_img_desc.get("1.0", "end-1c"))
        with sqlite3.connect(DB_NAME) as conn:
            if self.current_patient_id:
                conn.execute("UPDATE patients SET name=?, age=?, date=?, meds=?, notes=?, images=?, image_desc=? WHERE id=?", (*data, self.current_patient_id))
            else:
                cursor = conn.execute("INSERT INTO patients (name, age, date, meds, notes, images, image_desc) VALUES (?,?,?,?,?,?,?)", data)
                self.current_patient_id = cursor.lastrowid
        self.refresh_records_table()

    def load_selected(self):
        sel = self.tree.selection()
        if not sel: return
        p_id = self.tree.item(sel[0])['values'][0]
        with sqlite3.connect(DB_NAME) as conn:
            row = conn.execute("SELECT * FROM patients WHERE id=?", (p_id,)).fetchone()
        if row:
            self.current_patient_id = row[0]
            self.ent_name.delete(0, "end"); self.ent_name.insert(0, row[1])
            self.ent_age.delete(0, "end"); self.ent_age.insert(0, row[2])
            self.txt_meds.delete("1.0", "end"); self.txt_meds.insert("1.0", row[4])
            self.image_paths = json.loads(row[6])
            self.tabs.set("Nuevo Paciente")

    def generate_patient_pdf(self):
        fn = f"Receta_{self.ent_name.get()}.pdf"
        c = canvas.Canvas(fn, pagesize=letter)
        c.setFont("Helvetica", 9)
        y = letter[1] - TOP_MARGIN_PTS
        c.drawString(50, y, f"Paciente: {self.ent_name.get()}")
        c.drawRightString(letter[0]-50, y, f"Fecha: {self.ent_date.get()}")
        y -= 30
        for line in self.txt_meds.get("1.0", "end-1c").split('\n'):
            c.drawString(50, y, line); y -= 12
        c.save(); os.startfile(fn)

    def generate_image_pdf(self):
        fn = f"Reporte_Fotos_{self.ent_name.get()}.pdf"
        c = canvas.Canvas(fn, pagesize=letter)
        c.setFont("Helvetica", 9)
        y = letter[1] - TOP_MARGIN_PTS
        c.drawString(50, y, f"Paciente: {self.ent_name.get()}")
        y_grid = y - 150
        for i, fimg in enumerate(self.image_paths):
            if fimg:
                fp = os.path.join(MEDIA_FOLDER, fimg)
                if os.path.exists(fp):
                    r, col = divmod(i, 3)
                    c.drawImage(fp, 50+(col*180), y_grid-(r*160), width=160, height=140, preserveAspectRatio=True)
        c.save(); os.startfile(fn)

    def refresh_records_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        with sqlite3.connect(DB_NAME) as conn:
            for r in conn.execute("SELECT id, name, date FROM patients").fetchall():
                self.tree.insert("", "end", values=r)

if __name__ == "__main__":
    root = ctk.CTk()
    app = MedicalApp(root)
    root.mainloop()