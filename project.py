"""
library_system.py
A simple Library Management System with Tkinter frontend and MySQL backend.

Features:
- Add book
- Update selected book
- Delete selected book
- Search books by Title / Author / ISBN
- List all books in a Treeview
- Auto-create database & table if not exist

Before running:
- Ensure MySQL server is running locally
- Install dependency: pip install mysql-connector-python
- If your MySQL credentials differ, edit DB_CONFIG below
"""

import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import errorcode

# ----------------------- CONFIG -----------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "ankudata",     # change if your local MySQL has a password
    "database": "library_db"
}
# ------------------------------------------------------

TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    publisher VARCHAR(255),
    year INT,
    isbn VARCHAR(50),
    quantity INT DEFAULT 1
) ENGINE=InnoDB;
"""

class LibraryDB:
    def __init__(self, cfg):
        self.cfg = cfg.copy()
        self._ensure_database()

    def _connect_server(self, use_db=False):
        cfg = self.cfg.copy()
        if not use_db:
            cfg.pop("database", None)
        return mysql.connector.connect(**cfg)

    def _ensure_database(self):
        # Connect without database: create if doesn't exist
        try:
            conn = self._connect_server(use_db=False)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.cfg['database']}` DEFAULT CHARACTER SET 'utf8mb4'")
            conn.commit()
            cursor.close()
            conn.close()
            # Now create table
            conn = self._connect_server(use_db=True)
            cursor = conn.cursor()
            cursor.execute(TABLE_SCHEMA)
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            msg = f"Database error: {err}"
            raise RuntimeError(msg)

    def execute(self, query, params=None, commit=False, fetch=False):
        conn = None
        try:
            conn = self._connect_server(use_db=True)
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            if commit:
                conn.commit()
            if fetch:
                result = cursor.fetchall()
                cursor.close()
                conn.close()
                return result
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            if conn:
                conn.close()
            raise

    # CRUD helpers
    def add_book(self, title, author, publisher, year, isbn, quantity):
        q = """INSERT INTO books (title, author, publisher, year, isbn, quantity)
               VALUES (%s, %s, %s, %s, %s, %s)"""
        self.execute(q, (title, author, publisher or None, year or None, isbn or None, quantity or 0), commit=True)

    def update_book(self, book_id, title, author, publisher, year, isbn, quantity):
        q = """UPDATE books SET title=%s, author=%s, publisher=%s, year=%s, isbn=%s, quantity=%s WHERE id=%s"""
        self.execute(q, (title, author, publisher or None, year or None, isbn or None, quantity or 0, book_id), commit=True)

    def delete_book(self, book_id):
        q = "DELETE FROM books WHERE id=%s"
        self.execute(q, (book_id,), commit=True)

    def fetch_all(self):
        q = "SELECT id, title, author, publisher, year, isbn, quantity FROM books ORDER BY id DESC"
        return self.execute(q, fetch=True)

    def search(self, field, text):
        # field is 'title' or 'author' or 'isbn'
        q = f"SELECT id, title, author, publisher, year, isbn, quantity FROM books WHERE {field} LIKE %s ORDER BY id DESC"
        return self.execute(q, (f"%{text}%",), fetch=True)


class LibraryApp:
    def __init__(self, root, db: LibraryDB):
        self.db = db
        self.root = root
        self.root.title("Library Management System")
        self.root.geometry("900x600")
        self.create_widgets()
        self.selected_book_id = None
        self.refresh_books()

    def create_widgets(self):
        padx = 6
        pady = 6

        # --- Form frame ---
        form = tk.LabelFrame(self.root, text="Book Details", padx=10, pady=10)
        form.pack(fill=tk.X, padx=12, pady=8)

        # Title
        tk.Label(form, text="Title *").grid(row=0, column=0, sticky=tk.W, padx=padx, pady=pady)
        self.title_var = tk.StringVar()
        tk.Entry(form, textvariable=self.title_var, width=40).grid(row=0, column=1, padx=padx, pady=pady)

        # Author
        tk.Label(form, text="Author *").grid(row=0, column=2, sticky=tk.W, padx=padx, pady=pady)
        self.author_var = tk.StringVar()
        tk.Entry(form, textvariable=self.author_var, width=30).grid(row=0, column=3, padx=padx, pady=pady)

        # Publisher
        tk.Label(form, text="Publisher").grid(row=1, column=0, sticky=tk.W, padx=padx, pady=pady)
        self.publisher_var = tk.StringVar()
        tk.Entry(form, textvariable=self.publisher_var, width=40).grid(row=1, column=1, padx=padx, pady=pady)

        # Year
        tk.Label(form, text="Year").grid(row=1, column=2, sticky=tk.W, padx=padx, pady=pady)
        self.year_var = tk.StringVar()
        tk.Entry(form, textvariable=self.year_var, width=10).grid(row=1, column=3, padx=padx, pady=pady, sticky=tk.W)

        # ISBN
        tk.Label(form, text="ISBN").grid(row=2, column=0, sticky=tk.W, padx=padx, pady=pady)
        self.isbn_var = tk.StringVar()
        tk.Entry(form, textvariable=self.isbn_var, width=30).grid(row=2, column=1, padx=padx, pady=pady)

        # Quantity
        tk.Label(form, text="Quantity").grid(row=2, column=2, sticky=tk.W, padx=padx, pady=pady)
        self.quantity_var = tk.StringVar(value="1")
        tk.Entry(form, textvariable=self.quantity_var, width=10).grid(row=2, column=3, padx=padx, pady=pady, sticky=tk.W)

        # Buttons
        btn_frame = tk.Frame(form)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=(8, 0))
        tk.Button(btn_frame, text="Add Book", width=12, command=self.add_book).grid(row=0, column=0, padx=6)
        tk.Button(btn_frame, text="Update Book", width=12, command=self.update_book).grid(row=0, column=1, padx=6)
        tk.Button(btn_frame, text="Delete Book", width=12, command=self.delete_book).grid(row=0, column=2, padx=6)
        tk.Button(btn_frame, text="Clear Fields", width=12, command=self.clear_fields).grid(row=0, column=3, padx=6)

        # --- Search frame ---
        search_frame = tk.LabelFrame(self.root, text="Search", padx=10, pady=6)
        search_frame.pack(fill=tk.X, padx=12, pady=6)

        tk.Label(search_frame, text="Search by").grid(row=0, column=0, padx=6, pady=6)
        self.search_field = tk.StringVar(value="title")
        self.search_cb = ttk.Combobox(search_frame, textvariable=self.search_field, state="readonly", values=["title", "author", "isbn"], width=12)
        self.search_cb.grid(row=0, column=1, padx=6, pady=6)

        self.search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.search_var, width=40).grid(row=0, column=2, padx=6, pady=6)
        tk.Button(search_frame, text="Search", width=12, command=self.search_books).grid(row=0, column=3, padx=6)
        tk.Button(search_frame, text="Show All", width=12, command=self.refresh_books).grid(row=0, column=4, padx=6)

        # --- Treeview frame ---
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        columns = ("id", "title", "author", "publisher", "year", "isbn", "quantity")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col.title())
            # set width
            if col == "title":
                self.tree.column(col, width=280, anchor=tk.W)
            elif col == "author":
                self.tree.column(col, width=160, anchor=tk.W)
            else:
                self.tree.column(col, width=100, anchor=tk.W)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Status bar
        self.status_var = tk.StringVar(value="Welcome to Library Management System")
        status = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def set_status(self, text):
        self.status_var.set(text)

    def clear_fields(self):
        self.selected_book_id = None
        self.title_var.set("")
        self.author_var.set("")
        self.publisher_var.set("")
        self.year_var.set("")
        self.isbn_var.set("")
        self.quantity_var.set("1")
        self.set_status("Cleared fields")

    def validate_book_fields(self, for_update=False):
        title = self.title_var.get().strip()
        author = self.author_var.get().strip()
        if not title or not author:
            messagebox.showwarning("Validation error", "Title and Author are required fields.")
            return None
        # year -> int or None
        year = self.year_var.get().strip()
        if year:
            try:
                year_val = int(year)
            except ValueError:
                messagebox.showwarning("Validation error", "Year must be an integer.")
                return None
        else:
            year_val = None
        # quantity
        qty = self.quantity_var.get().strip()
        try:
            qty_val = int(qty) if qty else 0
            if qty_val < 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("Validation error", "Quantity must be a non-negative integer.")
            return None
        return {
            "title": title,
            "author": author,
            "publisher": self.publisher_var.get().strip(),
            "year": year_val,
            "isbn": self.isbn_var.get().strip(),
            "quantity": qty_val
        }

    def add_book(self):
        data = self.validate_book_fields()
        if not data:
            return
        try:
            self.db.add_book(data["title"], data["author"], data["publisher"], data["year"], data["isbn"], data["quantity"])
            messagebox.showinfo("Success", "Book added successfully.")
            self.clear_fields()
            self.refresh_books()
        except Exception as e:
            messagebox.showerror("DB Error", f"Failed to add book: {e}")

    def update_book(self):
        if not self.selected_book_id:
            messagebox.showwarning("No selection", "Select a book from the list to update.")
            return
        data = self.validate_book_fields(for_update=True)
        if not data:
            return
        try:
            self.db.update_book(self.selected_book_id, data["title"], data["author"], data["publisher"], data["year"], data["isbn"], data["quantity"])
            messagebox.showinfo("Success", "Book updated successfully.")
            self.clear_fields()
            self.refresh_books()
        except Exception as e:
            messagebox.showerror("DB Error", f"Failed to update book: {e}")

    def delete_book(self):
        if not self.selected_book_id:
            messagebox.showwarning("No selection", "Select a book from the list to delete.")
            return
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected book?")
        if not confirm:
            return
        try:
            self.db.delete_book(self.selected_book_id)
            messagebox.showinfo("Success", "Book deleted successfully.")
            self.clear_fields()
            self.refresh_books()
        except Exception as e:
            messagebox.showerror("DB Error", f"Failed to delete book: {e}")

    def refresh_books(self):
        try:
            rows = self.db.fetch_all()
            self.populate_tree(rows)
            self.set_status(f"Loaded {len(rows)} books.")
        except Exception as e:
            messagebox.showerror("DB Error", f"Could not fetch books: {e}")
            self.set_status("Error loading books")

    def search_books(self):
        field = self.search_field.get()
        text = self.search_var.get().strip()
        if not text:
            messagebox.showwarning("Input required", "Enter text to search.")
            return
        try:
            rows = self.db.search(field, text)
            self.populate_tree(rows)
            self.set_status(f"Search results: {len(rows)} book(s) found.")
        except Exception as e:
            messagebox.showerror("DB Error", f"Search failed: {e}")

    def populate_tree(self, rows):
        # clear existing
        for r in self.tree.get_children():
            self.tree.delete(r)
        for row in rows:
            # row: (id, title, author, publisher, year, isbn, quantity)
            self.tree.insert("", tk.END, values=row)

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        vals = item["values"]
        if not vals:
            return
        # map values into fields
        self.selected_book_id = vals[0]
        self.title_var.set(vals[1])
        self.author_var.set(vals[2])
        self.publisher_var.set(vals[3] or "")
        self.year_var.set(vals[4] if vals[4] is not None else "")
        self.isbn_var.set(vals[5] or "")
        self.quantity_var.set(vals[6] if vals[6] is not None else "0")
        self.set_status(f"Selected book ID {self.selected_book_id}")

def main():
    # Initialize DB
    try:
        db = LibraryDB(DB_CONFIG)
    except Exception as e:
        messagebox.showerror("DB Initialization Error", f"Could not initialize database: {e}")
        return

    root = tk.Tk()
    app = LibraryApp(root, db)
    root.mainloop()

if __name__ == "__main__":
    main()
