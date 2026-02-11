"""
Day 87 - Outlook COM Client
============================
win32com.clientを使用してOutlookの受信トレイを操作する。
共有メールボックス対応、添付タイプ判定、URL抽出、送信元SMTP解決を含む。

Restrict方式: 前回実行時刻以降のメールだけをフィルタして効率化。
"""
import os
import logging
import re
from datetime import datetime, timedelta

import win32com.client
import pywintypes

from config import (
    SUBJECT_FILTER, SUBJECT_MATCH_MODE, ATTACHMENT_SAVE_DIR,
    SCAN_LAST_N_DAYS, SCAN_MAX_ITEMS, SCAN_SAFETY_MARGIN_MINUTES,
    SHARED_MAILBOX_NAME, OUTLOOK_FOLDER_PATH,
    ATTACHMENT_TYPE_MAP,
)

logger = logging.getLogger(__name__)

# Windowsファイル名に使えない文字
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')

# 本文からURL抽出用
_URL_PATTERN = re.compile(r'https?://[^\s<>"\')\]]+')


def _sanitize_filename(name: str) -> str:
    """ファイル名からWindows禁止文字を除去する。"""
    return _INVALID_FILENAME_CHARS.sub("_", name)


def _classify_attachment(filename: str) -> str:
    """添付ファイルの拡張子から種類を判定する。"""
    _, ext = os.path.splitext(filename.lower())
    return ATTACHMENT_TYPE_MAP.get(ext, ext if ext else "no_ext")


def _resolve_sender_smtp(mail_item) -> str:
    """送信者のSMTPアドレスを取得する（ExchangeユーザーのX500対策）。"""
    try:
        PR_SMTP = "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
        return mail_item.PropertyAccessor.GetProperty(PR_SMTP)
    except Exception:
        pass
    try:
        sender = mail_item.Sender
        if sender:
            exuser = sender.GetExchangeUser()
            if exuser:
                return exuser.PrimarySmtpAddress
    except Exception:
        pass
    try:
        return mail_item.SenderEmailAddress or ""
    except Exception:
        return ""


def _get_recipients_str(mail_item, field: str) -> str:
    """To/Ccの受信者一覧をカンマ区切り文字列で返す。"""
    try:
        if field == "to":
            return mail_item.To or ""
        elif field == "cc":
            return mail_item.CC or ""
    except Exception:
        return ""
    return ""


def _get_reply_to(mail_item) -> str:
    """ReplyTo（返信先）を取得する。"""
    try:
        reply_recipients = mail_item.ReplyRecipients
        if reply_recipients and reply_recipients.Count > 0:
            addrs = []
            for i in range(1, reply_recipients.Count + 1):
                addrs.append(reply_recipients.Item(i).Address)
            return ", ".join(addrs)
    except Exception:
        pass
    return ""


def extract_urls(mail_item) -> list:
    """メール本文からURLを抽出する。"""
    try:
        body = mail_item.Body or ""
        return _URL_PATTERN.findall(body)
    except Exception:
        return []


# ===== 取引先コード抽出 =====

def extract_client_code(subject: str, known_codes: list) -> str:
    """
    メール件名から取引先コードを抽出する。
    known_codes に含まれるコードが件名に見つかれば返す。
    長いコードを先にマッチさせる（"A001" と "A00" の両方あるケース対策）。
    見つからなければ空文字を返す。
    """
    if not subject or not known_codes:
        return ""
    # 長い順にソートしてマッチ（部分一致の誤爆防止）
    for code in sorted(known_codes, key=len, reverse=True):
        if code in subject:
            return code
    return ""


# ===== メールボックス接続 =====

def _get_mailbox_root(namespace):
    """共有メールボックスまたは個人メールボックスのルートを返す。"""
    if SHARED_MAILBOX_NAME:
        recipient = namespace.CreateRecipient(SHARED_MAILBOX_NAME)
        recipient.Resolve()
        if not recipient.Resolved:
            raise RuntimeError(
                f"共有メールボックスが解決できません: {SHARED_MAILBOX_NAME}"
            )
        return namespace.GetSharedDefaultFolder(recipient, 6).Parent
    return namespace.GetDefaultFolder(6).Parent


def get_outlook_folder():
    """
    Outlookに接続し、設定されたフォルダオブジェクトを返す。
    Returns: (folder, mailbox_name, folder_path)
    """
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")

    root = _get_mailbox_root(namespace)
    mailbox_name = SHARED_MAILBOX_NAME or root.Name

    folder = root
    for name in OUTLOOK_FOLDER_PATH.split("/"):
        name = name.strip()
        if name:
            folder = folder.Folders.Item(name)

    logger.info("Outlookフォルダに接続: [%s] %s (%d件)",
                mailbox_name, OUTLOOK_FOLDER_PATH, folder.Items.Count)
    return folder, mailbox_name, OUTLOOK_FOLDER_PATH


def match_subject(email_subject: str) -> bool:
    """メール件名がフィルタに一致するか判定する。"""
    subject = (email_subject or "").strip()
    if SUBJECT_MATCH_MODE == "exact":
        return subject == SUBJECT_FILTER
    elif SUBJECT_MATCH_MODE == "startswith":
        return subject.startswith(SUBJECT_FILTER)
    else:  # "contains"
        return SUBJECT_FILTER.lower() in subject.lower()


