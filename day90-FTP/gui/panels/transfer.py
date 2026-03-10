"""gui/panels/transfer.py - 転送ボタン列（UL / DL / 削除）"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from gui.styles import BG_PANEL


def _fmt_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024**2:.1f} MB"
    else:
        return f"{size_bytes / 1024**3:.2f} GB"


def build_transfer_buttons(app, parent):
    """
    転送ボタン行をビルドして parent にgrid(row=0, columnspan=2, sticky=s)。
    """
    btn_frame = ttk.Frame(parent)
    btn_frame.grid(row=0, column=0, columnspan=2,
                   sticky="s", pady=(0, 8))

    ttk.Button(btn_frame, text="⬆  アップロード",
               style="Accent.TButton",
               command=app._upload).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="⬇  ダウンロード",
               style="Accent.TButton",
               command=app._download).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="🗑  削除",
               style="Danger.TButton",
               command=app._delete_remote).pack(side="left", padx=6)


# ──────────────────────────────
# アップロード
# ──────────────────────────────

def upload(app, files=None):
    """ローカル選択ファイルをリモートへアップロード。"""
    if not app.ftp.connected:
        messagebox.showinfo("未接続", "先にFTPサーバーへ接続してください")
        return

    if files is None:
        sel = app.local_tree.selection()
        if not sel:
            messagebox.showinfo("選択なし", "アップロードするファイルを選択してください")
            return
        local_dir = app.local_path_var.get()
        files = []
        for iid in sel:
            name = app.local_tree.item(iid, "values")[0]
            if name == "..":
                continue
            full = os.path.join(local_dir, name)
            if os.path.isfile(full):
                files.append((name, full))

    if not files:
        messagebox.showinfo("選択エラー", "ファイルのみアップロードできます（フォルダ不可）")
        return

    _do_upload(app, files)


def _do_upload(app, files):
    total_size = sum(os.path.getsize(p) for _, p in files)
    transferred = [0]
    app.transfer_cancelled = False
    app.cancel_btn.state(["!disabled"])

    def worker():
        for name, path in files:
            if app.transfer_cancelled:
                app.after(0, lambda: app._log("キャンセルされました", "warn"))
                break
            remote = app.remote_path.rstrip("/") + "/" + name
            app.after(0, lambda n=name: app._log(f"アップロード中: {n}", "info"))

            def cb(chunk, name=name):
                transferred[0] += chunk
                pct = min(transferred[0] / total_size * 100, 100) if total_size else 100
                app.after(0, lambda p=pct, n=name: app._set_progress(
                    p, f"⬆ {n}  {p:.1f}%"))

            try:
                app.ftp.upload(path, remote, cb)
                app.after(0, lambda n=name: app._log(f"完了: {n}", "ok"))
            except Exception as e:
                app.after(0, lambda e=e: app._log(f"エラー: {e}", "err"))

        app.after(0, lambda: app._set_progress(0, "待機中"))
        app.after(0, lambda: app.cancel_btn.state(["disabled"]))
        app.after(0, app._refresh_remote)

    threading.Thread(target=worker, daemon=True).start()


# ──────────────────────────────
# ダウンロード
# ──────────────────────────────

def download(app):
    """リモート選択ファイルをローカルへダウンロード。"""
    if not app.ftp.connected:
        messagebox.showinfo("未接続", "先にFTPサーバーへ接続してください")
        return
    sel = app.remote_tree.selection()
    if not sel:
        messagebox.showinfo("選択なし", "ダウンロードするファイルを選択してください")
        return

    files = []
    for iid in sel:
        vals = app.remote_tree.item(iid, "values")
        if vals[0] == ".." or vals[2] == "📁":
            continue
        files.append(vals[0])

    if not files:
        messagebox.showinfo("選択エラー", "ファイルのみダウンロードできます")
        return

    save_dir = app.local_path_var.get()
    app.transfer_cancelled = False
    app.cancel_btn.state(["!disabled"])

    def worker():
        for name in files:
            if app.transfer_cancelled:
                app.after(0, lambda: app._log("キャンセルされました", "warn"))
                break
            remote = app.remote_path.rstrip("/") + "/" + name
            local  = os.path.join(save_dir, name)
            app.after(0, lambda n=name: app._log(f"ダウンロード中: {n}", "info"))

            downloaded = [0]

            def cb(chunk, name=name):
                downloaded[0] += chunk
                app.after(0, lambda n=name, d=downloaded[0]:
                    app._set_progress(0, f"⬇ {n}  {_fmt_size(d)}"))

            try:
                app.ftp.download(remote, local, cb)
                app.after(0, lambda n=name: app._log(f"保存完了: {n}", "ok"))
            except Exception as e:
                app.after(0, lambda e=e: app._log(f"エラー: {e}", "err"))

        app.after(0, lambda: app._set_progress(0, "待機中"))
        app.after(0, lambda: app.cancel_btn.state(["disabled"]))
        app.after(0, app._refresh_local)

    threading.Thread(target=worker, daemon=True).start()


# ──────────────────────────────
# 削除
# ──────────────────────────────

def delete_remote(app):
    """リモート選択ファイル／フォルダを削除。"""
    if not app.ftp.connected:
        return
    sel = app.remote_tree.selection()
    if not sel:
        return
    names = [app.remote_tree.item(i, "values")[0] for i in sel
             if app.remote_tree.item(i, "values")[0] != ".."]
    if not names:
        return
    if not messagebox.askyesno("確認", f"{len(names)} 件を削除しますか？"):
        return

    def worker():
        for name in names:
            remote = app.remote_path.rstrip("/") + "/" + name
            try:
                vals = next((app.remote_tree.item(i, "values")
                             for i in sel
                             if app.remote_tree.item(i, "values")[0] == name), None)
                is_dir = vals and vals[2] == "📁"
                if is_dir:
                    app.ftp.delete_dir(remote)
                else:
                    app.ftp.delete_file(remote)
                app.after(0, lambda n=name: app._log(f"削除: {n}", "warn"))
            except Exception as e:
                app.after(0, lambda e=e: app._log(f"削除エラー: {e}", "err"))
        app.after(0, app._refresh_remote)

    threading.Thread(target=worker, daemon=True).start()


def cancel_transfer(app):
    app.transfer_cancelled = True
