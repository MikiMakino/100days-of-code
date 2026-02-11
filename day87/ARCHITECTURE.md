# Day 87: Outlook Email Monitor & 管理台帳 — アーキテクチャ

## 概要

特定の件名を持つメールを自動監視し、添付ファイルの保存・台帳記録・処理ログの記録を行う業務アプリケーション。
**取引先マスタ**を基盤とし、メール件名に含まれる取引先コードで自動紐づけを行う。
保存された添付ファイル（Excel/PDF）を開き、取引先コードの件数をカウントしてDBに記録する機能も備える。

- **メール監視**: Windows タスクスケジューラにより **5分おき** に自動実行
- **ファイル処理**: ZIP展開・Web取得後、人が手動でCLI実行

---

## システム全体図

```
                    取引先マスタ Excel
                    (client_master.xlsx)
                          │
                          ▼
                  ┌───────────────┐
                  │client_import  │ ← 初回 or マスタ更新時に手動実行
                  │.py            │    python client_import.py
                  └───────┬───────┘
                          │ UPSERT
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Windows タスクスケジューラ                       │
│                   (5分おきに自動起動)                              │
│                                                                 │
│   register_task.ps1 で登録                                       │
│   タスク名: Day87_EmailMonitor                                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │ 起動
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     email_monitor.py                             │
│                    (メール監視オーケストレーター)                    │
│                                                                 │
│  1. ログ設定（ファイル＋コンソール）                                │
│  2. DB初期化                                                    │
│  3. 取引先コード一覧をDBから取得（マッチング用）                    │
│  4. 前回実行時刻を取得 → Restrictフィルタで差分スキャン             │
│  5. メール処理ループ:                                            │
│     件名から取引先コード抽出→添付保存→台帳登録→イベントログ        │
│  6. 最終実行時刻を記録                                            │
│  7. 新着があればExcel自動エクスポート（4シート）                    │
└──────┬──────────┬──────────┬──────────┬─────────────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐┌──────────┐┌──────────┐┌──────────┐
│config.py ││outlook_  ││database  ││excel_    │
│          ││client.py ││.py       ││export.py │
│ 全設定値  ││ Outlook  ││ SQLite   ││ Excel    │
│ 一箇所管理││ COM操作  ││ 5テーブル ││ 4シート  │
└──────────┘└────┬─────┘└────┬─────┘└────┬─────┘
                 │           │           │
                 ▼           ▼           ▼
           ┌──────────┐┌──────────┐┌──────────┐
           │ Outlook  ││ email_   ││ exports/ │
           │ 受信トレイ││ ledger   ││ *.xlsx   │
           │          ││ .db      ││          │
           └──────────┘└──────────┘└──────────┘

                     ↓ 添付ファイル保存後 ↓

┌─────────────────────────────────────────────────────────────────┐
│                     file_processor.py                            │
│                    (ファイル処理 — 手動CLI実行)                    │
│                                                                 │
│  python file_processor.py --folder attachments/2026-02-11/      │
│                                                                 │
│  1. フォルダ内の Excel/PDF をスキャン                              │
│  2. ファイル名末尾5桁 → 取引先コード抽出                           │
│  3. Excel: A列でコードカウント                                    │
│  4. PDF-text: pdfplumber で表抽出 → 1列目カウント                 │
│  5. PDF-image: Tesseract OCR → 全文カウント - 1                  │
│  6. file_processing_results に件数を記録                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## ファイル構成と役割

```
day87/
├── email_monitor.py    ← メール監視エントリポイント（CLIオーケストレーション）
├── file_processor.py   ← ファイル処理（Excel/PDFの件数カウント — 手動CLI実行）
├── config.py           ← 全設定（件名フィルタ、共有MB、パス、OCR、取引先列定義等）
├── outlook_client.py   ← Outlook COM操作（走査、添付保存、URL抽出、SMTP解決、コード抽出）
├── database.py         ← SQLite 5テーブル管理（取引先・台帳・ファイル結果・ログ・メタ）
├── excel_export.py     ← Excel 4シート出力（台帳・ログ・取引先・ファイル処理結果）
├── client_import.py    ← 取引先マスタExcel→SQLiteインポート（UPSERT対応）
├── register_task.ps1   ← タスクスケジューラ登録スクリプト
├── requirements.txt    ← pywin32, openpyxl, pdfplumber, pytesseract, pdf2image, Pillow
│
├── client_master.xlsx  ← (手動配置) 取引先マスタExcel
├── email_ledger.db     ← (実行時に自動生成) SQLiteデータベース
├── email_monitor.log   ← (実行時に自動生成) ログファイル
├── attachments/        ← (実行時に自動生成) 添付ファイル保存先
│   └── 2026-02-11/     ←   日付別サブフォルダ（file_processor.py の対象）
│       ├── report_A0012.xlsx
│       └── invoice_B0034.pdf
└── exports/            ← (実行時に自動生成) Excelエクスポート先
    └── email_ledger_20260211_100500.xlsx
