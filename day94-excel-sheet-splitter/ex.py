import os
import re
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pythoncom
import win32com.client as win32


# ──────────────────────────────────────────────
#  ユーティリティ
# ──────────────────────────────────────────────

def safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', name)


# ──────────────────────────────────────────────
#  Excel 処理（すべてバックグラウンドスレッドで実行）
# ──────────────────────────────────────────────

def get_sheet_names(src_path: str) -> list[str]:
    """シート名一覧を取得して返す（COM初期化付き）。"""
    pythoncom.CoInitialize()
    try:
        excel = win32.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        try:
            wb = excel.Workbooks.Open(os.path.abspath(src_path))
            names = [s.Name for s in wb.Sheets]
            wb.Close(False)
        finally:
            excel.Quit()
    finally:
        pythoncom.CoUninitialize()
    return names


def _split_by_delete(excel, src_file, common_sheets, split_sheets,
                     out_dir, progress_cb):
    """互換版: ファイルをコピーして不要シートを削除。"""
    created = []
    keep_base = set(common_sheets)
    for i, sheet_name in enumerate(split_sheets, 1):
        progress_cb(i, len(split_sheets), sheet_name)
        out_path = os.path.join(out_dir, safe_name(sheet_name) + ".xlsx")
        shutil.copy2(src_file, out_path)

        new_wb = excel.Workbooks.Open(os.path.abspath(out_path))
        keep = keep_base | {sheet_name}
        for name in [s.Name for s in new_wb.Sheets if s.Name not in keep]:
            new_wb.Sheets(name).Visible = True
            new_wb.Sheets(name).Delete()
        new_wb.SaveAs(os.path.abspath(out_path), FileFormat=51)
        new_wb.Close(SaveChanges=False)
        created.append(out_path)
    return created


def run_split(src_file, common_sheets, split_sheets, out_dir, progress_cb):
    """分割処理のエントリーポイント（バックグラウンドスレッドから呼ぶ）。"""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    pythoncom.CoInitialize()
    try:
        excel = win32.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        try:
            created = _split_by_delete(excel, src_file, common_sheets,
                                       split_sheets, out_dir, progress_cb)
        finally:
            excel.Quit()
    finally:
        pythoncom.CoUninitialize()

    return created


