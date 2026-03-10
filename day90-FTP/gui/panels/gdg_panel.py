"""gui/panels/gdg_panel.py - GDG 世代ファイル DL パネル"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from gui.styles import (
    BG_PANEL, BG_ITEM, TEXT_MAIN, TEXT_SUB, BORDER, ACCENT, ACCENT2
)

_Q = "'"  # single-quote helper for f-strings


def _fmt_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024**2:.1f} MB"
    else:
        return f"{size_bytes / 1024**3:.2f} GB"


def build_gdg_panel(app, parent):
    """GDG 世代DLパネルをビルドして parent にpack。"""
    frame = ttk.Frame(parent, style="Panel.TFrame")
    frame.pack(fill="x", padx=12, pady=(0, 4))

    left = ttk.Frame(frame, style="Panel.TFrame")
    left.pack(side="left", padx=(14, 0), pady=8)
    tk.Label(left, text="🗂  GDG 世代DL",
             fg=ACCENT2, bg=BG_PANEL,
             font=("Helvetica", 10, "bold")).pack(anchor="w")
    tk.Label(left, text="データセット名を入力 → (0) を付けてDL",
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).pack(anchor="w")

    mid = ttk.Frame(frame, style="Panel.TFrame")
    mid.pack(side="left", padx=16, pady=8)

    tk.Label(mid, text="データセット名",
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).grid(row=0, column=0, columnspan=3, sticky="w")

    app.gdg_dsn_var = tk.StringVar(value="")
    tk.Entry(mid, textvariable=app.gdg_dsn_var, width=36,
             bg=BG_ITEM, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
             relief="flat", font=("Helvetica", 10),
             highlightthickness=1, highlightbackground=BORDER,
             highlightcolor=ACCENT).grid(row=1, column=0, padx=(0, 4))

    tk.Label(mid, text="(0)", fg=ACCENT2, bg=BG_PANEL,
             font=("Helvetica", 11, "bold")).grid(row=1, column=1, padx=(0, 12))

    app.gdg_preview_var = tk.StringVar(value="")
    tk.Label(mid, textvariable=app.gdg_preview_var,
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).grid(row=2, column=0, columnspan=2,
                                         sticky="w", pady=(2, 0))

    def _update_preview(*_):
        dsn = app.gdg_dsn_var.get().strip()
        app.gdg_preview_var.set(
            f"→ FTP実行: RETR {_Q}{dsn}(0){_Q}" if dsn else "")
    app.gdg_dsn_var.trace_add("write", _update_preview)

    tk.Label(mid, text="保存先フォルダ",
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).grid(row=0, column=3, sticky="w", padx=(16, 0))

    app.gdg_savedir_var = tk.StringVar(value=os.path.expanduser("~"))
    tk.Entry(mid, textvariable=app.gdg_savedir_var, width=24,
             bg=BG_ITEM, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
             relief="flat", font=("Helvetica", 10),
             highlightthickness=1, highlightbackground=BORDER,
             highlightcolor=ACCENT).grid(row=1, column=3, padx=(16, 4))
    ttk.Button(mid, text="参照", style="Small.TButton",
               command=app._gdg_browse_savedir).grid(row=1, column=4)

    right = ttk.Frame(frame, style="Panel.TFrame")
    right.pack(side="right", padx=14, pady=8)
    ttk.Button(right, text="⬇ GDG DL",
               style="Accent.TButton",
               command=app._gdg_download_latest).pack()


def gdg_browse_savedir(app):
    d = filedialog.askdirectory(initialdir=app.gdg_savedir_var.get())
    if d:
        app.gdg_savedir_var.set(d)


def gdg_download_latest(app):
    if not app.ftp.connected:
        messagebox.showinfo("未接続", "先にFTPサーバーへ接続してください")
        return
    dsn = app.gdg_dsn_var.get().strip()
    if not dsn:
        messagebox.showwarning("入力エラー", "データセット名を入力してください\n例: HLQ.SALES.DATA")
        return
    save_dir = app.gdg_savedir_var.get()
    if not os.path.isdir(save_dir):
        messagebox.showwarning("保存先エラー", f"保存先フォルダが存在しません:\n{save_dir}")
        return
    local_name = dsn.split(".")[-1]
    local_path = os.path.join(save_dir, local_name)
    app.transfer_cancelled = False
    app.cancel_btn.state(["!disabled"])
    app._log(f"GDG DL開始: RETR {_Q}{dsn}(0){_Q}", "info")
    app._log(f"保存先: {local_path}", "info")

    def worker():
        try:
            downloaded = [0]
            def cb(chunk):
                if app.transfer_cancelled:
                    raise Exception("キャンセルされました")
                downloaded[0] += chunk
                app.after(0, lambda d=downloaded[0]:
                    app._set_progress(0, f"⬇ {local_name}  {_fmt_size(d)}"))
            app.ftp.download_gdg(dsn, local_path, cb)
            app.after(0, lambda: app._log(f"✦ DL完了: {local_path}", "ok"))
            app.after(0, lambda: messagebox.showinfo(
                "DL完了",
                f"GDG最新世代をダウンロードしました。\n\n"
                f"データセット: {dsn}(0)\n保存先: {local_path}"))
        except Exception as e:
            app.after(0, lambda e=e: app._log(f"GDG DLエラー: {e}", "err"))
            app.after(0, lambda e=e: messagebox.showerror("DLエラー", str(e)))
        finally:
            app.after(0, lambda: app._set_progress(0, "待機中"))
            app.after(0, lambda: app.cancel_btn.state(["disabled"]))
            app.after(0, app._refresh_local)
    threading.Thread(target=worker, daemon=True).start()