```

---

## データベース構造（5テーブル）

```
┌─────────────────────────────────────────────────────────────┐
│                     email_ledger.db                          │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ clients（取引先マスタ）                                 │  │
│  │ 取引先1社につき1行                                      │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ code (PRIMARY KEY)  ← 取引先コード                     │  │
│  │ company_name        ← 社名                            │  │
│  │ month_1             ← 実施月1                          │  │
│  │ month_2             ← 実施月2                          │  │
│  │ cs_category         ← CS区分                          │  │
│  │ created_at          ← 登録日時                         │  │
│  │ updated_at          ← 更新日時                         │  │
│  └───────────────────────────────────────────────────────┘  │
│       ▲                                                     │
│       │ FOREIGN KEY (client_code → clients.code)            │
│       │                                                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ processed_emails（メール台帳）                          │  │
│  │ メール1通につき1行                                      │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ stable_id (UNIQUE)  ← 重複排除キー                     │  │
│  │ client_code          ← 取引先コード（FK → clients）     │  │
│  │ message_id          ← Outlook EntryID                 │  │
│  │ internet_message_id ← RFC 2822 Message-ID（安定）      │  │
│  │ conversation_id     ← スレッド識別                     │  │
│  │ mailbox / folder_path                                 │  │
│  │ sender / sender_email / sender_smtp                   │  │
│  │ reply_to / to_recipients / cc_recipients              │  │
│  │ subject / received_date                               │  │
│  │ attachment_count / attachment_names / attachment_types │  │
│  │ save_folder / url_count / urls                        │  │
│  │ processed_at                                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ file_processing_results（ファイル処理結果）             │  │
│  │ ファイル1つにつき1行                                    │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ client_code (FK)    ← 取引先コード（FK → clients）     │  │
│  │ file_name           ← ファイル名                       │  │
│  │ file_type           ← "excel" / "pdf"                 │  │
│  │ pdf_type            ← "text" / "image" (NULLはExcel)  │  │
│  │ record_count        ← A列の取引先コード件数             │  │
│  │ source_folder       ← 処理元フォルダパス               │  │
│  │ processed_at        ← 処理日時                        │  │
│  │ UNIQUE(file_name, source_folder) ← 重複防止           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ processing_events（監査ログ）                           │  │
│  │ メール/ファイル処理の各ステップを記録                     │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ message_id  ← どのメール/ファイルの処理か               │  │
│  │ event_time  ← いつ起きたか                             │  │
│  │ event_type  ← SCAN_MATCH / FILE_EXCEL_OK / ERROR ...  │  │
│  │ level       ← INFO / WARN / ERROR                     │  │
│  │ source      ← monitor / file_processor / ...          │  │
│  │ detail      ← 自由テキスト（例外内容、保存先等）        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ run_metadata（実行メタデータ）                          │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ key = "last_run_time"                                 │  │
│  │ value = "2026-02-11 10:05:00"                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 取引先マスタの仕組み

```
┌─────────────────────┐    python client_import.py    ┌──────────────┐
│ client_master.xlsx  │ ─────────────────────────────→│ clients テーブル│
│                     │         UPSERT                │ (SQLite)      │
│ コード | 社名 | ... │    (既存は上書き更新)           └───────┬──────┘
└─────────────────────┘                                       │
                                                              │ get_client_codes()
                                                              ▼
                                              ┌───────────────────────────┐
                                              │ email_monitor.py          │
                                              │ 件名からコード抽出         │
                                              │ 長い順にマッチ → "A001"    │
                                              ├───────────────────────────┤
                                              │ file_processor.py         │
                                              │ ファイル名末尾5桁 → コード │
                                              │ 例: report_A0012.xlsx     │
                                              │     → "A0012"            │
                                              └───────────────────────────┘
```

---

## ファイル処理フロー（file_processor.py）

