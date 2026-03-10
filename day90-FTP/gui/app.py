"""gui/app.py - App メインウィンドウ"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from ftp.client import FTPClient
import config
from gui.styles import apply_styles, BG_DARK, BG_PANEL, TEXT_SUB, SUCCESS, ERROR
from gui.panels.connection import build_connection_panel
from gui.panels.file_panes import (
    build_local_pane, build_remote_pane,
    refresh_local, browse_local_dir, local_double_click,
    refresh_remote, remote_double_click, remote_up,
)
from gui.panels.transfer import (
    build_transfer_buttons,
    upload, download, delete_remote, cancel_transfer,
)
from gui.panels.dsn_panel import (
    build_dsn_panel,
    dsn_browse_localfile, dsn_browse_savedir, dsn_upload, dsn_download,
)
from gui.panels.gdg_panel import (
    build_gdg_panel,
    gdg_browse_savedir, gdg_download_latest,
)
from gui.panels.log_panel import build_log_panel


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FTP クライアント  ✦  Day 90")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=BG_DARK)

        self.ftp = FTPClient()
        self.remote_path = "/"
        self.transfer_cancelled = False

        apply_styles(self)
        self._build_ui()
        self._load_profile()

    # ──────────────────────────────
    # UI 構築
    # ──────────────────────────────
    def _build_ui(self):
        # タイトルバー
        title_bar = ttk.Frame(self, style="Panel.TFrame")
        title_bar.pack(fill="x", pady=(0, 1))
        ttk.Label(title_bar, text="⬡  FTP クライアント",
                  style="Title.TLabel",
                  background=BG_PANEL).pack(side="left", padx=18, pady=10)
        self.status_dot = tk.Label(title_bar, text="●", fg=ERROR,
                                   bg=BG_PANEL, font=("Helvetica", 12))
        self.status_dot.pack(side="right", padx=6)
        self.status_label = tk.Label(title_bar, text="未接続",
                                     fg=TEXT_SUB, bg=BG_PANEL,
                                     font=("Helvetica", 9))
        self.status_label.pack(side="right", padx=(0, 4))

        # 接続パネル
        build_connection_panel(self, self)

        # ログパネル（先に作る — 他パネルから _log を使うため）
        build_log_panel(self, self)

        # メインエリア（ファイルペイン）
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=12, pady=6)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        build_local_pane(self, main)
        build_remote_pane(self, main)
        build_transfer_buttons(self, main)

        # DSN / GDG パネル
        build_dsn_panel(self, self)
        build_gdg_panel(self, self)

    # ──────────────────────────────
    # パネルへのメソッド委譲
    # ──────────────────────────────
    def _refresh_local(self, path=None):
        refresh_local(self, path)

    def _browse_local_dir(self):
        browse_local_dir(self)

    def _local_double_click(self, event):
        local_double_click(self, event)

    def _refresh_remote(self):
        refresh_remote(self)

    def _remote_double_click(self, event):
        remote_double_click(self, event)

    def _remote_up(self):
        remote_up(self)

    def _upload(self, files=None):
        upload(self, files)

    def _download(self):
        download(self)

    def _delete_remote(self):
        delete_remote(self)

    def _cancel_transfer(self):
        cancel_transfer(self)

    def _dsn_browse_localfile(self):
        dsn_browse_localfile(self)

    def _dsn_browse_savedir(self):
        dsn_browse_savedir(self)

    def _dsn_upload(self):
        dsn_upload(self)

    def _dsn_download(self):
        dsn_download(self)

    def _gdg_browse_savedir(self):
        gdg_browse_savedir(self)

    def _gdg_download_latest(self):
        gdg_download_latest(self)

    # ──────────────────────────────
    # 接続・切断
    # ──────────────────────────────
    def _toggle_connect(self):
        if self.ftp.connected:
            self.ftp.disconnect()
            self._set_connected(False)
            self.remote_tree.delete(*self.remote_tree.get_children())
            self._log("切断しました", "warn")
        else:
            self._do_connect()

    def _do_connect(self):
        host   = self.conn_host.get().strip()
        port   = self.conn_port.get().strip() or "21"
        user   = self.conn_user.get().strip()
        passwd = self.conn_pass.get()

        if not host:
            messagebox.showwarning("入力エラー", "ホスト名を入力してください")
            return

        self._log(f"接続中: {host}:{port} ({user})", "info")
        self.connect_btn.state(["disabled"])

        def worker():
            try:
                self.ftp.connect(host, port, user, passwd, self.passive_var.get())
                pwd = self.ftp.pwd()
                self.remote_path = pwd
                self.after(0, lambda: self.remote_path_var.set(pwd))
                self.after(0, lambda: self._set_connected(True))
                self.after(0, lambda: self._log(f"接続成功: {host}  [現在地: {pwd}]", "ok"))
                self.after(0, self._refresh_remote)
            except Exception as e:
                self.after(0, lambda e=e: self._log(f"接続失敗: {e}", "err"))
                self.after(0, lambda e=e: messagebox.showerror("接続エラー", str(e)))
            finally:
                self.after(0, lambda: self.connect_btn.state(["!disabled"]))

        threading.Thread(target=worker, daemon=True).start()

    def _set_connected(self, ok):
        color = SUCCESS if ok else ERROR
        text  = "接続中" if ok else "未接続"
        self.status_dot.configure(fg=color)
        self.status_label.configure(text=text)
        self.connect_btn.configure(text="切断" if ok else "接続")

    # ──────────────────────────────
    # プロファイル
    # ──────────────────────────────
    def _save_profile(self):
        try:
            path = config.save_profile(
                self.conn_host.get().strip(),
                self.conn_port.get().strip(),
                self.conn_user.get().strip(),
                self.conn_pass.get(),
                self.passive_var.get(),
            )
            self._log(f"プロファイルを保存しました → {path}", "ok")
            messagebox.showinfo("保存完了", "接続情報を保存しました。\n次回起動時に自動入力されます。")
        except Exception as e:
            self._log(f"プロファイル保存エラー: {e}", "err")

    def _load_profile(self):
        p = config.load_profile()
        if not p:
            return
        try:
            self.conn_host.set(p.get("host", ""))
            self.conn_port.set(p.get("port", "21"))
            self.conn_user.set(p.get("user", ""))
            self.conn_pass.set(p.get("passwd", ""))
            self.passive_var.set(p.get("passive", True))
            self._log("プロファイルを読み込みました（自動入力済み）", "ok")
        except Exception as e:
            self._log(f"プロファイル読込エラー: {e}", "err")

    def on_close(self):
        self.ftp.disconnect()
        self.destroy()
