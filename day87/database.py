"""
Day 87 - SQLite Database Layer
===============================
取引先マスタ + メール管理台帳 + ファイル処理結果 + イベントログ + 実行メタデータ。

テーブル構成:
  clients                - 取引先マスタ（コード, 社名, 実施月, CS区分）
  processed_emails       - メール1通につき1行（台帳）→ client_code で取引先に紐づく
  file_processing_results - ファイル1つにつき1行（件数カウント結果）→ client_code で紐づく
  processing_events      - メール/ファイル処理の監査ログ（複数行）
  run_metadata           - 最終実行時刻などのメタ情報

重複排除: Internet Message-ID 優先、EntryID フォールバック
"""
import sqlite3
import logging
from datetime import datetime

from config import DB_PATH

logger = logging.getLogger(__name__)


def get_db():
    """データベース接続を取得する。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """データベーススキーマを初期化する。"""
    conn = get_db()

    # --- 取引先マスタ ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            code          TEXT PRIMARY KEY,
            company_name  TEXT NOT NULL,
            month_1       TEXT,
            month_2       TEXT,
            cs_category   TEXT,
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL
        )
    """)

    # --- 台帳テーブル ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            stable_id            TEXT NOT NULL UNIQUE,
            client_code          TEXT,
            message_id           TEXT NOT NULL,
            internet_message_id  TEXT,
            conversation_id      TEXT,
            mailbox              TEXT,
            folder_path          TEXT,
            sender               TEXT NOT NULL,
            sender_email         TEXT,
            sender_smtp          TEXT,
            reply_to             TEXT,
            to_recipients        TEXT,
            cc_recipients        TEXT,
            subject              TEXT NOT NULL,
            received_date        TEXT NOT NULL,
            attachment_count     INTEGER DEFAULT 0,
            attachment_names     TEXT,
            attachment_types     TEXT,
            save_folder          TEXT,
            url_count            INTEGER DEFAULT 0,
            urls                 TEXT,
            processed_at         TEXT NOT NULL,
            FOREIGN KEY (client_code) REFERENCES clients(code)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stable_id
        ON processed_emails(stable_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_client_code
        ON processed_emails(client_code)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_received_date
        ON processed_emails(received_date)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversation_id
        ON processed_emails(conversation_id)
    """)

    # --- イベントログテーブル ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processing_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id  TEXT,
            event_time  TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            level       TEXT NOT NULL,
            source      TEXT NOT NULL,
            detail      TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_message_id
        ON processing_events(message_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_time
        ON processing_events(event_time)
    """)

    # --- ファイル処理結果テーブル ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_processing_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            client_code     TEXT,
            file_name       TEXT NOT NULL,
            file_type       TEXT NOT NULL,
            pdf_type        TEXT,
            record_count    INTEGER NOT NULL DEFAULT 0,
            source_folder   TEXT NOT NULL,
            processed_at    TEXT NOT NULL,
            UNIQUE(file_name, source_folder),
            FOREIGN KEY (client_code) REFERENCES clients(code)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fpr_client
        ON file_processing_results(client_code)
    """)

    # --- 実行メタデータテーブル ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    logger.info("データベース初期化完了: %s", DB_PATH)


# ===== 安定ID =====

def make_stable_id(internet_message_id: str, entry_id: str) -> str:
    """
    重複排除用の安定IDを生成する。
    Internet Message-ID があればそれを優先、なければ EntryID。
    """
    if internet_message_id:
        return f"inet:{internet_message_id}"
    return f"eid:{entry_id}"


# ===== 取引先マスタ =====

def upsert_client(code, company_name, month_1="", month_2="",
                  cs_category=""):
    """取引先を登録または更新する。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute(
        """INSERT INTO clients (code, company_name, month_1, month_2,
                                cs_category, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(code) DO UPDATE SET
               company_name = excluded.company_name,
               month_1      = excluded.month_1,
               month_2      = excluded.month_2,
               cs_category  = excluded.cs_category,
               updated_at   = excluded.updated_at""",
        (code, company_name, month_1, month_2, cs_category, now, now)
    )
    conn.commit()
    conn.close()


def get_all_clients():
    """全取引先を取得する。"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM clients ORDER BY code"
    ).fetchall()
    conn.close()
    return rows


def get_client_codes():
    """全取引先コードのリストを取得する（マッチング用）。"""
    conn = get_db()
    rows = conn.execute("SELECT code FROM clients ORDER BY code").fetchall()
    conn.close()
    return [r["code"] for r in rows]


def find_client_by_code(code: str):
    """コードで取引先を検索する。"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM clients WHERE code = ?", (code,)
    ).fetchone()
    conn.close()
    return row


# ===== 実行メタデータ =====

def get_last_run_time() -> str:
    """最終実行時刻を取得する。未実行なら空文字を返す。"""
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM run_metadata WHERE key = 'last_run_time'"
    ).fetchone()
    conn.close()
    return row["value"] if row else ""