```
python file_processor.py --folder attachments/2026-02-11/
│
▼
[1] フォルダ内の .xlsx / .xlsm / .pdf をリストアップ
│
▼
[2] 各ファイルに対して:
│
│   ファイル名: 月次レポート_A0012.xlsx
│          末尾5桁 → "A0012"
│                  │
│                  ▼
│   ┌─────────────────────────┐
│   │ clients テーブルに存在？  │
│   │ YES → FILE_CLIENT_MATCH │
│   │ NO  → FILE_CLIENT_NOT_FOUND (WARN)
│   └────────┬────────────────┘
│            │
│            ▼
│   ┌─────────────────────────────────────┐
│   │ Excel (.xlsx/.xlsm)                  │
│   │ → openpyxl で全シートのA列を走査     │
│   │ → client_code 完全一致をカウント      │
│   │ → FILE_EXCEL_OK                      │
│   ├─────────────────────────────────────┤
│   │ PDF (.pdf) — テキスト埋め込み         │
│   │ → pdfplumber で表抽出                │
│   │ → 1列目から client_code カウント      │
│   │ → FILE_PDF_TEXT_OK                   │
│   ├─────────────────────────────────────┤
│   │ PDF (.pdf) — 画像（テキスト抽出失敗） │
│   │ → pdf2image で画像変換               │
│   │ → pytesseract (jpn+eng) で OCR      │
│   │ → 全文から client_code カウント       │
│   │ → カウント - 1 = 件数                │
│   │ → FILE_PDF_OCR_OK                   │
│   └────────┬────────────────────────────┘
│            │
│            ▼
│   file_processing_results に INSERT
│   processing_events にログ記録
│
▼
[3] 処理サマリー表示
    処理: 5件 (Excel: 3, PDF-text: 1, PDF-OCR: 1) スキップ: 0 エラー: 0
```

**なぜ手動CLI実行か:**
- ZIP展開やWebダウンロードは人間の作業
- フォルダの準備完了は人間しか判断できない
- 日付フォルダを指定して柔軟に実行可能
- email_monitor.py（5分自動）とは独立した処理として明確に分離

---

## メール監視フロー（email_monitor.py — 1回の実行）

```
タスクスケジューラが python email_monitor.py を起動
│
▼
[1] ログ設定（ファイル + コンソール）
│
▼
[2] DB初期化（テーブルが無ければ作成）
│
▼
[3] 取引先コード一覧を DB から取得（マッチング用）
│
▼
[4] 前回実行時刻を取得
│
├── 初回: last_run_time = なし → 直近2日分を全件スキャン
│
└── 2回目以降: last_run_time = "2026-02-11 10:05:00"
    │           → 10:05 - 10分マージン = 09:55 以降だけスキャン
    ▼
[5] Outlook COM に接続
    │
    ├── 共有メールボックス指定あり → CreateRecipient → GetSharedDefaultFolder
    └── 個人メールボックス        → GetDefaultFolder(6)
    │
    ▼
[6] Items.Restrict("[ReceivedTime] >= '02/11/2026 09:55 AM'")
    │   ↑ Restrict で時間範囲を絞ってから走査（効率化）
    ▼
[7] 件名フィルタに一致するメールだけを処理
    │
    ▼
[8] 各メールに対して:
    │
    │   ┌──────────────────────────────────────────────────┐
    │   │  stable_id を生成                                 │
    │   │  (Internet Message-ID 優先, EntryID フォールバック) │
    │   └──────────┬───────────────────────────────────────┘
    │              │
    │              ▼
    │   ┌──────────────────────┐    YES
    │   │  DB に stable_id が  │ ──────→ スキップ (SKIP_DUPLICATE)
    │   │  既に存在する？       │          ログに記録して次のメールへ
    │   └──────────┬───────────┘
    │         NO   │
    │              ▼
    │   ┌──────────────────────────────────────────────┐
    │   │  件名から取引先コード抽出                       │
    │   │  → CLIENT_MATCH (見つかった場合)               │
    │   │  → CLIENT_NOT_FOUND (見つからない場合 / WARN)  │
    │   └──────────┬───────────────────────────────────┘
    │              │
    │              ▼
    │   ┌──────────────────────┐
    │   │  添付ファイル保存      │
    │   │  attachments/日付/    │
    │   ├──────────────────────┤
    │   │ 成功 → ATTACH_SAVE_OK │
    │   │ なし → ATTACH_NONE    │
    │   │ 失敗 → ATTACH_SAVE_FAIL (台帳登録は続行)
    │   └──────────┬───────────┘
    │              │
    │              ▼
    │   ┌──────────────────────┐
    │   │  本文から URL 抽出    │
    │   │  → URL_DETECTED      │
    │   └──────────┬───────────┘
    │              │
    │              ▼
    │   ┌──────────────────────┐
    │   │  台帳に INSERT        │
    │   │  (必ず実行)           │
    │   │  client_code 付き    │
    │   ├──────────────────────┤
    │   │ 成功 → DB_INSERT_OK   │
    │   │ 重複 → DB_INSERT_DUP  │
    │   └──────────────────────┘
    │
    ▼ (全メール処理完了)
│
[9] 最終実行時刻を run_metadata に記録
│
▼
[10] 新着があれば Excel 自動エクスポート（4シート）
    │
    ├── シート1「管理台帳」: 台帳レコード＋取引先情報（LEFT JOIN）
    ├── シート2「処理ログ」: イベントログ一覧（ERROR=赤, WARN=黄）
    ├── シート3「取引先マスタ」: 登録済み取引先一覧
    └── シート4「ファイル処理結果」: ファイル件数カウント結果
│
▼
終了（次の5分後にタスクスケジューラが再起動）
```

