"""
Day 87 - Outlook Email Monitor & Management Ledger
====================================================
Outlookの受信トレイを監視し、特定件名のメールから
添付ファイルを保存、SQLiteに記録、Excelにエクスポートする。

件名に含まれる取引先コードで自動紐づけ。
処理は必ず台帳+イベントログの両方に記録される。
添付保存が失敗してもスキップせず台帳には登録する。

タスクスケジューラで5分おきに実行する想定。

Usage:
    pip install pywin32 openpyxl
    python client_import.py              # 取引先マスタをインポート（初回）
    python email_monitor.py              # メール処理（1回実行）
    python email_monitor.py --export     # Excelエクスポートのみ
    python email_monitor.py --scan-only  # 添付保存なしでメタデータ記録
"""
import sys
import logging
import argparse

from config import LOG_FILE, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT, SUBJECT_FILTER
from database import (
    init_db, is_processed, save_record, log_event,
    make_stable_id, get_last_run_time, save_last_run_time,
    get_client_codes,
)
from outlook_client import (
    scan_inbox, save_attachments, extract_urls, extract_client_code,
)
from excel_export import export_to_excel


def setup_logging():
    """ファイルとコンソールの両方にログを出力するよう設定する。"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))

    if root_logger.handlers:
        return

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def process_emails(scan_only=False):
    """メイン処理: 受信トレイを走査し、添付保存・DB記録を行う。"""
    logger = logging.getLogger("monitor")
    logger.info("=" * 50)
    logger.info("メールスキャン開始 (件名フィルタ: '%s')", SUBJECT_FILTER)

    # --- 取引先コード一覧をDBから取得（マッチング用） ---
    known_codes = get_client_codes()
    if known_codes:
        logger.info("取引先マスタ: %d件ロード済み", len(known_codes))
    else:
        logger.warning("取引先マスタが空です。python client_import.py で登録してください")

    # --- 前回実行時刻を取得してRestrictに渡す ---
    last_run = get_last_run_time()
    if last_run:
        logger.info("前回実行: %s （差分スキャン）", last_run)
    else:
        logger.info("初回実行（SCAN_LAST_N_DAYS で全件スキャン）")

    log_event("", "SCAN_START", "INFO", "monitor",
              f"filter={SUBJECT_FILTER} scan_only={scan_only} "
              f"last_run={last_run or 'N/A'} clients={len(known_codes)}")

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for mail in scan_inbox(last_run_time=last_run):
        msg_id = mail["message_id"]
        inet_id = mail["internet_message_id"]
        subject = mail["subject"]
        sender = mail["sender"]
        received_date = mail["received_date"]
        mail_item = mail["mail_item"]

        # --- 安定IDで重複チェック ---
        stable_id = make_stable_id(inet_id, msg_id)

        log_event(stable_id, "SCAN_MATCH", "INFO", "monitor",
                  f"subject={subject} sender={sender}")

        if is_processed(stable_id):
            skipped_count += 1
            logger.debug("処理済みのためスキップ: %s", subject)
            log_event(stable_id, "SKIP_DUPLICATE", "INFO", "monitor",
                      "既に処理済み")
            continue

        # --- 取引先コード抽出 ---
        client_code = extract_client_code(subject, known_codes)
        if client_code:
            logger.info("処理中: [%s] 取引先=%s from %s (%s)",
                        subject, client_code, sender, received_date)
            log_event(stable_id, "CLIENT_MATCH", "INFO", "monitor",
                      f"client_code={client_code}")
        else:
            logger.info("処理中: [%s] 取引先=不明 from %s (%s)",
                        subject, sender, received_date)
            log_event(stable_id, "CLIENT_NOT_FOUND", "WARN", "monitor",
                      f"subject={subject}")

        # --- 添付ファイル保存 ---
        att_count, att_names, save_folder, att_types = 0, "", "", ""
        if not scan_only:
            try:
                att_count, att_names, save_folder, att_types = \
                    save_attachments(mail_item)
                if att_count > 0:
                    log_event(stable_id, "ATTACH_SAVE_OK", "INFO",
                              "outlook_client",
                              f"count={att_count} types={att_types} "
                              f"folder={save_folder}")
                else:
                    log_event(stable_id, "ATTACH_NONE", "INFO",
                              "outlook_client", "添付ファイルなし")
            except Exception as e:
                logger.error("添付ファイル保存失敗: %s", e)
                log_event(stable_id, "ATTACH_SAVE_FAIL", "ERROR",
                          "outlook_client", str(e))
                error_count += 1

        # --- URL抽出 ---
        urls = extract_urls(mail_item)
        url_count = len(urls)
        urls_str = ", ".join(urls[:20])
        if url_count > 0:
            log_event(stable_id, "URL_DETECTED", "INFO", "monitor",
                      f"count={url_count} urls={urls_str[:500]}")

        # --- データベースに記録（必ず実行） ---
        success = save_record(
            stable_id=stable_id,
            client_code=client_code,
            message_id=msg_id,
            internet_message_id=inet_id,
            conversation_id=mail["conversation_id"],
            mailbox=mail["mailbox"],
            folder_path=mail["folder_path"],
            sender=sender,
            sender_email=mail["sender_email"],
            sender_smtp=mail["sender_smtp"],
            reply_to=mail["reply_to"],
            to_recipients=mail["to_recipients"],
            cc_recipients=mail["cc_recipients"],
            subject=subject,
            received_date=received_date,
            attachment_count=att_count,
            attachment_names=att_names,
            attachment_types=att_types,
            save_folder=save_folder,
            url_count=url_count,
            urls=urls_str,
        )

        if success:
            processed_count += 1
            logger.info("記録完了: 取引先=%s 添付%d件 URL%d件",
                        client_code or "不明", att_count, url_count)
            log_event(stable_id, "DB_INSERT_OK", "INFO", "database",
                      f"client={client_code or 'N/A'} "
                      f"att={att_count} urls={url_count}")
        else:
            skipped_count += 1
            log_event(stable_id, "DB_INSERT_DUP", "WARN", "database",
                      "重複のためINSERTスキップ")

    # --- 最終実行時刻を記録 ---
    save_last_run_time()

    logger.info("-" * 50)
    logger.info(
        "スキャン完了: %d件処理, %d件スキップ, %d件エラー",
        processed_count, skipped_count, error_count,
    )
    log_event("", "SCAN_END", "INFO", "monitor",
              f"processed={processed_count} skipped={skipped_count} "
              f"errors={error_count}")
    return processed_count


def main():
    parser = argparse.ArgumentParser(
        description="Day 87: Outlook Email Monitor & Management Ledger"
    )
    parser.add_argument(
        "--export", action="store_true",
        help="管理台帳をExcelにエクスポート",
    )
    parser.add_argument(
        "--scan-only", action="store_true",
        help="添付ファイルを保存せずメタデータのみ記録",
    )
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("main")

    logger.info("=" * 50)
    logger.info("  Day 87: Email Monitor & 管理台帳")
    logger.info("=" * 50)

    init_db()

    if args.export:
        filepath = export_to_excel()
        if filepath:
            logger.info("エクスポート完了: %s", filepath)
        else:
            logger.warning("エクスポート対象のレコードがありません")
    else:
        count = process_emails(scan_only=args.scan_only)
        logger.info("完了。%d件の新規メールを処理しました。", count)

        if count > 0:
            filepath = export_to_excel()
            if filepath:
                logger.info("自動エクスポート完了: %s", filepath)


if __name__ == "__main__":
    main()
