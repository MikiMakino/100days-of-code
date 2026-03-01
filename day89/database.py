"""
database.py - SQLite DB 操作（お弁当発注管理アプリ）
"""
import sqlite3
import uuid
import hashlib
from datetime import datetime, date
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).parent / "bento.db"


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id      TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            affiliation  TEXT NOT NULL DEFAULT '社内',
            payment_type TEXT NOT NULL DEFAULT '非現金',
            email        TEXT UNIQUE NOT NULL,
            is_active    INTEGER NOT NULL DEFAULT 1,
            is_admin     INTEGER NOT NULL DEFAULT 0,
            password     TEXT NOT NULL,
            created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id      TEXT PRIMARY KEY,
            user_id       TEXT NOT NULL,
            order_date    TEXT NOT NULL,
            quantity      INTEGER NOT NULL DEFAULT 1,
            registered_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            status        TEXT NOT NULL DEFAULT '有効',
            cancelled_at  TEXT,
            orderer_id    TEXT NOT NULL,
            is_proxy      INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id)    REFERENCES users(user_id),
            FOREIGN KEY (orderer_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS bento_settings (
            id         INTEGER PRIMARY KEY,
            unit_price INTEGER NOT NULL DEFAULT 500,
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS company_calendar (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday_date TEXT NOT NULL UNIQUE,
            description  TEXT NOT NULL DEFAULT '休日',
            created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS fax_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date    TEXT NOT NULL,
            quantity      INTEGER NOT NULL,
            status        TEXT NOT NULL,
            sent_at       TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            error_message TEXT
        );
    """)

    # 初期データ投入（未登録の場合のみ）
    if not c.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        _seed(c)

    conn.commit()
    conn.close()


def _seed(c: sqlite3.Cursor):
    seed_users = [
        ("admin@company.com",  "管理者 太郎", "社内",  "非現金", True,  True,  "admin123"),
        ("tanaka@company.com", "田中 花子",   "社内",  "現金",   True,  False, "pass123"),
        ("suzuki@company.com", "鈴木 一郎",   "社内",  "非現金", True,  False, "pass123"),
        ("sato@partner.com",   "佐藤 次郎",   "出向者", "現金",  True,  False, "pass123"),
        ("yamada@partner.com", "山田 三郎",   "出向者", "非現金", True, False, "pass123"),
    ]
    for email, name, affil, pay, active, admin, pw in seed_users:
        c.execute("""
            INSERT OR IGNORE INTO users
              (user_id, name, affiliation, payment_type, email, is_active, is_admin, password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (email, name, affil, pay, email, int(active), int(admin), hash_pw(pw)))

    c.execute("INSERT OR IGNORE INTO bento_settings (id, unit_price) VALUES (1, 500)")


# ── 認証 ─────────────────────────────────────────────────────────────────────────
def authenticate(email: str, password: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=? AND is_active=1",
        (email, hash_pw(password))
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── ユーザー ─────────────────────────────────────────────────────────────────────
def get_all_users(include_inactive=False) -> pd.DataFrame:
    conn = get_conn()
    q = "SELECT * FROM users" + ("" if include_inactive else " WHERE is_active=1") + " ORDER BY name"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df


def get_user(user_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_user(user_id, name, affiliation, payment_type, email, is_active, is_admin, password=None):
    conn = get_conn()
    existing = conn.execute("SELECT password FROM users WHERE user_id=?", (user_id,)).fetchone()
    pw = hash_pw(password) if password else (existing["password"] if existing else hash_pw("pass123"))
    if existing:
        conn.execute("""
            UPDATE users
            SET name=?, affiliation=?, payment_type=?, email=?, is_active=?, is_admin=?, password=?
            WHERE user_id=?
        """, (name, affiliation, payment_type, email, int(is_active), int(is_admin), pw, user_id))
    else:
        conn.execute("""
            INSERT INTO users (user_id, name, affiliation, payment_type, email, is_active, is_admin, password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, affiliation, payment_type, email, int(is_active), int(is_admin), pw))
    conn.commit()
    conn.close()


# ── 注文 ──────────────────────────────────────────────────────────────────────────
def get_user_orders(user_id: str, year: int, month: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT o.*, u.name AS orderer_name
        FROM orders o
        JOIN users u ON o.orderer_id = u.user_id
        WHERE o.user_id = ?
          AND strftime('%Y', o.order_date) = ?
          AND strftime('%m', o.order_date) = ?
          AND o.status = '有効'
        ORDER BY o.order_date
    """, conn, params=(user_id, str(year), f"{month:02d}"))
    conn.close()
    return df


def get_all_orders(year: int, month: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT o.*,
               u.name  AS user_name,
               u.affiliation,
               u.payment_type,
               op.name AS orderer_name
        FROM orders o
        JOIN users u  ON o.user_id    = u.user_id
        JOIN users op ON o.orderer_id = op.user_id
        WHERE strftime('%Y', o.order_date) = ?
          AND strftime('%m', o.order_date) = ?
          AND o.status = '有効'
        ORDER BY o.order_date, u.name
    """, conn, params=(str(year), f"{month:02d}"))
    conn.close()
    return df


def get_orders_by_date(order_date: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT o.*, u.name AS user_name, u.payment_type
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        WHERE o.order_date = ? AND o.status = '有効'
        ORDER BY u.name
    """, conn, params=(order_date,))
    conn.close()
    return df


def place_order(user_id: str, order_date: str, orderer_id: str) -> tuple[bool, str]:
    conn = get_conn()
    try:
        # 休日チェック
        holiday = conn.execute(
            "SELECT description FROM company_calendar WHERE holiday_date=?", (order_date,)
        ).fetchone()
        if holiday:
            return False, f"休日のため注文できません（{holiday['description']}）"

        # 重複チェック
        if conn.execute(
            "SELECT 1 FROM orders WHERE user_id=? AND order_date=? AND status='有効'",
            (user_id, order_date)
        ).fetchone():
            return False, "その日はすでに注文済みです"

        order_id = str(uuid.uuid4())[:8].upper()
        is_proxy = 1 if user_id != orderer_id else 0
        conn.execute("""
            INSERT INTO orders (order_id, user_id, order_date, quantity, orderer_id, is_proxy)
            VALUES (?, ?, ?, 1, ?, ?)
        """, (order_id, user_id, order_date, orderer_id, is_proxy))
        conn.commit()
        return True, "注文しました ✅"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def cancel_order(order_id: str, requester_id: str, is_admin: bool) -> tuple[bool, str]:
    conn = get_conn()
    try:
        order = conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        if not order:
            return False, "注文が見つかりません"
        order = dict(order)
        if not is_admin and order["orderer_id"] != requester_id:
            return False, "この注文をキャンセルする権限がありません"
        conn.execute("""
            UPDATE orders
            SET status='キャンセル済み', cancelled_at=datetime('now','localtime')
            WHERE order_id=?
        """, (order_id,))
        conn.commit()
        return True, "キャンセルしました"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_proxy_history(user_id: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT o.order_id, o.order_date, o.status, o.registered_at, o.cancelled_at,
               u.name  AS target_name,
               op.name AS orderer_name,
               o.is_proxy
        FROM orders o
        JOIN users u  ON o.user_id    = u.user_id
        JOIN users op ON o.orderer_id = op.user_id
        WHERE (o.orderer_id=? OR o.user_id=?) AND o.is_proxy=1
        ORDER BY o.registered_at DESC
        LIMIT 100
    """, conn, params=(user_id, user_id))
    conn.close()
    return df


# ── 費用集計 ──────────────────────────────────────────────────────────────────────
def get_monthly_summary(year: int, month: int) -> tuple[pd.DataFrame, int]:
    conn = get_conn()
    row = conn.execute("SELECT unit_price FROM bento_settings WHERE id=1").fetchone()
    unit_price = row["unit_price"] if row else 500

    df = pd.read_sql_query("""
        SELECT u.user_id, u.name, u.affiliation, u.payment_type,
               COUNT(o.order_id) AS order_count
        FROM users u
        LEFT JOIN orders o
          ON u.user_id = o.user_id
         AND strftime('%Y', o.order_date) = ?
         AND strftime('%m', o.order_date) = ?
         AND o.status = '有効'
        WHERE u.is_active = 1
        GROUP BY u.user_id
        ORDER BY u.name
    """, conn, params=(str(year), f"{month:02d}"))
    conn.close()

    df["total_amount"] = df["order_count"] * unit_price
    return df, unit_price


# ── 弁当設定 ──────────────────────────────────────────────────────────────────────
def get_unit_price() -> int:
    conn = get_conn()
    row = conn.execute("SELECT unit_price FROM bento_settings WHERE id=1").fetchone()
    conn.close()
    return row["unit_price"] if row else 500


def update_unit_price(price: int):
    conn = get_conn()
    conn.execute(
        "UPDATE bento_settings SET unit_price=?, updated_at=datetime('now','localtime') WHERE id=1",
        (price,)
    )
    conn.commit()
    conn.close()


# ── 会社カレンダー ────────────────────────────────────────────────────────────────
def get_holidays(year: int, month: int = None) -> pd.DataFrame:
    conn = get_conn()
    if month:
        df = pd.read_sql_query(
            "SELECT * FROM company_calendar WHERE strftime('%Y',holiday_date)=? AND strftime('%m',holiday_date)=? ORDER BY holiday_date",
            conn, params=(str(year), f"{month:02d}")
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM company_calendar WHERE strftime('%Y',holiday_date)=? ORDER BY holiday_date",
            conn, params=(str(year),)
        )
    conn.close()
    return df


def is_holiday(date_str: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM company_calendar WHERE holiday_date=?", (date_str,)).fetchone()
    conn.close()
    return row is not None


def add_holiday(date_str: str, description: str) -> bool:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO company_calendar (holiday_date, description) VALUES (?, ?)",
            (date_str, description)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def remove_holiday(holiday_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM company_calendar WHERE id=?", (holiday_id,))
    conn.commit()
    conn.close()


# ── FAX ログ ──────────────────────────────────────────────────────────────────────
def log_fax(order_date: str, quantity: int, status: str, error_message: str = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO fax_log (order_date, quantity, status, error_message) VALUES (?, ?, ?, ?)",
        (order_date, quantity, status, error_message)
    )
    conn.commit()
    conn.close()


def get_fax_logs() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM fax_log ORDER BY sent_at DESC LIMIT 100", conn)
    conn.close()
    return df
