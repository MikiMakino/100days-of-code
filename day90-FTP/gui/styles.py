"""gui/styles.py - カラー定数・ttk スタイル"""

# ========== カラーテーマ（ダーク） ==========
BG_DARK    = "#1a1d23"
BG_PANEL   = "#22262f"
BG_ITEM    = "#2a2f3a"
ACCENT     = "#4f9cf9"
ACCENT2    = "#63e6be"
TEXT_MAIN  = "#e8ecf4"
TEXT_SUB   = "#8b95a8"
BORDER     = "#3a3f4d"
SUCCESS    = "#63e6be"
ERROR      = "#ff6b6b"
WARNING    = "#ffd43b"


def apply_styles(widget):
    """ttk.Style にダークテーマを適用する。widget は tk.Tk / ttk.Style のどちらでも可。"""
    from tkinter import ttk
    style = ttk.Style(widget)
    style.theme_use("clam")

    style.configure(".",
        background=BG_DARK,
        foreground=TEXT_MAIN,
        fieldbackground=BG_ITEM,
        troughcolor=BG_PANEL,
        bordercolor=BORDER,
        darkcolor=BG_PANEL,
        lightcolor=BG_PANEL,
        font=("Helvetica", 10))

    style.configure("TFrame", background=BG_DARK)
    style.configure("Panel.TFrame", background=BG_PANEL)

    style.configure("TLabel",
        background=BG_DARK, foreground=TEXT_MAIN)
    style.configure("Sub.TLabel",
        background=BG_PANEL, foreground=TEXT_SUB, font=("Helvetica", 9))
    style.configure("Title.TLabel",
        background=BG_DARK, foreground=ACCENT,
        font=("Helvetica", 13, "bold"))
    style.configure("Header.TLabel",
        background=BG_PANEL, foreground=TEXT_MAIN,
        font=("Helvetica", 10, "bold"))

    style.configure("TEntry",
        fieldbackground=BG_ITEM, foreground=TEXT_MAIN,
        insertcolor=TEXT_MAIN, bordercolor=BORDER,
        relief="flat", padding=5)

    style.configure("Accent.TButton",
        background=ACCENT, foreground="#ffffff",
        font=("Helvetica", 10, "bold"),
        borderwidth=0, focusthickness=0, padding=(14, 7))
    style.map("Accent.TButton",
        background=[("active", "#3a7fd4"), ("disabled", BORDER)],
        foreground=[("disabled", TEXT_SUB)])

    style.configure("Danger.TButton",
        background="#c0392b", foreground="#ffffff",
        font=("Helvetica", 10), borderwidth=0, padding=(10, 6))
    style.map("Danger.TButton",
        background=[("active", "#e74c3c")])

    style.configure("Small.TButton",
        background=BG_ITEM, foreground=TEXT_MAIN,
        font=("Helvetica", 9), borderwidth=0, padding=(8, 4))
    style.map("Small.TButton",
        background=[("active", BORDER)])

    style.configure("Treeview",
        background=BG_ITEM, foreground=TEXT_MAIN,
        fieldbackground=BG_ITEM, rowheight=24,
        font=("Helvetica", 9), borderwidth=0)
    style.configure("Treeview.Heading",
        background=BG_PANEL, foreground=ACCENT,
        font=("Helvetica", 9, "bold"), borderwidth=0)
    style.map("Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", "#ffffff")])

    style.configure("TProgressbar",
        troughcolor=BG_ITEM, background=ACCENT,
        borderwidth=0, thickness=6)

    style.configure("TCheckbutton",
        background=BG_PANEL, foreground=TEXT_SUB)

    style.configure("TNotebook", background=BG_DARK, borderwidth=0)
    style.configure("TNotebook.Tab",
        background=BG_PANEL, foreground=TEXT_SUB,
        padding=(14, 6), borderwidth=0)
    style.map("TNotebook.Tab",
        background=[("selected", BG_DARK)],
        foreground=[("selected", ACCENT)])
