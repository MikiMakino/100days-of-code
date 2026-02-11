"""
Day 87 - File Processor
========================
添付ファイル（Excel/PDF）を開き、ファイル名末尾5桁の取引先コードが
A列（または表の1列目）に何件含まれるかカウントしてDBに記録する。

使い方:
  python file_processor.py --folder attachments/2026-02-11/
  python file_processor.py --folder attachments/2026-02-11/ --list
"""
import os
import sys
import argparse
import logging
from pathlib import Path

import openpyxl

from config import (
    BASE_DIR, LOG_FILE, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT,
    FILE_PROCESS_EXTENSIONS, TESSERACT_CMD, POPPLER_PATH,
    OCR_LANG, OCR_DPI,
)
from database import (
    init_db, get_client_codes, find_client_by_code,
    save_file_result, is_file_processed, fetch_file_results,
    log_event,
)

logger = logging.getLogger(__name__)


# ===== ユーティリティ =====

def extract_client_code_from_filename(file_path: str) -> str:
    """ファイル名（拡張子除く）の末尾5文字を取引先コードとして返す。"""
    stem = Path(file_path).stem
    if len(stem) < 5:
        return stem
    return stem[-5:]


# ===== Excel 処理 =====

def count_code_in_excel(file_path: str, client_code: str) -> int:
    """
    Excelファイルの全シートのA列で client_code の出現回数をカウントする。
    """
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    count = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_col=1, max_col=1, values_only=True):
            cell_value = row[0]
            if cell_value is not None and str(cell_value).strip() == client_code:
                count += 1
    wb.close()
    return count


# ===== PDF 処理 =====

def count_code_in_pdf_text(file_path: str, client_code: str) -> tuple:
    """
    テキスト埋め込みPDFから表を抽出し、1列目で client_code をカウントする。
    戻り値: (count, "text") または (None, None) テキスト抽出できない場合。
    """
    import pdfplumber

    count = 0
    has_table = False

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                has_table = True
                for table in tables:
                    for row in table:
                        if row and row[0] is not None:
                            if str(row[0]).strip() == client_code:
                                count += 1

    if has_table:
        return count, "text"
    return None, None


def count_code_in_pdf_ocr(file_path: str, client_code: str) -> int:
    """
    画像PDFをOCRで読み取り、全文から client_code の出現回数をカウントする。
    結果は「カウント - 1」を返す（ヘッダー/タイトル分を除外）。
    """
    import pytesseract
    from pdf2image import convert_from_path

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

    images = convert_from_path(
        file_path, dpi=OCR_DPI, poppler_path=POPPLER_PATH
    )

    full_text = ""
    for img in images:
        text = pytesseract.image_to_string(img, lang=OCR_LANG)
        full_text += text + "\n"

    raw_count = full_text.count(client_code)
    result = max(0, raw_count - 1)
    return result


def process_pdf(file_path: str, client_code: str) -> tuple:
    """
    PDFを処理する。テキスト抽出を試み、失敗時はOCRにフォールバック。
    戻り値: (record_count, pdf_type)
    """
    count, pdf_type = count_code_in_pdf_text(file_path, client_code)
    if count is not None:
        return count, pdf_type

    count = count_code_in_pdf_ocr(file_path, client_code)
    return count, "image"


# ===== メイン処理 =====