def save_last_run_time(time_str: str = ""):
    """最終実行時刻を保存する。引数省略で現在時刻。"""
    if not time_str:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO run_metadata (key, value) VALUES (?, ?)",
        ("last_run_time", time_str)
    )
    conn.commit()
    conn.close()
    logger.debug("最終実行時刻を記録: %s", time_str)


# ===== イベントログ =====

def log_event(message_id: str, event_type: str, level: str,
              source: str, detail: str = ""):
    """
    処理イベントを記録する。
    event_type例: SCAN_START, SCAN_MATCH, CLIENT_MATCH, CLIENT_NOT_FOUND,
                  ATTACH_SAVE_OK, ATTACH_SAVE_FAIL, ATTACH_NONE,
                  URL_DETECTED, DB_INSERT_OK, DB_INSERT_DUP, ERROR
    """
    conn = get_db()
    conn.execute(
        """INSERT INTO processing_events
           (message_id, event_time, event_type, level, source, detail)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (message_id,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         event_type, level, source, detail)
    )
    conn.commit()
    conn.close()


def fetch_events(message_id: str = None):
    """イベントログを取得する。message_id指定で絞込み可能。"""
    conn = get_db()
    if message_id:
        rows = conn.execute(
            "SELECT * FROM processing_events WHERE message_id = ? "
            "ORDER BY event_time DESC",
            (message_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM processing_events ORDER BY event_time DESC"
        ).fetchall()
    conn.close()
    return rows


# ===== 台帳 =====

def is_processed(stable_id: str) -> bool:
    """指定のメールが既に処理済みかチェックする（安定ID基準）。"""
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM processed_emails WHERE stable_id = ?",
        (stable_id,)
    ).fetchone()
    conn.close()
    return row is not None


def save_record(*, stable_id, client_code="", message_id,
                internet_message_id="",
                conversation_id="", mailbox="", folder_path="",
                sender, sender_email="", sender_smtp="",
                reply_to="", to_recipients="", cc_recipients="",
                subject, received_date,
                attachment_count=0, attachment_names="",
                attachment_types="", save_folder="",
                url_count=0, urls=""):
    """
    処理済みメールのレコードを登録する。
    成功時True、重複時Falseを返す。
    """
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO processed_emails
               (stable_id, client_code,
                message_id, internet_message_id, conversation_id,
                mailbox, folder_path,
                sender, sender_email, sender_smtp,
                reply_to, to_recipients, cc_recipients,
                subject, received_date,
                attachment_count, attachment_names, attachment_types,
                save_folder, url_count, urls, processed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (stable_id, client_code or None,
             message_id, internet_message_id, conversation_id,
             mailbox, folder_path,
             sender, sender_email, sender_smtp,
             reply_to, to_recipients, cc_recipients,
             subject, received_date,
             attachment_count, attachment_names, attachment_types,
             save_folder, url_count, urls,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        logger.warning("重複メールをスキップ: %s", stable_id[:40])
        return False
    finally:
        conn.close()


# ===== ファイル処理結果 =====

def save_file_result(*, client_code="", file_name, file_type,
                     pdf_type=None, record_count, source_folder):
    """
    ファイル処理結果を登録する。
    成功時True、重複時Falseを返す。
    """
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO file_processing_results
               (client_code, file_name, file_type, pdf_type,
                record_count, source_folder, processed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (client_code or None, file_name, file_type, pdf_type,
             record_count, source_folder,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        logger.warning("重複ファイルをスキップ: %s", file_name)
        return False
    finally:
        conn.close()


def is_file_processed(file_name: str, source_folder: str) -> bool:
    """指定ファイルが既に処理済みかチェックする。"""
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM file_processing_results "
        "WHERE file_name = ? AND source_folder = ?",
        (file_name, source_folder)
    ).fetchone()
    conn.close()
    return row is not None


def fetch_file_results(source_folder: str = None):
    """ファイル処理結果を取得する（取引先情報をJOIN）。"""
    conn = get_db()
    if source_folder:
        rows = conn.execute("""
            SELECT f.*, c.company_name
            FROM file_processing_results f
            LEFT JOIN clients c ON f.client_code = c.code
            WHERE f.source_folder = ?
            ORDER BY f.processed_at DESC
        """, (source_folder,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT f.*, c.company_name
            FROM file_processing_results f
            LEFT JOIN clients c ON f.client_code = c.code
            ORDER BY f.processed_at DESC
        """).fetchall()
    conn.close()
    return rows


def fetch_all_records():
    """全レコードを取得する（Excel出力用、取引先情報をJOIN）。"""
    conn = get_db()
    rows = conn.execute("""
        SELECT e.*, c.company_name, c.month_1, c.month_2, c.cs_category
        FROM processed_emails e
        LEFT JOIN clients c ON e.client_code = c.code
        ORDER BY e.received_date DESC
    """).fetchall()
    conn.close()
    return rows