---

## イベントログ一覧

### メール監視イベント (email_monitor.py)

```
event_time           event_type        level   source          detail
─────────────────────────────────────────────────────────────────────────────
2026-02-11 10:05:00  SCAN_START        INFO    monitor         filter=月次レポート ...
2026-02-11 10:05:01  SCAN_MATCH        INFO    monitor         subject=月次レポート_A001_2月
2026-02-11 10:05:01  CLIENT_MATCH      INFO    monitor         client_code=A001
2026-02-11 10:05:01  ATTACH_SAVE_OK    INFO    outlook_client  count=2 types=excel, pdf
2026-02-11 10:05:02  URL_DETECTED      INFO    monitor         count=1 urls=https://...
2026-02-11 10:05:02  DB_INSERT_OK      INFO    database        client=A001 att=2 urls=1
2026-02-11 10:05:02  SCAN_END          INFO    monitor         processed=1 skipped=0
```

### ファイル処理イベント (file_processor.py)

```
event_time           event_type           level   source          detail
─────────────────────────────────────────────────────────────────────────────
2026-02-11 14:00:00  FILE_SCAN_START      INFO    file_processor  folder=.../2026-02-11 files=5
2026-02-11 14:00:01  FILE_CLIENT_MATCH    INFO    file_processor  code=A0012 file=report_A0012.xlsx
2026-02-11 14:00:02  FILE_EXCEL_OK        INFO    file_processor  count=15 code=A0012
2026-02-11 14:00:03  FILE_CLIENT_MATCH    INFO    file_processor  code=B0034 file=invoice_B0034.pdf
2026-02-11 14:00:05  FILE_PDF_TEXT_OK     INFO    file_processor  count=8 type=text code=B0034
2026-02-11 14:00:06  FILE_CLIENT_MATCH    INFO    file_processor  code=C0056 file=scan_C0056.pdf
2026-02-11 14:00:10  FILE_PDF_OCR_OK      INFO    file_processor  count=4 type=image code=C0056
2026-02-11 14:00:10  FILE_SCAN_END        INFO    file_processor  processed=3 skipped=0 errors=0
```

---

## Excel 出力の構成（4シート）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  email_ledger_20260211_100500.xlsx                                         │
│                                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────────┐           │
│  │ 管理台帳  │ │ 処理ログ  │ │ 取引先マスタ  │ │ ファイル処理結果│ ← 4シート │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ └───────┬────────┘           │
│       ▼            ▼              ▼                 ▼                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────────┐           │
│  │ 21カラム  │ │ 7カラム   │ │ 7カラム       │ │ 9カラム         │           │
│  │ ID,取引先│ │ ID,日時,  │ │ コード,社名,  │ │ ID,コード,社名,│           │
│  │ コード,  │ │ 種別,     │ │ 実施月1/2,    │ │ ファイル名,    │           │
│  │ 社名,... │ │ レベル,...│ │ CS区分,...    │ │ 種別,PDF種別,  │           │
│  │          │ │ ERROR→赤 │ │              │ │ 件数,フォルダ, │           │
│  │          │ │ WARN →黄 │ │              │ │ 処理日時       │           │
│  └──────────┘ └──────────┘ └──────────────┘ └────────────────┘           │
│                                                                          │
│  ※ 管理台帳・ファイル処理結果はそれぞれ clients を LEFT JOIN               │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 重複排除の仕組み

### メール（processed_emails）
```
    Internet Message-ID あり？
    │
    YES ─────┴───── NO
    │                │
    ▼                ▼
"inet:<msg-id>"   "eid:<EntryID>"
    │                │
    └───────┬────────┘
            ▼
       stable_id (UNIQUE制約)
```