def process_folder(folder_path: str):
    """指定フォルダ内のExcel/PDFファイルを処理する。"""
    folder = os.path.abspath(folder_path)
    if not os.path.isdir(folder):
        logger.error("フォルダが見つかりません: %s", folder)
        print(f"エラー: フォルダが見つかりません: {folder}")
        return

    known_codes = get_client_codes()
    files = sorted([
        f for f in os.listdir(folder)
        if Path(f).suffix.lower() in FILE_PROCESS_EXTENSIONS
    ])

    if not files:
        logger.info("処理対象のファイルがありません: %s", folder)
        print(f"処理対象のファイルがありません: {folder}")
        return

    log_event("", "FILE_SCAN_START", "INFO", "file_processor",
              f"folder={folder} files={len(files)}")

    stats = {"processed": 0, "excel": 0, "pdf_text": 0,
             "pdf_ocr": 0, "skipped": 0, "errors": 0}

    for filename in files:
        file_path = os.path.join(folder, filename)
        file_id = filename  # イベントログの message_id として使用

        # 重複チェック
        if is_file_processed(filename, folder):
            logger.info("処理済みスキップ: %s", filename)
            log_event(file_id, "FILE_SKIP_DUPLICATE", "INFO",
                      "file_processor", f"file={filename}")
            stats["skipped"] += 1
            continue

        # 取引先コード抽出
        client_code = extract_client_code_from_filename(filename)
        if client_code in known_codes:
            log_event(file_id, "FILE_CLIENT_MATCH", "INFO",
                      "file_processor", f"code={client_code} file={filename}")
        else:
            log_event(file_id, "FILE_CLIENT_NOT_FOUND", "WARN",
                      "file_processor",
                      f"code={client_code} file={filename}")

        ext = Path(filename).suffix.lower()
        try:
            if ext in (".xlsx", ".xlsm"):
                # Excel処理
                record_count = count_code_in_excel(file_path, client_code)
                file_type = "excel"
                pdf_type = None
                log_event(file_id, "FILE_EXCEL_OK", "INFO",
                          "file_processor",
                          f"count={record_count} code={client_code}")
                stats["excel"] += 1

            elif ext == ".pdf":
                # PDF処理（テキスト → OCR フォールバック）
                record_count, pdf_type = process_pdf(file_path, client_code)
                file_type = "pdf"
                event_type = ("FILE_PDF_TEXT_OK" if pdf_type == "text"
                              else "FILE_PDF_OCR_OK")
                log_event(file_id, event_type, "INFO",
                          "file_processor",
                          f"count={record_count} type={pdf_type} "
                          f"code={client_code}")
                if pdf_type == "text":
                    stats["pdf_text"] += 1
                else:
                    stats["pdf_ocr"] += 1
            else:
                continue

            # DB登録
            save_file_result(
                client_code=client_code if client_code in known_codes else "",
                file_name=filename,
                file_type=file_type,
                pdf_type=pdf_type,
                record_count=record_count,
                source_folder=folder,
            )
            stats["processed"] += 1
            logger.info("[%s] %s → %d件", file_type.upper(), filename,
                        record_count)

        except Exception as e:
            logger.error("ファイル処理失敗: %s — %s", filename, e)
            log_event(file_id, "FILE_ERROR", "ERROR",
                      "file_processor", f"file={filename} error={e}")
            stats["errors"] += 1

    log_event("", "FILE_SCAN_END", "INFO", "file_processor",
              f"processed={stats['processed']} skipped={stats['skipped']} "
              f"errors={stats['errors']}")

    # サマリー表示
    print(f"\n=== ファイル処理完了 ===")
    print(f"フォルダ: {folder}")
    print(f"処理: {stats['processed']}件 "
          f"(Excel: {stats['excel']}, "
          f"PDF-text: {stats['pdf_text']}, "
          f"PDF-OCR: {stats['pdf_ocr']})")
    print(f"スキップ: {stats['skipped']}件")
    print(f"エラー: {stats['errors']}件")


def show_results(folder_path: str = None):
    """処理結果一覧を表示する。"""
    source = os.path.abspath(folder_path) if folder_path else None
    results = fetch_file_results(source)

    if not results:
        print("処理結果がありません")
        return

    print(f"\n{'コード':<8} {'社名':<16} {'ファイル名':<36} "
          f"{'種別':<8} {'PDF':<6} {'件数':>5}  {'処理日時'}")
    print("-" * 120)
    for r in results:
        print(f"{r['client_code'] or '':.<8} "
              f"{(r['company_name'] or '')[:14]:<16} "
              f"{r['file_name'][:34]:<36} "
              f"{r['file_type']:<8} "
              f"{(r['pdf_type'] or '-'):<6} "
              f"{r['record_count']:>5}  "
              f"{r['processed_at']}")


def setup_logging():
    """ロギングを設定する。"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

    if not root_logger.handlers:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        root_logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        root_logger.addHandler(ch)


def main():
    parser = argparse.ArgumentParser(
        description="添付ファイル（Excel/PDF）の取引先コード件数をカウントしてDBに記録する"
    )
    parser.add_argument(
        "--folder", required=True,
        help="処理対象フォルダ（例: attachments/2026-02-11/）"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="処理結果一覧を表示して終了"
    )
    args = parser.parse_args()

    setup_logging()
    init_db()

    if args.list:
        show_results(args.folder)
    else:
        process_folder(args.folder)


if __name__ == "__main__":
    main()
