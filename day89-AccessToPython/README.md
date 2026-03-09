# Day 89 - Access → pandas 変換アシスタント

AccessのSQLクエリやVBAモジュールをPythonへ移行するための支援ツールです。
「まるっと完全自動変換」ではなく、**たたき台コードを素早く生成してCopilotや手修正につなげる**ことを目的としています。

---

## 機能要件

### SQL変換（`converter.py` / Streamlit Tab 1）

| 機能 | 内容 |
|---|---|
| SELECT/FROM 変換 | テーブル名から `pd.read_csv()` を生成 |
| JOIN 変換 | `LEFT JOIN` / `INNER JOIN` → `.merge(how="left"/"inner")` |
| WHERE 変換 | 等号・不等号・比較演算子・日付リテラル・`IsNull` → pandas条件式 |
| ORDER BY 変換 | `ASC` / `DESC` → `.sort_values(ascending=...)` |
| GROUP BY + 集計 | `Sum` / `Count` / `Avg` / `Max` / `Min` → `.groupby().agg()` |
| 計算列 | `列 * 列 AS 名前` → `df["名前"] = df["列"] * df["列"]` |
| `IIf` 変換 | `IIf(条件, 真, 偽)` → `np.where(条件, 真, 偽)`（括弧ネスト対応）|
| `IsNull` 変換 | → `.isna()` / `.notna()` |
| `Like` 変換 | → `.str.contains()` |
| サンプルクエリ | 5種類の代表的なクエリを内蔵 |
| コードダウンロード | 変換結果を `.py` ファイルとしてダウンロード |

### Accessエクスポート（`export_access.py` / Streamlit Tab 2）

| 機能 | 内容 |
|---|---|
| クエリ定義出力 | `SaveAsText` によるクエリオブジェクトのテキスト化 |
| VBAモジュール出力 | `SaveAsText` によるモジュールテキスト化 |
| フォーム/レポート/マクロ出力 | 同上 |
| テーブル定義出力 | フィールド名・型・サイズ・必須フラグを CSV 出力 |
| クエリSQL一覧出力 | `all_queries_sql.csv` に全クエリのSQL文をまとめる |
| 一括pandas変換 | エクスポートしたSQLをそのまま pandas コードに変換 |
| 進捗リアルタイム表示 | Streamlit UI 上でログをリアルタイム表示 |
| 出力ファイル一覧表示 | 完了後に出力されたファイルを一覧表示 |

### 一括変換 CLI（`batch_convert.py`）

| 機能 | 内容 |
|---|---|
| CSV から一括変換 | `all_queries_sql.csv` を読み込んで全クエリを変換 |
| フォルダから一括変換 | `queries/` フォルダのテキストファイルを変換 |
| Python ファイル出力 | クエリ名ごとに `.py` ファイルを生成 |

---

## 非機能要件

| 項目 | 内容 |
|---|---|
| 対応OS | Windows 10/11（`pywin32` / COM 使用のため） |
| 対応 Access | `.accdb` / `.mdb`（Microsoft Access がインストールされていること） |
| 変換方針 | 完全変換ではなく「たたき台」生成。複雑な条件は警告コメントを付与 |
| エンコーディング | 出力CSV は `utf-8-sig`（Excel で直接開ける）、Python ファイルは `utf-8` |
| エラー耐性 | 変換できないオブジェクトはスキップし、処理を継続 |
| ポータビリティ | SQL変換機能（Tab 1）は Access なし・pywin32 なしでも動作 |

---

## 技術スタック

| カテゴリ | 技術 |
|---|---|
| 言語 | Python 3.13 |
| UI フレームワーク | Streamlit 1.50 |
| データ処理 | pandas 2.x / numpy 2.x |
| Windows COM 操作 | pywin32 |
| SQL パース | 正規表現（re モジュール）標準ライブラリのみ |
| ドキュメント | HTML / CSS / JavaScript（vanilla） |

---

## ディレクトリ・ファイル構成

```
day89-AccessToPython/
│
├── app.py                  # Streamlit メインアプリ（2タブ構成）
├── converter.py            # SQL → pandas 変換ロジック + サンプルクエリ
├── export_access.py        # Access オブジェクト一括エクスポート（CLI版）
├── batch_convert.py        # エクスポート済みクエリ → pandas 一括変換（CLI版）
│
├── requirements.txt        # 依存ライブラリ
├── README.md               # 本ファイル
│
└── docs/
    └── user_guide.html     # ユーザーガイド（HTML）
```

### エクスポート実行後の出力例

```
export_<DBファイル名>/
├── queries/                # クエリ定義テキスト（SaveAsText）
├── modules/                # VBAモジュールテキスト
├── forms/                  # フォーム定義テキスト
├── reports/                # レポート定義テキスト
├── macros/                 # マクロ定義テキスト
├── tables/                 # テーブルごとのフィールド定義CSV
├── all_tables_schema.csv   # 全テーブルまとめCSV
├── all_queries_sql.csv     # 全クエリのSQL文CSV
└── converted_python/       # pandas変換済みPythonファイル
    ├── Q_受注抽出.py
    └── Q_集計.py
```

---

## セットアップ

```bash
pip install -r requirements.txt
```

> **注意**: `pywin32` は Windows 専用です。
> SQL変換機能だけ使う場合は `streamlit pandas numpy` のみで動きます。

---

## 起動方法

```bash
# Streamlit アプリ
streamlit run app.py

# Access エクスポート（CLI）
python export_access.py C:\work\sample.accdb
python export_access.py C:\work\sample.accdb --out C:\export --type query module

# クエリ一括変換（CLI）
python batch_convert.py export_sample/all_queries_sql.csv
python batch_convert.py export_sample/queries/
```

---

## 変換対応表

| Access SQL | 変換後 pandas コード |
|---|---|
| `FROM Orders` | `orders = pd.read_csv("Orders.csv")` |
| `LEFT JOIN Products ON ...` | `.merge(products, left_on=..., right_on=..., how="left")` |
| `WHERE Status = "未処理"` | `df[df["Status"] == "未処理"]` |
| `WHERE 列 <> "値"` | `df[df["列"] != "値"]` |
| `WHERE OrderDate >= #2024/01/01#` | `df[df["OrderDate"] >= "2024/01/01"]` |
| `IsNull(列)` | `df["列"].isna()` |
| `IIf(条件, 真, 偽)` | `np.where(条件, 真, 偽)` |
| `Sum(Quantity) ... GROUP BY` | `.groupby([...]).agg(("TotalQty", "sum"))` |
| `ORDER BY 列 DESC` | `.sort_values("列", ascending=False)` |
| `Like "*キーワード*"` | `.str.contains("キーワード")` |

---

## 未対応・注意事項

- `UPDATE` / `DELETE` / `INSERT INTO` クエリは変換対象外
- `TRANSFORM`（クロス集計）は未対応
- Access 独自関数（`Nz` / `Format` / `DateDiff` / `Mid` など）は未変換
- IIf の条件式内の変数は `df["列"]` への変換が不完全な場合があります（警告付き）
- フォームのイベント処理や VBA の UI 操作は変換対象外

---

## 100日チャレンジ

**Day 89** - 2026/03/09
