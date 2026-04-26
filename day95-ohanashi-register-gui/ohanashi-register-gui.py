"""
おはなしレジアプリ（tkinter版）
CLI版と同じ会話の流れを、GUIウィンドウで再現します。
"""

import tkinter as tk
from tkinter.scrolledtext import ScrolledText


# ── 計算ロジック（CLI版と同じ） ──────────────────────────────

def calculate_total(price, quantity, is_member):
    subtotal = price * quantity

    member_discount = int(subtotal * 0.1) if is_member else 0
    bulk_discount   = 100 if quantity >= 3 else 0

    total = subtotal - member_discount - bulk_discount
    return subtotal, member_discount, bulk_discount, total


def member_label(is_member):
    return "会員" if is_member else "一般"


# ── GUIアプリ本体 ─────────────────────────────────────────────

class OhanashiRegisterApp:
    """
    質問を1つずつ表示し、Enterキーで回答を受け取るターミナル風GUIです。
    CLIの input() → print() の流れを、Entryウィジェットで再現しています。
    """

    # 会話のステップを定数で管理
    STEP_NAME     = 0
    STEP_ITEM     = 1
    STEP_PRICE    = 2
    STEP_QUANTITY = 3
    STEP_MEMBER   = 4
    STEP_DONE     = 5

    def __init__(self, root):
        self.root = root
        self.root.title("おはなしレジアプリ")
        self.root.resizable(False, False)

        # 入力途中のデータを保持する変数
        self.customer_name = ""
        self.item_name     = ""
        self.price         = 0
        self.quantity      = 0
        self.is_member     = False

        self._build_ui()
        self._start()

    # ── UI構築 ──────────────────────────────────────────────

    def _build_ui(self):
        FONT_MAIN  = ("Helvetica", 13)
        FONT_INPUT = ("Helvetica", 13)
        BG_OUTPUT  = "#1e1e2e"   # ターミナル風の暗い背景
        FG_OUTPUT  = "#cdd6f4"   # 明るいテキスト
        BG_INPUT   = "#313244"
        FG_INPUT   = "#cdd6f4"
        BG_BTN     = "#89b4fa"
        FG_BTN     = "#1e1e2e"

        self.root.configure(bg=BG_OUTPUT)

        # ── 出力エリア ──
        self.output = ScrolledText(
            self.root,
            width=52, height=22,
            font=FONT_MAIN,
            bg=BG_OUTPUT, fg=FG_OUTPUT,
            insertbackground=FG_OUTPUT,
            relief="flat",
            padx=12, pady=10,
            state="disabled",       # ユーザーが直接編集できないようにする
            wrap="word",
        )
        self.output.pack(padx=16, pady=(16, 6))

        # ── 入力エリア ──
        input_frame = tk.Frame(self.root, bg=BG_OUTPUT)
        input_frame.pack(padx=16, pady=(0, 16), fill="x")

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.entry_var,
            font=FONT_INPUT,
            bg=BG_INPUT, fg=FG_INPUT,
            insertbackground=FG_INPUT,
            relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.entry.bind("<Return>", self._on_enter)   # Enterキーで送信
        self.entry.focus_set()

        self.send_btn = tk.Button(
            input_frame,
            text="送信",
            font=FONT_INPUT,
            bg=BG_BTN, fg=FG_BTN,
            relief="flat",
            padx=12,
            command=self._on_enter,
        )
        self.send_btn.pack(side="left", ipady=6)

    # ── 出力ヘルパー ────────────────────────────────────────

    def _print(self, text=""):
        """出力エリアに1行追記する（ScrolledTextはdisabledなので一時的に解除）"""
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")          # 常に最新行を表示
        self.output.configure(state="disabled")

    # ── 会話の流れ ───────────────────────────────────────────

    def _start(self):
        """アプリ起動時の最初のメッセージと最初の質問"""
        self.step = self.STEP_NAME
        self._print("おはなしレジアプリへようこそ！")
        self._print()
        self._print("お客さんの名前を入力してください: ")

    def _on_enter(self, event=None):
        """Enterキーまたは送信ボタンが押されたとき"""
        answer = self.entry_var.get().strip()
        self.entry_var.set("")          # 入力欄をクリア

        if not answer:
            return                      # 空のまま送信は無視

        # 入力内容を出力エリアに反映（ターミナルのエコーに相当）
        self._print(f"  > {answer}")

        # 現在のステップに応じて処理を分岐
        if   self.step == self.STEP_NAME:     self._handle_name(answer)
        elif self.step == self.STEP_ITEM:     self._handle_item(answer)
        elif self.step == self.STEP_PRICE:    self._handle_price(answer)
        elif self.step == self.STEP_QUANTITY: self._handle_quantity(answer)
        elif self.step == self.STEP_MEMBER:   self._handle_member(answer)
        elif self.step == self.STEP_DONE:     self._restart()

    # ── 各ステップの処理 ─────────────────────────────────────

    def _handle_name(self, answer):
        self.customer_name = answer
        self.step = self.STEP_ITEM
        self._print()
        self._print("商品名を入力してください: ")

    def _handle_item(self, answer):
        self.item_name = answer
        self.step = self.STEP_PRICE
        self._print()
        self._print("1つの値段（円）を入力してください: ")

    def _handle_price(self, answer):
        try:
            self.price = int(answer)
        except ValueError:
            self._print("  ※ 数字を入力してください。")
            self._print("1つの値段（円）を入力してください: ")
            return                      # ステップを進めずやり直し
        self.step = self.STEP_QUANTITY
        self._print()
        self._print("個数を入力してください: ")

    def _handle_quantity(self, answer):
        try:
            self.quantity = int(answer)
        except ValueError:
            self._print("  ※ 数字を入力してください。")
            self._print("個数を入力してください: ")
            return
        self.step = self.STEP_MEMBER
        self._print()
        self._print("会員ですか？ (y/n): ")

    def _handle_member(self, answer):
        self.is_member = answer.lower() == "y"
        self._show_result()

    def _show_result(self):
        """計算して会計を表示する"""
        subtotal, member_discount, bulk_discount, total = calculate_total(
            self.price, self.quantity, self.is_member
        )

        self._print()
        self._print("--- お会計 ---")
        self._print(f"{self.customer_name}さん、ありがとうございます。")
        self._print(f"商品: {self.item_name}")
        self._print(f"区分: {member_label(self.is_member)}")
        self._print(f"小計: {subtotal}円")
        self._print(f"会員割引: -{member_discount}円")
        self._print(f"まとめ買い割引: -{bulk_discount}円")
        self._print(f"合計: {total}円")
        self._print("またおはなしの世界へどうぞ！")
        self._print()
        self._print("─" * 40)
        self._print("続けるには、何か入力してEnterを押してください。")

        self.step = self.STEP_DONE

    def _restart(self):
        """もう一度最初から"""
        self._print()
        self._start()


# ── エントリーポイント ────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = OhanashiRegisterApp(root)
    root.mainloop()