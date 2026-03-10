"""gui/panels/dsn_panel.py - DSN 直接転送パネル"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from gui.styles import (
    BG_PANEL, BG_ITEM, TEXT_MAIN, TEXT_SUB, BORDER, ACCENT, WARNING
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


def build_dsn_panel(app, parent):
    """DSN 直接転送パネルをビルドして parent にpack。"""
    frame = ttk.Frame(parent, style="Panel.TFrame")
    frame.pack(fill="x", padx=12, pady=(0, 4))

    left = ttk.Frame(frame, style="Panel.TFrame")
    left.pack(side="left", padx=(14, 0), pady=8)
    tk.Label(left, text="📋  DSN 直接転送",
             fg=WARNING, bg=BG_PANEL,
             font=("Helvetica", 10, "bold")).pack(anchor="w")
    tk.Label(left, text="データセット名を直接入力して UL / DL",
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).pack(anchor="w")

    mid = ttk.Frame(frame, style="Panel.TFrame")
    mid.pack(side="left", padx=16, pady=8)

    tk.Label(mid, text="データセット名",
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).grid(row=0, column=0, columnspan=4, sticky="w")

    app.dsn_dsn_var = tk.StringVar(value="")
    tk.Entry(mid, textvariable=app.dsn_dsn_var, width=36,
             bg=BG_ITEM, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
             relief="flat", font=("Helvetica", 10),
             highlightthickness=1, highlightbackground=BORDER,
             highlightcolor=ACCENT).grid(row=1, column=0, columnspan=4,
                                         sticky="w", pady=(0, 4))

    app.dsn_preview_var = tk.StringVar(value="")
    tk.Label(mid, textvariable=app.dsn_preview_var,
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).grid(row=2, column=0, columnspan=4,
                                         sticky="w", pady=(0, 6))

    def _update_preview(*_):
        d = app.dsn_dsn_var.get().strip()
        app.dsn_preview_var.set(
            f"→ UL: STOR {_Q}{d}{_Q}  /  DL: RETR {_Q}{d}{_Q}" if d else "")
    app.dsn_dsn_var.trace_add("write", _update_preview)

    tk.Label(mid, text="UL ローカルファイル",
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).grid(row=3, column=0, sticky="w")

    app.dsn_localfile_var = tk.StringVar(value="")
    tk.Entry(mid, textvariable=app.dsn_localfile_var, width=30,
             bg=BG_ITEM, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
             relief="flat", font=("Helvetica", 10),
             highlightthickness=1, highlightbackground=BORDER,
             highlightcolor=ACCENT).grid(row=4, column=0, padx=(0, 4))
    ttk.Button(mid, text="参照", style="Small.TButton",
               command=app._dsn_browse_localfile).grid(row=4, column=1)

    tk.Label(mid, text="DL 保存先フォルダ",
             fg=TEXT_SUB, bg=BG_PANEL,
             font=("Helvetica", 8)).grid(row=3, column=2, sticky="w", padx=(16, 0))

    app.dsn_savedir_var = tk.StringVar(value=os.path.expanduser("~"))
    tk.Entry(mid, textvariable=app.dsn_savedir_var, width=24,
             bg=BG_ITEM, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
             relief="flat", font=("Helvetica", 10),
             highlightthickness=1, highlightbackground=BORDER,
             highlightcolor=ACCENT).grid(row=4, column=2, padx=(16, 4))
    ttk.Button(mid, text="参照", style="Small.TButton",
               command=app._dsn_browse_savedir).grid(row=4, column=3)

    right = ttk.Frame(frame, style="Panel.TFrame")
    right.pack(side="right", padx=14, pady=8)
    ttk.Button(right, text="⬆ DSN UL",
               style="Accent.TButton",
               command=app._dsn_upload).pack(pady=(0, 6))
    ttk.Button(right, text="⬇ DSN DL",
               style="Accent.TButton",
               command=app._dsn_download).pack()


def dsn_browse_localfile(app):
    p = filedialog.askopenfilename()
    if p:
        app.dsn_localfile_var.set(p)


def dsn_browse_savedir(app):
    d = filedialog.askdirectory(initialdir=app.dsn_savedir_var.get())
    if d:
        app.dsn_savedir_var.set(d)


def dsn_upload(app):
    if not app.ftp.connected:
        messagebox.showinfo("未接続", "先にFTPサーバーへ接続してください")
        return
    dsn = app.dsn_dsn_var.get().strip()
    if not dsn:
        messagebox.showwarning("入力エラー", "データセット名を入力してください\n例: HLQ.SALES.DATA")
        return
    local_path = app.dsn_localfile_var.get().strip()
    if not local_path or not os.path.isfile(local_path):
        messagebox.showwarning("ファイルエラー", "アップロードするローカルファイルを選択してください")
        return
    local_name = os.path.basename(local_path)
    file_size = os.path.getsize(local_path)
    app.transfer_cancelled = False
    app.cancel_btn.state(["!disabled"])
    app._log(f"DSN UL開始: STOR {_Q}{dsn}{_Q}", "info")
    app._log(f"ローカル: {local_path}", "info")

    def worker():
        try:
            uploaded = [0]
            def cb(chunk):
                if app.transfer_cancelled:
                    raise Exception("キャンセルされました")
                uploaded[0] += chunk
                pct = min(uploaded[0] / file_size * 100, 100) if file_size else 100
                app.after(0, lambda p=pct:
                    app._set_progress(p, f"⬆ {local_name}  {p:.1f}%"))
            app.ftp.upload_dsn(local_path, dsn, cb)
            app.after(0, lambda: app._log(f"✦ UL完了: {_Q}{dsn}{_Q}", "ok"))
            app.after(0, lambda: messagebox.showinfo(
                "UL完了",
                f"データセットへアップロードしました。\n\n"
                f"データセット: {dsn}\nローカルファイル: {local_path}"))
        except Exception as e:
            app.after(0, lambda e=e: app._log(f"DSN ULエラー: {e}", "err"))
            app.after(0, lambda e=e: messagebox.showerror("ULエラー", str(e)))
        finally:
            app.after(0, lambda: app._set_progress(0, "待機中"))
            app.after(0, lambda: app.cancel_btn.state(["disabled"]))
    threading.Thread(target=worker, daemon=True).start()


def dsn_download(app):
    if not app.ftp.connected:
        messagebox.showinfo("未接続", "先にFTPサーバーへ接続してください")
        return
    dsn = app.dsn_dsn_var.get().strip()
    if not dsn:
        messagebox.showwarning("入力エラー", "データセット名を入力してください\n例: HLQ.SALES.DATA")
        return
    save_dir = app.dsn_savedir_var.get()
    if not os.path.isdir(save_dir):
        messagebox.showwarning("保存先エラー", f"保存先フォルダが存在しません:\n{save_dir}")
        return
    local_name = dsn.split(".")[-1]
    local_path = os.path.join(save_dir, local_name)
    app.transfer_cancelled = False
    app.cancel_btn.state(["!disabled"])
    app._log(f"DSN DL開始: RETR {_Q}{dsn}{_Q}", "info")
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
            app.ftp.download_dsn(dsn, local_path, cb)
            app.after(0, lambda: app._log(f"✦ DL完了: {local_path}", "ok"))
            app.after(0, lambda: messagebox.showinfo(
                "DL完了",
                f"データセットをダウンロードしました。\n\n"
                f"データセット: {dsn}\n保存先: {local_path}"))
        except Exception as e:
            app.after(0, lambda e=e: app._log(f"DSN DLエラー: {e}", "err"))
            app.after(0, lambda e=e: messagebox.showerror("DLエラー", str(e)))
        finally:
            app.after(0, lambda: app._set_progress(0, "待機中"))
            app.after(0, lambda: app.cancel_btn.state(["disabled"]))
            app.after(0, app._refresh_local)
    threading.Thread(target=worker, daemon=True).start()