# ===== 添付ファイル保存 =====

def save_attachments(mail_item):
    """
    メールの添付ファイルを保存する。
    Returns: (件数, カンマ区切りファイル名, 保存先フォルダ, カンマ区切り種類)
    """
    attachments = mail_item.Attachments
    count = attachments.Count
    if count == 0:
        return 0, "", "", ""

    received = mail_item.ReceivedTime
    date_str = datetime(
        received.year, received.month, received.day
    ).strftime("%Y-%m-%d")
    save_folder = os.path.join(ATTACHMENT_SAVE_DIR, date_str)
    os.makedirs(save_folder, exist_ok=True)

    saved_names = []
    att_types = []
    for i in range(1, count + 1):
        attachment = attachments.Item(i)
        filename = _sanitize_filename(attachment.FileName)
        att_type = _classify_attachment(filename)
        att_types.append(att_type)
        filepath = os.path.join(save_folder, filename)

        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{base}_{timestamp}{ext}"
            filepath = os.path.join(save_folder, filename)

        attachment.SaveAsFile(filepath)
        saved_names.append(filename)
        logger.info("添付ファイル保存: %s [%s] -> %s",
                     filename, att_type, save_folder)

    return (count, ", ".join(saved_names),
            save_folder, ", ".join(att_types))


# ===== 安定メッセージID取得 =====

def _get_internet_message_id(mail_item) -> str:
    """Internet Message-ID（RFC 2822）を取得する。EntryIDより安定。"""
    try:
        PR_INTERNET_MESSAGE_ID = (
            "http://schemas.microsoft.com/mapi/proptag/0x1035001E"
        )
        return mail_item.PropertyAccessor.GetProperty(
            PR_INTERNET_MESSAGE_ID
        ) or ""
    except Exception:
        return ""


def _get_conversation_id(mail_item) -> str:
    """ConversationID（スレッド識別用）を取得する。"""
    try:
        return mail_item.ConversationID or ""
    except Exception:
        return ""


# ===== Restrict フィルタ生成 =====

def _build_restrict_filter(last_run_time: str) -> str:
    """
    Outlook Items.Restrict 用のフィルタ文字列を生成する。
    last_run_time があればそこ - safety_margin 以降、
    なければ SCAN_LAST_N_DAYS 日前以降。
    """
    if last_run_time:
        # last_run_time: "2026-02-11 10:00:00"
        base = datetime.strptime(last_run_time, "%Y-%m-%d %H:%M:%S")
        since = base - timedelta(minutes=SCAN_SAFETY_MARGIN_MINUTES)
    else:
        since = datetime.now() - timedelta(days=SCAN_LAST_N_DAYS)

    # Outlook Restrict の日時書式: "MM/DD/YYYY HH:MM AM/PM"
    since_str = since.strftime("%m/%d/%Y %I:%M %p")
    restrict = f"[ReceivedTime] >= '{since_str}'"
    logger.info("Restrictフィルタ: %s", restrict)
    return restrict


# ===== 受信トレイ走査 =====

def scan_inbox(last_run_time: str = ""):
    """
    受信トレイを走査し、件名フィルタに一致するメールをyieldする。
    last_run_time: 前回実行時刻（Restrict用）。空文字なら SCAN_LAST_N_DAYS で代替。
    Yields: dict with mail metadata + mail_item
    """
    folder, mailbox_name, folder_path = get_outlook_folder()

    # --- Restrict で時間範囲を絞る ---
    restrict_filter = _build_restrict_filter(last_run_time)
    items = folder.Items.Restrict(restrict_filter)
    items.Sort("[ReceivedTime]", True)  # 新しい順

    yielded = 0

    for item in items:
        if yielded >= SCAN_MAX_ITEMS:
            logger.warning("スキャン上限 %d 件に到達、打ち切り",
                           SCAN_MAX_ITEMS)
            break

        try:
            if item.Class != 43:
                continue

            if not match_subject(item.Subject):
                continue

            received = item.ReceivedTime
            received_dt = datetime(
                received.year, received.month, received.day,
                received.hour, received.minute, received.second
            )

            yielded += 1
            yield {
                "message_id": item.EntryID,
                "internet_message_id": _get_internet_message_id(item),
                "conversation_id": _get_conversation_id(item),
                "mailbox": mailbox_name,
                "folder_path": folder_path,
                "sender": item.SenderName or "",
                "sender_email": item.SenderEmailAddress or "",
                "sender_smtp": _resolve_sender_smtp(item),
                "reply_to": _get_reply_to(item),
                "to_recipients": _get_recipients_str(item, "to"),
                "cc_recipients": _get_recipients_str(item, "cc"),
                "subject": item.Subject or "",
                "received_date": received_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "mail_item": item,
            }

        except pywintypes.com_error as e:
            logger.error("COMエラー: %s", e)
            continue
        except Exception as e:
            logger.error("予期しないエラー: %s", e)
            continue

    logger.info("Restrict結果: %d件が件名フィルタに一致", yielded)
