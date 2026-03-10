"""gui/panels/log_panel.py - プログレスバー・ログ"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from gui.styles import (
    BG_PANEL, BG_DARK, TEXT_MAIN, TEXT_SUB,
    ACCENT, SUCCESS, ERROR, WARNING
)


def build_log_panel(app, parent):
    """
    プログレス＋ログパネルをビルドして parent にpack。
    app に以下の属性を追加:
        progress_var (tk.DoubleVar)
        progressbar  (ttk.Progressbar)
        progress_label (tk.Label)
        cancel_btn   (ttk.Button)
        log_text     (tk.Text)
    また app._log / app._set_progress メソッドを追加。
    """
    bottom = ttk.Frame(parent, style="Panel.TFrame")
    bottom.pack(fill="x", padx=12, pady=(4, 10))

    # ── プログレス行 ──
    prog_row = ttk.Frame(bottom, style="Panel.TFrame")
    prog_row.pack(fill="x", padx=10, pady=(8, 4))

    app.progress_label = tk.Label(prog_row, text="待機中",
                                   fg=TEXT_SUB, bg=BG_PANEL,
                                   font=("Helvetica", 9))
    app.progress_label.pack(side="left")

    app.cancel_btn = ttk.Button(prog_row, text="キャンセル",
                                 style="Small.TButton",
                                 command=app._cancel_transfer)
    app.cancel_btn.pack(side="right")
    app.cancel_btn.state(["disabled"])

    app.progress_var = tk.DoubleVar()
    app.progressbar = ttk.Progressbar(bottom, variable=app.progress_var,
                                       maximum=100, style="TProgressbar")
    app.progressbar.pack(fill="x", padx=10, pady=(0, 6))

    # ── ログ ──
    log_hdr = ttk.Frame(bottom, style="Panel.TFrame")
    log_hdr.pack(fill="x", padx=10)
    tk.Label(log_hdr, text="ログ", fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8, "bold")).pack(side="left")
    ttk.Button(log_hdr, text="クリア", style="Small.TButton",
               command=lambda: app.log_text.delete("1.0", "end")
               ).pack(side="right")

    app.log_text = tk.Text(bottom, height=5, bg=BG_DARK,
                            fg=TEXT_SUB, font=("Courier", 8),
                            relief="flat", state="disabled",
                            insertbackground=TEXT_MAIN)
    app.log_text.pack(fill="x", padx=10, pady=(4, 8))

    app.log_text.tag_configure("ok",   foreground=SUCCESS)
    app.log_text.tag_configure("err",  foreground=ERROR)
    app.log_text.tag_configure("info", foreground=ACCENT)
    app.log_text.tag_configure("warn", foreground=WARNING)

    # メソッドをappにバインド
    app._log = _make_log(app)
    app._set_progress = _make_set_progress(app)


def _make_log(app):
    def _log(msg, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        app.log_text.configure(state="normal")
        app.log_text.insert("end", f"[{ts}] {msg}\n", tag)
        app.log_text.see("end")
        app.log_text.configure(state="disabled")
    return _log


def _make_set_progress(app):
    def _set_progress(pct, label=""):
        app.progress_var.set(pct)
        if label:
            app.progress_label.configure(text=label)
    return _set_progress
