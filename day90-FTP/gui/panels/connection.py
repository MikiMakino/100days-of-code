"""gui/panels/connection.py - 接続パネル"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from gui.styles import (
    BG_PANEL, BG_ITEM, TEXT_MAIN, TEXT_SUB, BORDER, ACCENT
)


def build_connection_panel(app, parent):
    """
    接続パネルをビルドして parent にpack。
    app に以下の属性を追加:
        conn_host, conn_port, conn_user, conn_pass (tk.StringVar)
        passive_var (tk.BooleanVar)
        connect_btn (ttk.Button)
    """
    conn = ttk.Frame(parent, style="Panel.TFrame")
    conn.pack(fill="x", padx=12, pady=(8, 4))

    fields = [
        ("ホスト:",    "conn_host", 20, "ftp.example.com"),
        ("ポート:",    "conn_port",  6, "21"),
        ("ユーザー:", "conn_user", 14, "anonymous"),
        ("パスワード:", "conn_pass", 14, ""),
    ]

    col = 0
    for label, attr, width, placeholder in fields:
        tk.Label(conn, text=label, fg=TEXT_SUB, bg=BG_PANEL,
                 font=("Helvetica", 9)).grid(row=0, column=col,
                                             padx=(12, 4), pady=8, sticky="w")
        col += 1
        var = tk.StringVar(value=placeholder if attr != "conn_pass" else "")
        entry = tk.Entry(conn, textvariable=var, width=width,
                         bg=BG_ITEM, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                         relief="flat", font=("Helvetica", 10),
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT,
                         show="*" if attr == "conn_pass" else "")
        entry.grid(row=0, column=col, padx=(0, 8), pady=8)
        setattr(app, attr, var)
        col += 1

    app.passive_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(conn, text="パッシブ", variable=app.passive_var,
                    style="TCheckbutton").grid(row=0, column=col, padx=4)
    col += 1

    app.connect_btn = ttk.Button(conn, text="接続",
                                  style="Accent.TButton",
                                  command=app._toggle_connect)
    app.connect_btn.grid(row=0, column=col, padx=(8, 4), pady=8)
    col += 1

    ttk.Button(conn, text="💾 保存",
               style="Small.TButton",
               command=app._save_profile).grid(row=0, column=col,
                                               padx=(0, 12), pady=8)