# ──────────────────────────────────────────────
#  GUI
# ──────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel シート分割ツール")
        self.resizable(True, True)
        self._build_ui()

    # ── UIの構築 ──────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # ── ファイル選択 ──
        frm_file = ttk.LabelFrame(self, text="元のExcelファイル", padding=8)
        frm_file.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")
        frm_file.columnconfigure(0, weight=1)

        self.src_var = tk.StringVar()
        ttk.Entry(frm_file, textvariable=self.src_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(frm_file, text="参照...", command=self._browse_src).grid(
            row=0, column=1)
        ttk.Button(frm_file, text="シート読み込み",
                   command=self._load_sheets_async).grid(
            row=0, column=2, padx=(6, 0))

        # ── シート振り分け ──
        frm_sheets = ttk.LabelFrame(self, text="シートの振り分け", padding=8)
        frm_sheets.grid(row=1, column=0, padx=12, pady=4, sticky="nsew")
        self.rowconfigure(1, weight=1)
        frm_sheets.columnconfigure(0, weight=2)
        frm_sheets.columnconfigure(3, weight=1)

        # 左列：分割対象
        ttk.Label(frm_sheets, text="分割対象",
                  font=("", 9, "bold")).grid(row=0, column=0, columnspan=2)
        self.lb_split = tk.Listbox(frm_sheets, selectmode=tk.EXTENDED,
                                   width=28, height=15, exportselection=False)
        sb_split = ttk.Scrollbar(frm_sheets, orient=tk.VERTICAL,
                                 command=self.lb_split.yview)
        self.lb_split.configure(yscrollcommand=sb_split.set)
        self.lb_split.grid(row=1, column=0, rowspan=6, sticky="nsew")
        sb_split.grid(row=1, column=1, rowspan=6, sticky="ns")

        # 中央：移動ボタン
        frm_mid = ttk.Frame(frm_sheets)
        frm_mid.grid(row=1, column=2, padx=8, sticky="n")
        ttk.Button(frm_mid, text="→ 共通へ", width=11,
                   command=lambda: self._move(self.lb_split, self.lb_common)
                   ).pack(pady=3)
        ttk.Button(frm_mid, text="→ 除外へ", width=11,
                   command=lambda: self._move(self.lb_split, self.lb_exclude)
                   ).pack(pady=3)
        ttk.Separator(frm_mid, orient=tk.HORIZONTAL).pack(fill="x", pady=8)
        ttk.Button(frm_mid, text="← 共通を戻す", width=11,
                   command=lambda: self._move(self.lb_common, self.lb_split)
                   ).pack(pady=3)
        ttk.Button(frm_mid, text="← 除外を戻す", width=11,
                   command=lambda: self._move(self.lb_exclude, self.lb_split)
                   ).pack(pady=3)

        # 右列：共通シート＋除外シート
        ttk.Label(frm_sheets, text="共通シート（全ファイルに含める）",
                  font=("", 9, "bold")).grid(row=0, column=3, columnspan=2)
        self.lb_common = tk.Listbox(frm_sheets, selectmode=tk.EXTENDED,
                                    width=26, height=7, exportselection=False)
        sb_common = ttk.Scrollbar(frm_sheets, orient=tk.VERTICAL,
                                  command=self.lb_common.yview)
        self.lb_common.configure(yscrollcommand=sb_common.set)
        self.lb_common.grid(row=1, column=3, rowspan=2, sticky="nsew")
        sb_common.grid(row=1, column=4, rowspan=2, sticky="ns")

        ttk.Label(frm_sheets, text="除外シート（どのファイルにも含めない）",
                  font=("", 9, "bold")).grid(row=3, column=3, columnspan=2,
                                             pady=(10, 2))
        self.lb_exclude = tk.Listbox(frm_sheets, selectmode=tk.EXTENDED,
                                     width=26, height=7, exportselection=False)
        sb_exclude = ttk.Scrollbar(frm_sheets, orient=tk.VERTICAL,
                                   command=self.lb_exclude.yview)
        self.lb_exclude.configure(yscrollcommand=sb_exclude.set)
        self.lb_exclude.grid(row=4, column=3, rowspan=2, sticky="nsew")
        sb_exclude.grid(row=4, column=4, rowspan=2, sticky="ns")

        # ── 出力設定 ──
        frm_out = ttk.LabelFrame(self, text="出力設定", padding=8)
        frm_out.grid(row=2, column=0, padx=12, pady=4, sticky="ew")
        frm_out.columnconfigure(1, weight=1)

        ttk.Label(frm_out, text="出力先フォルダ:").grid(
            row=0, column=0, sticky="e", padx=(0, 4))
        self.out_var = tk.StringVar()
        ttk.Entry(frm_out, textvariable=self.out_var).grid(
            row=0, column=1, sticky="ew")
        ttk.Button(frm_out, text="参照...", command=self._browse_out).grid(
            row=0, column=2, padx=(4, 0))

        # ── 進捗 & 実行ボタン ──
        frm_exec = ttk.Frame(self, padding=(12, 4, 12, 12))
        frm_exec.grid(row=3, column=0, sticky="ew")
        frm_exec.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(frm_exec, mode="determinate")
        self.progress.grid(row=0, column=0, columnspan=2,
                           sticky="ew", pady=(0, 4))

        self.status_var = tk.StringVar(value="Excelファイルを選択してください")
        ttk.Label(frm_exec, textvariable=self.status_var,
                  anchor="w").grid(row=1, column=0, sticky="w")

        self.btn_run = ttk.Button(frm_exec, text="  実行  ",
                                  command=self._run, state="disabled")
        self.btn_run.grid(row=1, column=1, sticky="e")

    # ── イベントハンドラ ──────────────────────

    def _browse_src(self):
        path = filedialog.askopenfilename(
            title="Excelファイルを選択",
            filetypes=[("Excelファイル", "*.xlsx *.xls *.xlsm"),
                       ("すべてのファイル", "*.*")])
        if path:
            self.src_var.set(path)
            base = os.path.splitext(os.path.basename(path))[0]
            self.out_var.set(
                os.path.join(os.path.dirname(path), safe_name(base) + "_split"))

    def _browse_out(self):
        path = filedialog.askdirectory(title="出力先フォルダを選択")
        if path:
            self.out_var.set(path)

    def _load_sheets_async(self):
        src = self.src_var.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showerror("エラー", "有効なExcelファイルを指定してください")
            return
        self.status_var.set("シートを読み込み中...")
        self.btn_run.config(state="disabled")
        self.update_idletasks()

        def worker():
            try:
                names = get_sheet_names(src)
                self.after(0, lambda: self._on_sheets_loaded(names))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "エラー", f"シート読み込み失敗:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_sheets_loaded(self, names: list[str]):
        for lb in (self.lb_split, self.lb_common, self.lb_exclude):
            lb.delete(0, tk.END)
        for name in names:
            self.lb_split.insert(tk.END, name)
        self.status_var.set(
            f"{len(names)}枚のシートを読み込みました。"
            "振り分けを設定して「実行」を押してください")
        self.btn_run.config(state="normal")

    def _move(self, src_lb: tk.Listbox, dst_lb: tk.Listbox):
        selected = list(src_lb.curselection())
        if not selected:
            return
        items = [src_lb.get(i) for i in selected]
        for i in reversed(selected):
            src_lb.delete(i)
        for item in items:
            dst_lb.insert(tk.END, item)

    def _run(self):
        src = self.src_var.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showerror("エラー", "有効なExcelファイルを指定してください")
            return

        split_sheets = list(self.lb_split.get(0, tk.END))
        common_sheets = list(self.lb_common.get(0, tk.END))

        if not split_sheets:
            messagebox.showwarning("警告", "分割対象のシートがありません")
            return

        out_dir = self.out_var.get().strip()
        if not out_dir:
            messagebox.showerror("エラー", "出力先フォルダを指定してください")
            return

        self.btn_run.config(state="disabled")
        self.progress.configure(maximum=len(split_sheets), value=0)

        def progress_cb(i, total, name):
            def update():
                self.progress.configure(value=i)
                self.status_var.set(f"[{i}/{total}] 作成中: {name}")
            self.after(0, update)

        def worker():
            try:
                created = run_split(src, common_sheets, split_sheets,
                                    out_dir, progress_cb)
                self.after(0, lambda: self._done(len(created), out_dir))
            except Exception as e:
                self.after(0, lambda: self._error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, count, out_dir):
        self.progress.configure(value=self.progress["maximum"])
        self.status_var.set(f"完了: {count}枚を分割 → {out_dir}")
        self.btn_run.config(state="normal")
        messagebox.showinfo(
            "完了",
            f"{count}枚のシートを個別ファイルに分割しました。\n\n"
            f"保存先:\n{out_dir}")

    def _error(self, msg):
        self.status_var.set("エラーが発生しました")
        self.btn_run.config(state="normal")
        messagebox.showerror("エラー", msg)


# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