### ファイル（file_processing_results）
```
    UNIQUE(file_name, source_folder)
    → 同一フォルダ内の同一ファイルは1回だけ処理
    → 再実行時は FILE_SKIP_DUPLICATE でスキップ
```

---

## Restrict 方式による効率化

```
                    ┌─────────────────────────────────┐
                    │      受信トレイ (2000件)          │
    従来方式        │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■ │ ← 全件走査
                    └─────────────────────────────────┘

                    ┌─────────────────────────────────┐
                    │                          ┌─┐    │
    Restrict方式    │                          │3│    │ ← 差分だけ走査
                    │                          └─┘    │
                    │         - 10分マージン            │
                    └─────────────────────────────────┘
```

---

## タスクスケジューラの設定

```
┌─────────────────────────────────────────────────────┐
│  タスク名: Day87_EmailMonitor                        │
│                                                     │
│  トリガー:  5分おきに繰り返し（無期限）                │
│  操作:      python.exe email_monitor.py              │
│  作業フォルダ: day87/                                 │
│  条件:      ユーザーがログオンしている場合のみ          │
│             (← Outlook COM に必要)                   │
│  設定:      バッテリー駆動中も実行                     │
│             多重実行は無視 (IgnoreNew)                │
│             実行時間上限 10分                         │
└─────────────────────────────────────────────────────┘

登録:   powershell -ExecutionPolicy Bypass -File register_task.ps1
確認:   Get-ScheduledTask -TaskName 'Day87_EmailMonitor'
手動:   Start-ScheduledTask -TaskName 'Day87_EmailMonitor'
解除:   Unregister-ScheduledTask -TaskName 'Day87_EmailMonitor' -Confirm:$false
```

---

## 送信元の解決（3段階フォールバック）

```
  ┌──────────────────────────────────────┐
  │ PropertyAccessor で SMTP を直接取得   │ ← 最も安定
  │ (MAPI プロパティ 0x39FE001E)         │
  └──────────────┬───────────────────────┘
            失敗 │
                 ▼
  ┌──────────────────────────────────────┐
  │ Sender.GetExchangeUser()             │
  │ → PrimarySmtpAddress                 │ ← Exchange環境で有効
  └──────────────┬───────────────────────┘
            失敗 │
                 ▼
  ┌──────────────────────────────────────┐
  │ SenderEmailAddress をそのまま使用     │ ← X500形式の場合あり
  └──────────────────────────────────────┘
```

---

## 使い方

```bash
# 1. 依存関係インストール
pip install pywin32 openpyxl pdfplumber pytesseract pdf2image Pillow

# 2. システム要件（ファイル処理用）
#    - Tesseract OCR (jpn言語パック含む)
#    - Poppler (pdf2image用)

# 3. 取引先マスタをインポート（初回 or マスタ更新時）
python client_import.py                     # デフォルトの client_master.xlsx から
python client_import.py --file other.xlsx   # 別ファイル指定
python client_import.py --list              # 登録済み取引先一覧

# 4. config.py の SUBJECT_FILTER を実際の件名に変更

# 5. メール監視（自動 or 手動実行）
python email_monitor.py              # メール処理（添付保存＋DB記録＋Excel出力）
python email_monitor.py --export     # Excelエクスポートのみ
python email_monitor.py --scan-only  # 添付保存なしでメタデータ記録のみ

# 6. タスクスケジューラに登録（5分おき自動実行）
powershell -ExecutionPolicy Bypass -File register_task.ps1

# 7. ファイル処理（ZIP展開・Web取得後に手動実行）
python file_processor.py --folder attachments/2026-02-11/       # 件数カウント実行
python file_processor.py --folder attachments/2026-02-11/ --list # 処理結果一覧
```

---

## 技術スタック

| 技術 | 用途 |
|------|------|
| Python 3.8+ | アプリケーション本体 |
| pywin32 (`win32com.client`) | Outlook COM 自動化 |
| SQLite (`sqlite3`) | 取引先・台帳・ファイル結果・ログ・メタデータ保存 |
| openpyxl | Excel インポート＋エクスポート＋A列カウント |
| pdfplumber | PDF テキスト・表抽出 |
| pytesseract | 画像PDF の OCR (Tesseract連携) |
| pdf2image + Pillow | PDF → 画像変換 (OCR前処理) |
| Python `logging` | ファイル＋コンソール ログ |
| Python `argparse` | CLI インターフェース |
| Windows タスクスケジューラ | 5分おき定期実行（メール監視） |
| PowerShell | タスク登録スクリプト |
