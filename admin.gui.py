import tkinter as tk
from tkinter import ttk
import sqlite3, subprocess, os
from datetime import datetime

DB = "transport.db"

class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transport-Admin")
        self.geometry("1000x600")
        self.configure(bg="#1f1f1f")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="#fff", fieldbackground="#2b2b2b")
        style.map("Treeview", background=[("selected", "#c53030")])
        self.build_ui()
        self.load_termine()

    def build_ui(self):
        cols = ("ID", "Name", "Tel", "Mail", "Datum", "Zeit", "Strecke", "Preis")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)

        btn_frame = tk.Frame(self, bg="#1f1f1f")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Rechnung erstellen", bg="#f6ad55", fg="#000", command=self.create_invoice).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Refresh", bg="#c53030", fg="#fff", command=self.load_termine).pack(side="left", padx=5)

    def load_termine(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        rows = c.execute("""SELECT t.id,k.name,k.tel,k.mail,t.datum,t.zeit,t.abfahrt||'→'||t.ziel,t.preis
                            FROM termine t JOIN kunden k ON t.kunde_id = k.id""").fetchall()
        for r in rows:
            self.tree.insert("", "end", values=r)
        conn.close()

    def create_invoice(self):
        selected = self.tree.focus()
        if not selected:
            return
        tid = self.tree.item(selected)["values"][0]
        subprocess.Popen(["start", "", f"http://localhost:5000/api/rechnung/{tid}"], shell=True)

if __name__ == "__main__":
    AdminApp().mainloop()