"""gui/panels/file_panes.py - ローカル・リモートペイン"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from gui.styles import (
    BG_PANEL, BG_ITEM, TEXT_MAIN, TEXT_SUB, BORDER, ACCENT
)


def _fmt_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024**2:.1f} MB"
    else:
        return f"{size_bytes / 1024**3:.2f} GB"


def _fmt_size_str(s):
    try:
        return _fmt_size(int(s))
    except Exception:
        return s


def build_local_pane(app, parent):
    """
    ローカルペインをビルドして parent にgrid(row=0, col=0)。
    app に local_tree, local_path_var を追加。
    """
    frame = ttk.Frame(parent, style="Panel.TFrame")
    frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=4)
    frame.rowconfigure(2, weight=1)
    frame.columnconfigure(0, weight=1)

    # ヘッダー
    hdr = ttk.Frame(frame, style="Panel.TFrame")
    hdr.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
    ttk.Label(hdr, text="💻  ローカル", style="Header.TLabel").pack(side="left")
    ttk.Button(hdr, text="参照", style="Small.TButton",
               command=app._browse_local_dir).pack(side="right")

    app.local_path_var = tk.StringVar(value=os.path.expanduser("~"))
    tk.Label(frame, textvariable=app.local_path_var,
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8), anchor="w",
             wraplength=400).grid(row=1, column=0, sticky="ew", padx=10)

    # ツリービュー
    tree_frame = ttk.Frame(frame, style="Panel.TFrame")
    tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(4, 8))
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    app.local_tree = ttk.Treeview(tree_frame,
        columns=("name", "size", "type"),
        show="headings", selectmode="extended")
    app.local_tree.heading("name", text="名前")
    app.local_tree.heading("size", text="サイズ")
    app.local_tree.heading("type", text="種別")
    app.local_tree.column("name", width=200)
    app.local_tree.column("size", width=80, anchor="e")
    app.local_tree.column("type", width=60, anchor="center")

    sb = ttk.Scrollbar(tree_frame, orient="vertical",
                       command=app.local_tree.yview)
    app.local_tree.configure(yscrollcommand=sb.set)
    app.local_tree.grid(row=0, column=0, sticky="nsew")
    sb.grid(row=0, column=1, sticky="ns")

    app.local_tree.bind("<Double-1>", app._local_double_click)
    app._refresh_local()


def build_remote_pane(app, parent):
    """
    リモートペインをビルドして parent にgrid(row=0, col=1)。
    app に remote_tree, remote_path_var を追加。
    """
    frame = ttk.Frame(parent, style="Panel.TFrame")
    frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=4)
    frame.rowconfigure(2, weight=1)
    frame.columnconfigure(0, weight=1)

    hdr = ttk.Frame(frame, style="Panel.TFrame")
    hdr.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
    ttk.Label(hdr, text="🌐  リモート", style="Header.TLabel").pack(side="left")
    ttk.Button(hdr, text="更新", style="Small.TButton",
               command=app._refresh_remote).pack(side="right")
    ttk.Button(hdr, text="↑ 上へ", style="Small.TButton",
               command=app._remote_up).pack(side="right", padx=4)

    app.remote_path_var = tk.StringVar(value="/")
    tk.Label(frame, textvariable=app.remote_path_var,
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8), anchor="w").grid(
                 row=1, column=0, sticky="ew", padx=10)

    tree_frame = ttk.Frame(frame, style="Panel.TFrame")
    tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(4, 8))
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    app.remote_tree = ttk.Treeview(tree_frame,
        columns=("name", "size", "type"),
        show="headings", selectmode="extended")
    app.remote_tree.heading("name", text="名前")
    app.remote_tree.heading("size", text="サイズ")
    app.remote_tree.heading("type", text="種別")
    app.remote_tree.column("name", width=200)
    app.remote_tree.column("size", width=80, anchor="e")
    app.remote_tree.column("type", width=60, anchor="center")

    sb2 = ttk.Scrollbar(tree_frame, orient="vertical",
                        command=app.remote_tree.yview)
    app.remote_tree.configure(yscrollcommand=sb2.set)
    app.remote_tree.grid(row=0, column=0, sticky="nsew")
    sb2.grid(row=0, column=1, sticky="ns")

    app.remote_tree.bind("<Double-1>", app._remote_double_click)


# ──────────────────────────────
# ローカル操作ロジック（Appメソッドとして追加）
# ──────────────────────────────

def refresh_local(app, path=None):
    if path:
        app.local_path_var.set(path)
    path = app.local_path_var.get()
    app.local_tree.delete(*app.local_tree.get_children())
    try:
        entries = sorted(os.listdir(path),
                         key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        if os.path.dirname(path) != path:
            app.local_tree.insert("", "end", iid="..",
                values=("..", "", "📁"), tags=("dir",))
        for name in entries:
            full = os.path.join(path, name)
            if os.path.isdir(full):
                app.local_tree.insert("", "end",
                    values=(name, "", "📁"), tags=("dir",))
            else:
                size = os.path.getsize(full)
                app.local_tree.insert("", "end",
                    values=(name, _fmt_size(size), "📄"))
    except Exception as e:
        app._log(f"ローカル読込エラー: {e}", "err")


def browse_local_dir(app):
    d = filedialog.askdirectory(initialdir=app.local_path_var.get())
    if d:
        refresh_local(app, d)


def local_double_click(app, event):
    sel = app.local_tree.selection()
    if not sel:
        return
    name = app.local_tree.item(sel[0], "values")[0]
    cur  = app.local_path_var.get()
    new  = os.path.dirname(cur) if name == ".." else os.path.join(cur, name)
    if os.path.isdir(new):
        refresh_local(app, new)


# ──────────────────────────────
# リモート操作ロジック
# ──────────────────────────────

def refresh_remote(app):
    if not app.ftp.connected:
        return
    app.remote_tree.delete(*app.remote_tree.get_children())

    def worker():
        try:
            items = app.ftp.list_dir(app.remote_path)
            def update():
                if app.remote_path not in ("/", ""):
                    app.remote_tree.insert("", "end", iid="..",
                        values=("..", "", "📁"), tags=("dir",))
                for item in sorted(items,
                        key=lambda x: (not x["is_dir"], x["name"].lower())):
                    icon = "📁" if item["is_dir"] else "📄"
                    sz   = "" if item["is_dir"] else _fmt_size_str(item["size"])
                    app.remote_tree.insert("", "end",
                        values=(item["name"], sz, icon),
                        tags=("dir",) if item["is_dir"] else ())
            app.after(0, update)
        except Exception as e:
            app.after(0, lambda e=e: app._log(f"リモート読込エラー: {e}", "err"))

    threading.Thread(target=worker, daemon=True).start()


def remote_double_click(app, event):
    if not app.ftp.connected:
        return
    sel = app.remote_tree.selection()
    if not sel:
        return
    vals = app.remote_tree.item(sel[0], "values")
    name, _, icon = vals
    if icon != "📁":
        return

    if name == "..":
        parent = os.path.dirname(app.remote_path.rstrip("/"))
        new_path = parent if parent else "/"
    else:
        new_path = app.remote_path.rstrip("/") + "/" + name

    def worker():
        try:
            app.ftp.cwd(new_path)
            app.remote_path = app.ftp.pwd()
            app.after(0, lambda: app.remote_path_var.set(app.remote_path))
            app.after(0, app._refresh_remote)
        except Exception as e:
            app.after(0, lambda e=e: app._log(f"ディレクトリ移動エラー: {e}", "err"))

    threading.Thread(target=worker, daemon=True).start()


def remote_up(app):
    if not app.ftp.connected:
        return
    parent = os.path.dirname(app.remote_path.rstrip("/"))
    new_path = parent if parent else "/"

    def worker():
        try:
            app.ftp.cwd(new_path)
            app.remote_path = app.ftp.pwd()
            app.after(0, lambda: app.remote_path_var.set(app.remote_path))
            app.after(0, app._refresh_remote)
        except Exception as e:
            app.after(0, lambda e=e: app._log(f"移動エラー: {e}", "err"))

    threading.Thread(target=worker, daemon=True).start()
