import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from jcl_generator import Condition, JCLConfig, JCLGenerator
from layout_loader import get_layout_files, load_layout


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JCL ジェネレーター")
        self.resizable(True, True)

        self._layout_data: dict | None = None
        self._condition_rows: list[dict] = []
        self._field_check_vars: dict[str, tk.BooleanVar] = {}

        self._build_ui()

    # ─── UI 構築 ─────────────────────────────────────────────────────────
    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_basic_settings(main)
        self._build_conditions(main)
        self._build_output_settings(main)
        self._build_buttons(main)

    # ─── [1] 基本設定 ────────────────────────────────────────────────────
    def _build_basic_settings(self, parent: ttk.Frame):
        frame = ttk.LabelFrame(parent, text="[1] 基本設定", padding=8)
        frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        labels = ["ユーザーコード:", "レイアウト定義:", "入力 DSN:", "出力 DSN:"]
        for i, text in enumerate(labels):
            ttk.Label(frame, text=text, anchor="w").grid(
                row=i, column=0, sticky="w", padx=5, pady=3
            )

        self._user_code = ttk.Entry(frame, width=12)
        self._user_code.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        self._layout_var = tk.StringVar()
        self._layout_combo = ttk.Combobox(
            frame, textvariable=self._layout_var,
            values=get_layout_files(), width=35, state="readonly"
        )
        self._layout_combo.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        self._layout_combo.bind("<<ComboboxSelected>>", self._on_layout_selected)

        self._input_dsn = ttk.Entry(frame, width=50)
        self._input_dsn.grid(row=2, column=1, sticky="w", padx=5, pady=3)

        self._output_dsn = ttk.Entry(frame, width=50)
        self._output_dsn.grid(row=3, column=1, sticky="w", padx=5, pady=3)

    def _on_layout_selected(self, _event=None):
        self._layout_data = load_layout(self._layout_var.get())
        field_names = [f["name"] for f in self._layout_data["fields"]]

        # 既存条件行のフィールドドロップダウンを更新
        for row in self._condition_rows:
            row["field_combo"]["values"] = field_names

        # 入力 DSN をレイアウト定義のデフォルトで補完
        self._input_dsn.delete(0, tk.END)
        self._input_dsn.insert(0, self._layout_data.get("dataset_name", ""))

        # 出力フィールド選択を更新
        self._refresh_output_fields()

    # ─── [2] 抽出条件 ────────────────────────────────────────────────────
    def _build_conditions(self, parent: ttk.Frame):
        outer = ttk.LabelFrame(parent, text="[2] 抽出条件", padding=8)
        outer.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # ヘッダー
        header = ttk.Frame(outer)
        header.pack(fill="x")
        col_spec = [("", 7), ("フィールド", 18), ("型", 5),
                    ("演算子", 8), ("値", 22), ("", 4)]
        for col, (text, width) in enumerate(col_spec):
            ttk.Label(header, text=text, width=width, anchor="center").grid(
                row=0, column=col, padx=2
            )

        # 条件行コンテナ
        self._cond_container = ttk.Frame(outer)
        self._cond_container.pack(fill="x")

        # ボタン
        btn_frame = ttk.Frame(outer)
        btn_frame.pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="条件追加",
                   command=self._add_condition_row).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="条件削除",
                   command=self._remove_last_condition_row).pack(side="left", padx=3)

        # 最初の条件行
        self._add_condition_row()

    def _add_condition_row(self):
        is_first = len(self._condition_rows) == 0
        field_names = (
            [f["name"] for f in self._layout_data["fields"]]
            if self._layout_data else []
        )

        row_frame = ttk.Frame(self._cond_container)
        row_frame.pack(fill="x", pady=1)

        widgets: dict = {"row_frame": row_frame}

        # AND/OR（最初の行はラベル、2行目以降はコンボボックス）
        connector_var = tk.StringVar(value="AND")
        if is_first:
            connector_w = ttk.Label(row_frame, text="", width=7)
        else:
            connector_w = ttk.Combobox(
                row_frame, textvariable=connector_var,
                values=["AND", "OR"], width=5, state="readonly"
            )
        connector_w.grid(row=0, column=0, padx=2)
        widgets["connector_var"] = connector_var

        # フィールド
        field_var = tk.StringVar()
        field_combo = ttk.Combobox(
            row_frame, textvariable=field_var,
            values=field_names, width=18, state="readonly"
        )
        field_combo.grid(row=0, column=1, padx=2)
        widgets["field_var"] = field_var
        widgets["field_combo"] = field_combo

        # 型（フィールド選択で自動表示）
        type_var = tk.StringVar()
        ttk.Label(
            row_frame, textvariable=type_var,
            width=5, relief="sunken", anchor="center"
        ).grid(row=0, column=2, padx=2)
        widgets["type_var"] = type_var

        def on_field_selected(_event, fv=field_var, tv=type_var):
            if self._layout_data:
                for f in self._layout_data["fields"]:
                    if f["name"] == fv.get():
                        tv.set(f["type"])
                        break

        field_combo.bind("<<ComboboxSelected>>", on_field_selected)

        # 演算子
        op_var = tk.StringVar(value="EQ")
        ttk.Combobox(
            row_frame, textvariable=op_var,
            values=["EQ", "NE", "GT", "LT", "GE", "LE"],
            width=6, state="readonly"
        ).grid(row=0, column=3, padx=2)
        widgets["op_var"] = op_var

        # 値
        val_entry = ttk.Entry(row_frame, width=22)
        val_entry.grid(row=0, column=4, padx=2)
        widgets["val_entry"] = val_entry

        # 削除ボタン
        ttk.Button(
            row_frame, text="×", width=3,
            command=lambda rw=widgets: self._remove_specific_row(rw)
        ).grid(row=0, column=5, padx=2)

        self._condition_rows.append(widgets)

    def _remove_last_condition_row(self):
        if len(self._condition_rows) <= 1:
            messagebox.showwarning("警告", "条件は最低1つ必要です。")
            return
        row = self._condition_rows.pop()
        row["row_frame"].destroy()

    def _remove_specific_row(self, row_widgets: dict):
        if len(self._condition_rows) <= 1:
            messagebox.showwarning("警告", "条件は最低1つ必要です。")
            return
        self._condition_rows.remove(row_widgets)
        row_widgets["row_frame"].destroy()

    # ─── [3] 出力設定 ────────────────────────────────────────────────────
    def _build_output_settings(self, parent: ttk.Frame):
        frame = ttk.LabelFrame(parent, text="[3] 出力設定", padding=8)
        frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        self._output_mode = tk.StringVar(value="COPY")
        ttk.Radiobutton(
            frame, text="全項目 COPY", variable=self._output_mode,
            value="COPY", command=self._on_output_mode_changed
        ).grid(row=0, column=0, padx=10, sticky="w")
        ttk.Radiobutton(
            frame, text="項目を絞る", variable=self._output_mode,
            value="SELECT", command=self._on_output_mode_changed
        ).grid(row=0, column=1, padx=10, sticky="w")

        self._field_select_frame = ttk.Frame(frame)
        self._field_select_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=5)

    def _on_output_mode_changed(self):
        self._refresh_output_fields()

    def _refresh_output_fields(self):
        for w in self._field_select_frame.winfo_children():
            w.destroy()
        self._field_check_vars.clear()

        if self._output_mode.get() != "SELECT" or not self._layout_data:
            return

        ttk.Label(self._field_select_frame, text="出力フィールドを選択:").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=2
        )
        for i, field in enumerate(self._layout_data["fields"]):
            var = tk.BooleanVar(value=True)
            self._field_check_vars[field["name"]] = var
            ttk.Checkbutton(
                self._field_select_frame, text=field["name"], variable=var
            ).grid(row=1 + i // 4, column=i % 4, sticky="w", padx=10)

    # ─── ボタン ──────────────────────────────────────────────────────────
    def _build_buttons(self, parent: ttk.Frame):
        frame = ttk.Frame(parent)
        frame.grid(row=3, column=0, pady=10)
        ttk.Button(frame, text="JCL 生成", command=self._generate_jcl,
                   width=15).pack(side="left", padx=10)
        ttk.Button(frame, text="プレビュー", command=self._preview_jcl,
                   width=15).pack(side="left", padx=10)

    # ─── 入力収集・バリデーション ──────────────────────────────────────────
    def _collect_input(self) -> JCLConfig | None:
        user_code = self._user_code.get().strip()
        if not user_code:
            messagebox.showerror("エラー", "ユーザーコードを入力してください。")
            return None
        if len(user_code) > 8:
            messagebox.showerror("エラー", "ユーザーコードは8文字以内で入力してください。")
            return None
        if not self._layout_data:
            messagebox.showerror("エラー", "レイアウト定義を選択してください。")
            return None

        input_dsn = self._input_dsn.get().strip()
        output_dsn = self._output_dsn.get().strip()
        if not input_dsn or not output_dsn:
            messagebox.showerror("エラー", "入力 DSN と出力 DSN を入力してください。")
            return None

        conditions = self._collect_conditions()
        if conditions is None:
            return None

        output_mode = self._output_mode.get()
        output_fields: list[dict] = []
        if output_mode == "SELECT":
            output_fields = [
                f for f in self._layout_data["fields"]
                if self._field_check_vars.get(f["name"], tk.BooleanVar(value=False)).get()
            ]
            if not output_fields:
                messagebox.showerror("エラー", "出力フィールドを1つ以上選択してください。")
                return None

        return JCLConfig(
            user_code=user_code,
            input_dsn=input_dsn,
            output_dsn=output_dsn,
            lrecl=self._layout_data["lrecl"],
            conditions=conditions,
            output_mode=output_mode,
            output_fields=output_fields,
        )

    def _collect_conditions(self) -> list[Condition] | None:
        conditions: list[Condition] = []
        for i, row in enumerate(self._condition_rows):
            field_name = row["field_var"].get()
            field_type = row["type_var"].get()
            operator = row["op_var"].get()
            value = row["val_entry"].get().strip()
            is_last = i == len(self._condition_rows) - 1
            connector = "" if is_last else row["connector_var"].get()

            if not field_name:
                messagebox.showerror("エラー", f"条件 {i + 1}: フィールドを選択してください。")
                return None
            if not value:
                messagebox.showerror("エラー", f"条件 {i + 1}: 値を入力してください。")
                return None

            field_def = next(
                f for f in self._layout_data["fields"] if f["name"] == field_name
            )
            conditions.append(Condition(
                field_name=field_name,
                start=field_def["start"],
                length=field_def["length"],
                field_type=field_type,
                operator=operator,
                value=value,
                connector=connector,
            ))
        return conditions

    # ─── JCL 生成・保存・プレビュー ──────────────────────────────────────
    def _generate_jcl(self):
        cfg = self._collect_input()
        if cfg is None:
            return
        gen = JCLGenerator(cfg)
        content = gen.generate()
        path = gen.save(content)
        messagebox.showinfo("完了", f"JCL を保存しました。\n{path}")

    def _preview_jcl(self):
        cfg = self._collect_input()
        if cfg is None:
            return
        content = JCLGenerator(cfg).generate()
        self._show_preview(content)

    def _show_preview(self, content: str):
        win = tk.Toplevel(self)
        win.title("JCL プレビュー")
        win.geometry("720x500")
        text = scrolledtext.ScrolledText(win, font=("Courier New", 10), wrap="none")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", content)
        text.config(state="disabled")
