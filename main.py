import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
from datetime import datetime

# ---------------- CONFIG ----------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',          # change if needed
    'password': 'ankudata',     # change to your MySQL password
    'database': 'cu_complaints'
}

APP_TITLE = "Chandigarh University - Complaint Management System"
CU_RED = "#B22234"
BG = "#FFFFFF"
FONT = ("Helvetica", 11)


# ---------------- DATABASE CLASS (robust) ----------------
class DB:
    def __init__(self, cfg):
        self.cfg = cfg.copy()
        temp = cfg.copy()
        temp.pop("database", None)

        # Ensure database exists
        try:
            conn = mysql.connector.connect(**temp)
            cur = conn.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}`")
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print("Warning: could not create database (check server):", e)

        # Connect to the target database
        try:
            self.conn = mysql.connector.connect(**self.cfg)
        except Error as e:
            raise RuntimeError(f"Could not connect to MySQL: {e}")

        # Ensure table & columns and insert sample data if empty
        self.ensure_table()
        self.ensure_columns()
        self.insert_dummy_data()

    def ensure_table(self):
        """Create base table if not exists (keeps minimal columns; ensure_columns will add others)."""
        sql = """
        CREATE TABLE IF NOT EXISTS complaints (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            gender VARCHAR(20) NOT NULL,
            complain TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
        """
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()
        cur.close()

    def ensure_columns(self):
        """Add any missing columns required by the app."""
        required = {
            'complaint_type': "VARCHAR(120) NOT NULL DEFAULT 'Other'",
            'priority': "VARCHAR(20) NOT NULL DEFAULT 'Medium'",
            'status': "VARCHAR(20) NOT NULL DEFAULT 'Pending'",
            'complain': "TEXT NOT NULL"
        }

        cur = self.conn.cursor()
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'complaints'
        """, (self.cfg['database'],))
        existing = {row[0] for row in cur.fetchall()}

        for col, definition in required.items():
            if col not in existing:
                try:
                    cur.execute(f"ALTER TABLE complaints ADD COLUMN `{col}` {definition}")
                    self.conn.commit()
                    print(f"Added missing column: {col}")
                except Exception as e:
                    print(f"Failed to add column {col}: {e}")
        cur.close()

    def insert_dummy_data(self):
        """Insert sample rows only when the table is empty."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM complaints")
        count = cur.fetchone()[0]

        if count == 0:
            dummy_rows = [
                ("Aman Sharma", "Male", "Hostel Issue", "Medium", "Bathroom not cleaned from two days."),
                ("Priya Verma", "Female", "Academic Issue", "High", "Faculty not covering syllabus properly."),
                ("Rohit Mehta", "Male", "Mess Issue", "Low", "Food quality is average, need improvement."),
                ("Simran Kaur", "Female", "Faculty Behaviour", "High", "Faculty humiliates students during class."),
                ("Kunal Bansal", "Male", "Transport", "Medium", "Bus arrived 45 minutes late."),
                ("Sneha Patel", "Female", "Technical / IT Issue", "High", "LMS not working, cannot submit assignment."),
                ("Harsh Raj", "Male", "Fee / Accounts", "Medium", "Wrong amount shown in fee portal."),
                ("Jaspreet Singh", "Male", "Mess Issue", "High", "Found insects in food."),
                ("Ritika Sharma", "Female", "Hostel Issue", "High", "AC not working from last week."),
                ("Rohit Saini", "Male", "Academic Issue", "Low", "Need extra lab session."),
                ("Aditya Jain", "Male", "Faculty Behaviour", "Medium", "Faculty ignores doubts in class."),
                ("Megha Tiwari", "Female", "Technical / IT Issue", "Medium", "WiFi disconnecting frequently."),
                ("Yash Gupta", "Male", "Transport", "Low", "Route change request."),
                ("Divya Agarwal", "Female", "Fee / Accounts", "High", "Refund not received yet."),
                ("Mohit Kumar", "Male", "Hostel Issue", "Low", "Water cooler not functioning."),
                ("Tanisha Kaur", "Female", "Mess Issue", "Medium", "Rice served was stale."),
                ("Saurabh Singh", "Male", "Academic Issue", "Medium", "Requesting notes of previous lecture."),
                ("Nisha Sharma", "Female", "Other", "Urgent", "Lost ID card inside campus.")
            ]

            # Make sure target columns exist before inserting
            cur2 = self.conn.cursor()
            cur2.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'complaints'
            """, (self.cfg['database'],))
            cols = [r[0] for r in cur2.fetchall()]

            needed_cols = ['full_name', 'gender', 'complaint_type', 'priority', 'status', 'complain']
            use_cols = [c for c in needed_cols if c in cols]

            placeholders = ", ".join(["%s"] * len(use_cols))
            col_list_sql = ", ".join(f"`{c}`" for c in use_cols)
            insert_sql = f"INSERT INTO complaints ({col_list_sql}) VALUES ({placeholders})"

            adapted = []
            for dr in dummy_rows:
                mapping = {
                    'full_name': dr[0],
                    'gender': dr[1],
                    'complaint_type': dr[2],
                    'priority': dr[3],
                    'complain': dr[4],
                    'status': 'Pending'
                }
                adapted.append(tuple(mapping[c] for c in use_cols))

            cur2.executemany(insert_sql, adapted)
            self.conn.commit()
            cur2.close()
        cur.close()

    def add(self, full_name, gender, ctype, priority, complain):
        q = "INSERT INTO complaints (full_name, gender, complaint_type, priority, complain) VALUES (%s,%s,%s,%s,%s)"
        cur = self.conn.cursor()
        cur.execute(q, (full_name, gender, ctype, priority, complain))
        self.conn.commit()
        last_id = cur.lastrowid
        cur.close()
        return last_id

    def fetch(self, search=None):
        cur = self.conn.cursor(dictionary=True)
        if search:
            cur.execute("SELECT * FROM complaints WHERE full_name LIKE %s ORDER BY created_at DESC", (f"%{search}%",))
        else:
            cur.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        return rows

    def delete(self, cid):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM complaints WHERE id=%s", (cid,))
        self.conn.commit()
        cur.close()

    def update(self, cid, name, gender, ctype, priority, complain):
        cur = self.conn.cursor()
        cur.execute("UPDATE complaints SET full_name=%s, gender=%s, complaint_type=%s, priority=%s, complain=%s WHERE id=%s",
                    (name, gender, ctype, priority, complain, cid))
        self.conn.commit()
        cur.close()


# ---------------- EDIT WINDOW ----------------
class EditWindow(tk.Toplevel):
    def __init__(self, parent, db, record, refresh_cb):
        super().__init__(parent)
        self.db = db
        self.record = record
        self.refresh_cb = refresh_cb

        self.title(f"Edit Complaint ID {record.get('id')}")
        self.geometry("520x380")
        self.configure(bg=BG)

        tk.Label(self, text="Full Name:", bg=BG, font=FONT).pack(anchor="w", padx=10, pady=(8, 0))
        self.ent_name = tk.Entry(self, width=50, font=FONT)
        self.ent_name.pack(padx=10)
        self.ent_name.insert(0, record.get("full_name", ""))

        tk.Label(self, text="Gender:", bg=BG, font=FONT).pack(anchor="w", padx=10, pady=(8, 0))
        self.gender_var = tk.StringVar(value=record.get("gender", "Male"))
        gf = tk.Frame(self, bg=BG)
        gf.pack(anchor="w", padx=10)
        tk.Radiobutton(gf, text="Male", variable=self.gender_var, value="Male", bg=BG).pack(side="left")
        tk.Radiobutton(gf, text="Female", variable=self.gender_var, value="Female", bg=BG).pack(side="left")
        tk.Radiobutton(gf, text="Other", variable=self.gender_var, value="Other", bg=BG).pack(side="left")

        tk.Label(self, text="Complaint Type:", bg=BG, font=FONT).pack(anchor="w", padx=10, pady=(8, 0))
        self.type_var = tk.StringVar(value=record.get("complaint_type", "Other"))
        ttk.Combobox(self, textvariable=self.type_var, values=[
            "Hostel Issue", "Mess Issue", "Academic Issue", "Transport",
            "Fee / Accounts", "Faculty Behaviour", "Technical / IT Issue", "Other"
        ], width=45, state="readonly").pack(padx=10)

        tk.Label(self, text="Priority:", bg=BG, font=FONT).pack(anchor="w", padx=10, pady=(8, 0))
        self.pr_var = tk.StringVar(value=record.get("priority", "Medium"))
        ttk.Combobox(self, textvariable=self.pr_var, values=["Low", "Medium", "High", "Urgent"], width=20,
                     state="readonly").pack(padx=10)

        tk.Label(self, text="Complain:", bg=BG, font=FONT).pack(anchor="w", padx=10, pady=(8, 0))
        self.txt = tk.Text(self, width=62, height=6, font=FONT)
        self.txt.pack(padx=10)
        self.txt.insert("1.0", record.get("complain", ""))

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Save", bg=CU_RED, fg="white", command=self.save).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left")

    def save(self):
        name = self.ent_name.get().strip()
        gender = self.gender_var.get()
        ctype = self.type_var.get()
        priority = self.pr_var.get()
        complain = self.txt.get("1.0", "end").strip()

        if not name or not complain:
            messagebox.showwarning("Validation", "Name and complain required")
            return

        try:
            self.db.update(self.record["id"], name, gender, ctype, priority, complain)
            messagebox.showinfo("Saved", "Complaint updated successfully")
            self.refresh_cb()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ---------------- MAIN APPLICATION ----------------
class App(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title(APP_TITLE)
        self.geometry("1050x580")
        self.configure(bg=BG)
        self.create_ui()
        self.load_data()

    def create_ui(self):
        header = tk.Frame(self, bg=CU_RED, height=70)
        header.pack(fill="x")

        tk.Label(header, text="Chandigarh University", bg=CU_RED, fg="white",
                 font=("Helvetica", 18, "bold")).pack(side="left", padx=12, pady=12)
        tk.Label(header, text="Student Complaint Management System", bg=CU_RED, fg="white",
                 font=("Helvetica", 13)).pack(side="left", padx=8)

        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="y")

        tk.Label(left, text="Submit Complaint", bg=BG, font=("Helvetica", 14, "bold")).pack(anchor="w")

        tk.Label(left, text="Full Name:", bg=BG, font=FONT).pack(anchor="w", pady=(6, 0))
        self.ent_name = tk.Entry(left, font=FONT, width=36)
        self.ent_name.pack()

        tk.Label(left, text="Gender:", bg=BG, font=FONT).pack(anchor="w", pady=(6, 0))
        self.gender_var = tk.StringVar(value="Male")
        gf = tk.Frame(left, bg=BG)
        gf.pack(anchor="w")
        tk.Radiobutton(gf, text="Male", variable=self.gender_var, value="Male", bg=BG).pack(side="left")
        tk.Radiobutton(gf, text="Female", variable=self.gender_var, value="Female", bg=BG).pack(side="left")
        tk.Radiobutton(gf, text="Other", variable=self.gender_var, value="Other", bg=BG).pack(side="left")

        tk.Label(left, text="Complaint Type:", bg=BG, font=FONT).pack(anchor="w", pady=(6, 0))
        self.type_var = tk.StringVar(value="Academic Issue")
        ttk.Combobox(left, textvariable=self.type_var, width=34, values=[
            "Hostel Issue", "Mess Issue", "Academic Issue", "Transport",
            "Fee / Accounts", "Faculty Behaviour", "Technical / IT Issue", "Other"
        ], state="readonly").pack()

        tk.Label(left, text="Priority:", bg=BG, font=FONT).pack(anchor="w", pady=(6, 0))
        self.pr_var = tk.StringVar(value="Medium")
        ttk.Combobox(left, textvariable=self.pr_var, width=20, values=["Low", "Medium", "High", "Urgent"],
                     state="readonly").pack()

        tk.Label(left, text="Complain:", bg=BG, font=FONT).pack(anchor="w", pady=(6, 0))
        self.txt_complain = tk.Text(left, width=40, height=10, font=FONT)
        self.txt_complain.pack()

        tk.Button(left, text="Submit", bg=CU_RED, fg="white", width=20, command=self.submit).pack(pady=8)

        right = tk.Frame(main, bg=BG)
        right.pack(side="right", fill="both", expand=True)

        top = tk.Frame(right, bg=BG)
        top.pack(fill="x")

        tk.Label(top, text="Search by Name:", bg=BG, font=FONT).pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(top, textvariable=self.search_var, font=FONT, width=30).pack(side="left", padx=8)
        tk.Button(top, text="Search", command=self.load_data).pack(side="left", padx=4)
        tk.Button(top, text="Reset", command=self.reset_search).pack(side="left", padx=4)

        cols = ("ID", "Full Name", "Gender", "Type", "Priority", "Status", "Complain", "Created At")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="w")
        self.tree.column("Complain", width=300)
        self.tree.pack(fill="both", expand=True, pady=8)
        self.tree.bind("<Double-1>", self.edit_selected)

        btns = tk.Frame(right, bg=BG)
        btns.pack(fill="x")
        tk.Button(btns, text="Edit", command=self.edit_selected).pack(side="left")
        tk.Button(btns, text="Delete", command=self.delete_selected).pack(side="left", padx=8)

        self.status = tk.Label(self, text="Ready", bg="lightgrey", anchor="w")
        self.status.pack(side="bottom", fill="x")

    def submit(self):
        name = self.ent_name.get().strip()
        gender = self.gender_var.get()
        ctype = self.type_var.get()
        priority = self.pr_var.get()
        complain = self.txt_complain.get("1.0", "end").strip()

        if not name or not complain or not ctype:
            messagebox.showwarning("Required", "Name, type and complain are required")
            return

        try:
            cid = self.db.add(name, gender, ctype, priority, complain)
            messagebox.showinfo("Submitted", f"Complaint submitted (ID: {cid})")
            self.ent_name.delete(0, "end")
            self.txt_complain.delete("1.0", "end")
            self.load_data()
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def load_data(self):
        search = self.search_var.get().strip()
        try:
            rows = self.db.fetch(search if search else None)
            for i in self.tree.get_children():
                self.tree.delete(i)
            for r in rows:
                created = r.get("created_at")
                if hasattr(created, "strftime"):
                    created = created.strftime("%Y-%m-%d %H:%M:%S")
                self.tree.insert("", "end", values=(
                    r.get("id"),
                    r.get("full_name"),
                    r.get("gender"),
                    r.get("complaint_type"),
                    r.get("priority"),
                    r.get("status"),
                    r.get("complain"),
                    created
                ))
            self.status.config(text=f"Loaded {len(rows)} records")
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def reset_search(self):
        self.search_var.set("")
        self.load_data()

    def edit_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a record to edit")
            return
        vals = self.tree.item(sel[0])["values"]
        rec = {
            "id": vals[0],
            "full_name": vals[1],
            "gender": vals[2],
            "complaint_type": vals[3],
            "priority": vals[4],
            "status": vals[5],
            "complain": vals[6]
        }
        EditWindow(self, self.db, rec, refresh_cb=self.load_data)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a record to delete")
            return
        cid = self.tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirm Delete", f"Delete complaint ID {cid}?"):
            try:
                self.db.delete(cid)
                messagebox.showinfo("Deleted", "Record deleted")
                self.load_data()
            except Exception as e:
                messagebox.showerror("DB Error", str(e))


# ---------------- RUN ----------------
if __name__ == "__main__":
    try:
        db = DB(DB_CONFIG)
    except Exception as e:
        # DB connection problem — show and exit
        try:
            messagebox.showerror("Database Error", str(e))
        except Exception:
            print("Database Error:", e)
        raise SystemExit

    app = App(db)
    app.mainloop()
