"""
Day 87 - Email Monitor Configuration
=====================================
全ての設定を一箇所で管理する。
"""
import os

# --- メールフィルタリング ---
SUBJECT_FILTER = "月次レポート"          # 監視する件名（変更してください）
SUBJECT_MATCH_MODE = "contains"          # "exact", "contains", "startswith"

# --- 共有メールボックス ---
SHARED_MAILBOX_NAME = ""                 # 空文字 = 個人メールボックス
                                         # 例: "PurchasingDX" or "shared@example.com"
OUTLOOK_FOLDER_PATH = "Inbox"            # "/" 区切りでサブフォルダ指定可
                                         # 例: "Inbox/Reports"

# --- フォルダパス ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ATTACHMENT_SAVE_DIR = os.path.join(BASE_DIR, "attachments")
DB_PATH = os.path.join(BASE_DIR, "email_ledger.db")
LOG_FILE = os.path.join(BASE_DIR, "email_monitor.log")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

# --- Outlook設定 ---
SCAN_LAST_N_DAYS = 2                     # 直近N日分（初回/フォールバック用）
SCAN_MAX_ITEMS = 500                     # 1回のスキャン上限（安全弁）
SCAN_SAFETY_MARGIN_MINUTES = 10          # Restrict開始時刻のマージン（遅延配信対策）

# --- タスクスケジューラ ---
SCAN_INTERVAL_MINUTES = 5               # register_task.ps1 で使う実行間隔（分）

# --- 取引先マスタ ---
CLIENT_MASTER_EXCEL = os.path.join(BASE_DIR, "client_master.xlsx")
CLIENT_SHEET_NAME = "Sheet1"             # 取引先一覧のシート名
# 取引先Excelの列マッピング（0始まり or ヘッダー名）
CLIENT_COL_CODE = "コード"
CLIENT_COL_NAME = "社名"
CLIENT_COL_MONTH1 = "実施月1"
CLIENT_COL_MONTH2 = "実施月2"
CLIENT_COL_CS = "CS区分"

# --- ファイル処理 ---
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler\Library\bin"
FILE_PROCESS_EXTENSIONS = {".xlsx", ".xlsm", ".pdf"}
OCR_LANG = "jpn+eng"               # Tesseract言語パック
OCR_DPI = 300                       # PDF→画像変換時のDPI

# --- 添付ファイル分類 ---
ATTACHMENT_TYPE_MAP = {
    ".xlsx": "excel", ".xlsm": "excel", ".xls": "excel", ".csv": "excel",
    ".pdf": "pdf",
    ".zip": "zip",
    ".zi": "unknown_zip_like",
    ".doc": "word", ".docx": "word",
    ".ppt": "powerpoint", ".pptx": "powerpoint",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
}

# --- Excel出力 ---
EXCEL_FILENAME_TEMPLATE = "email_ledger_{date}.xlsx"
EXCEL_SHEET_NAME = "管理台帳"
EXCEL_EVENTS_SHEET_NAME = "処理ログ"
EXCEL_CLIENTS_SHEET_NAME = "取引先マスタ"
EXCEL_FILE_RESULTS_SHEET_NAME = "ファイル処理結果"

# --- ログ ---
LOG_LEVEL = "DEBUG"
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
