import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import sqlite3
import os
import json
import shutil
import zipfile
from datetime import datetime
from PIL import Image, ImageTk
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Configuration
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
        self.root.title("Medical Form System Pro")
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

        ctk.CTkLabel(self.tab_form, text="Private Notes (Excluded from PDF)").pack(anchor="w", padx=20)
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

        ctk.CTkButton(top_bar, text="Export Data", fg_color="#8e44ad", command=self.export_data).pack(side="right", padx=5)
        ctk.CTkButton(top_bar, text="Import Data", fg_color="#d35400", command=self.import_data).pack(side="right", padx=5)

        self.tree = ttk.Treeview(self.tab_records, columns=("ID", "Name", "Age", "Date"), show="headings")
        for col in ("ID", "Name", "Age", "Date"): self.tree.heading(col, text=col)
        self.tree.column("ID", width=50)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # This is the "Retrieve" button that was broken
        ctk.CTkButton(self.tab_records, text="Retrieve and Load Patient", height=50, fg_color="#27ae60", command=self.load_selected).pack(pady=10)

    # --- FUNCTIONS ---
    def add_image(self, idx):
        path = filedialog.askopenfilename()
        if path:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.path.basename(path)}"
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
        if not name: 
            messagebox.showerror("Error", "Please enter a Name before saving.")
            return
        
        data = (name, self.ent_age.get(), self.ent_date.get(), self.txt_meds.get("1.0", "end-1c"), 
                self.txt_notes.get("1.0", "end-1c"), json.dumps(self.image_paths), self.txt_img_desc.get("1.0", "end-1c"))
        
        with sqlite3.connect(DB_NAME) as conn:
            if self.current_patient_id:
                conn.execute("UPDATE patients SET name=?, age=?, date=?, meds=?, notes=?, images=?, image_desc=? WHERE id=?", (*data, self.current_patient_id))
            else:
                cursor = conn.execute("INSERT INTO patients (name, age, date, meds, notes, images, image_desc) VALUES (?,?,?,?,?,?,?)", data)
                self.current_patient_id = cursor.lastrowid
        
        self.lbl_img_patient.configure(text=f"Current Patient: {name} ({self.ent_age.get()})")
        messagebox.showinfo("Success", "Record and Analysis saved successfully.")
        self.refresh_records_table()

    def load_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Select", "Select a patient from the list first.")
            return

        p_id = self.tree.item(selection[0])['values'][0]
        
        with sqlite3.connect(DB_NAME) as conn:
            row = conn.execute("SELECT * FROM patients WHERE id=?", (p_id,)).fetchone()
        
        if row:
            # Important: Clear everything first to avoid data ghosting
            self.clear_form()
            
            # Row mapping: 0:ID, 1:Name, 2:Age, 3:Date, 4:Meds, 5:Notes, 6:Images, 7:ImageDesc
            self.current_patient_id = row[0]
            self.ent_name.insert(0, str(row[1]))
            self.ent_age.insert(0, str(row[2]))
            self.ent_date.delete(0, "end")
            self.ent_date.insert(0, str(row[3]))
            
            # Note: Medications (row[4]) are NOT loaded as requested
            self.txt_notes.insert("1.0", row[5] if row[5] else "")
            self.txt_img_desc.insert("1.0", row[7] if row[7] else "")
            
            # Update the status label in the Images Tab
            self.lbl_img_patient.configure(text=f"Current Patient: {row[1]} ({row[2]})")
            
            # Load Images
            if row[6]:
                self.image_paths = json.loads(row[6])
                for i, fname in enumerate(self.image_paths):
                    if fname:
                        fpath = os.path.join(MEDIA_FOLDER, fname)
                        if os.path.exists(fpath):
                            self.update_thumbnail(i, fpath)
            
            self.tabs.set("New Patient")
            messagebox.showinfo("Loaded", f"Successfully retrieved record for {row[1]}.")

    def generate_patient_pdf(self):
        filename = f"Record_{self.ent_name.get()}.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        w, h = letter
        y = h - TOP_MARGIN_PTS
        c.setFont("Helvetica", 12)
        c.drawString(50, y, self.ent_name.get())
        c.drawString(450, y, self.ent_age.get())
        c.drawRightString(w - 50, y, self.ent_date.get())
        y -= 40
        c.setFont("Helvetica", 10)
        for line in self.txt_meds.get("1.0", "end-1c").split('\n'):
            if y < 50: c.showPage(); y = h - 50
            c.drawString(50, y, line); y -= 15
        c.save()
        os.startfile(filename)

    def generate_image_pdf(self):
        filename = f"Analysis_{self.ent_name.get()}.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        w, h = letter
        c.setFont("Helvetica", 11)
        c.drawString(50, h-50, f"Patient Name: {self.ent_name.get()}")
        c.drawString(300, h-50, f"Age: {self.ent_age.get()}")
        c.drawRightString(w-50, h-50, f"Date: {self.ent_date.get()}")
        y = h-80
        for line in self.txt_img_desc.get("1.0", "end-1c").split('\n'):
            c.drawString(50, y, line); y -= 15
        y_grid = y - 30
        for i, fname in enumerate(self.image_paths):
            if fname:
                fpath = os.path.join(MEDIA_FOLDER, fname)
                if os.path.exists(fpath):
                    row, col = divmod(i, 3)
                    ix, iy = 50 + (col*185), y_grid - 160 - (row*165)
                    c.drawImage(fpath, ix, iy, width=175, height=155, preserveAspectRatio=True)
        c.save()
        os.startfile(filename)

    def clear_form(self):
        self.current_patient_id = None
        self.ent_name.delete(0, "end")
        self.ent_age.delete(0, "end")
        self.txt_meds.delete("1.0", "end")
        self.txt_notes.delete("1.0", "end")
        self.txt_img_desc.delete("1.0", "end")
        self.lbl_img_patient.configure(text="Current Patient: None Selected")
        self.image_paths = [None] * 9
        for lbl in self.image_labels: lbl.configure(text="Empty", image="")

    def refresh_records_table(self, event=None):
        for i in self.tree.get_children(): self.tree.delete(i)
        with sqlite3.connect(DB_NAME) as conn:
            rows = conn.execute("SELECT id, name, age, date FROM patients WHERE name LIKE ?", (f"%{self.ent_search.get()}%",)).fetchall()
            for r in rows: self.tree.insert("", "end", values=r)

    def export_data(self):
        path = filedialog.asksaveasfilename(defaultextension=".zip")
        if not path: return
        with zipfile.ZipFile(path, 'w') as z:
            z.write(DB_NAME)
            if os.path.exists(MEDIA_FOLDER):
                for f in os.listdir(MEDIA_FOLDER):
                    z.write(os.path.join(MEDIA_FOLDER, f), arcname=os.path.join(MEDIA_FOLDER, f))
        messagebox.showinfo("Export", "All data and images exported to ZIP.")

    def import_data(self):
        path = filedialog.askopenfilename(filetypes=[("Zip", "*.zip")])
        if path and messagebox.askyesno("Confirm", "Importing will overwrite current database. Continue?"):
            with zipfile.ZipFile(path, 'r') as z:
                z.extractall(".")
            self.refresh_records_table()
            messagebox.showinfo("Import", "Data successfully restored.")

if __name__ == "__main__":
    root = ctk.CTk()
    app = MedicalApp(root)
    root.mainloop()