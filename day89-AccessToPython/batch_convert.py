"""
Day 89: エクスポート済みクエリ → pandas コード 一括変換

export_access.py で出力したクエリテキストまたはCSVを読み込み、
pandas コードのたたき台を一括生成します。

使い方:
  # CSVから変換（export_access.py の all_queries_sql.csv）
  python batch_convert.py export_sample/all_queries_sql.csv

  # クエリテキストフォルダから変換
  python batch_convert.py export_sample/queries/
"""

import csv
import sys
from pathlib import Path

from converter import convert


def convert_from_csv(csv_path: Path, out_dir: Path) -> None:
    """all_queries_sql.csv からまとめて変換"""
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"クエリ数: {len(rows)}件\n")

    for row in rows:
        name = row["name"]
        sql = row["sql"]
        if not sql.strip():
            print(f"  スキップ（SQLなし）: {name}")
            continue

        code, warns = convert(sql)
        out_file = out_dir / f"{name}.py"
        out_file.write_text(
            f"# 元クエリ名: {name}\n"
            f"# ※ このコードは自動生成されたたたき台です。手修正してください。\n\n"
            + code,
            encoding="utf-8"
        )
        print(f"  ✓ {name} → {out_file.name}")
        for w in warns:
            print(f"    ⚠ {w}")


def convert_from_dir(queries_dir: Path, out_dir: Path) -> None:
    """queries/ フォルダのテキストファイルからまとめて変換"""
    txt_files = list(queries_dir.glob("*.txt"))
    print(f"クエリファイル数: {len(txt_files)}件\n")

    for txt_file in sorted(txt_files):
        raw = txt_file.read_text(encoding="utf-8", errors="replace")

        # SaveAsText のクエリファイルは "Begin" ヘッダーの後に SQL がある
        # 簡易抽出: SQL = ... の行を拾う
        sql = extract_sql_from_saved_text(raw)
        if not sql:
            print(f"  スキップ（SQL抽出失敗）: {txt_file.name}")
            continue

        code, warns = convert(sql)
        out_file = out_dir / f"{txt_file.stem}.py"
        out_file.write_text(
            f"# 元クエリ名: {txt_file.stem}\n"
            f"# ※ このコードは自動生成されたたたき台です。手修正してください。\n\n"
            + code,
            encoding="utf-8"
        )
        print(f"  ✓ {txt_file.stem} → {out_file.name}")
        for w in warns:
            print(f"    ⚠ {w}")


def extract_sql_from_saved_text(text: str) -> str:
    """
    Access の SaveAsText クエリファイルから SQL 部分を抽出する。
    SaveAsText のクエリ定義には "SQL = ..." の行が含まれる。
    """
    import re

    # "SQL =" の後から次の改行を含むブロックを取る
    m = re.search(r'\bSQL\s*=\s*(.+?)(?=\r?\n[A-Za-z]|\Z)', text, re.DOTALL | re.IGNORECASE)
    if m:
        sql = m.group(1).strip()
        # Access のエスケープ: 改行は \r\n が入ることがある
        sql = sql.replace("\r\n", " ").replace("\r", " ")
        return sql
    return ""


def main():
    if len(sys.argv) < 2:
        print("使い方:")
        print("  python batch_convert.py <CSVファイルまたはqueries/フォルダ>")
        print()
        print("例:")
        print("  python batch_convert.py export_sample/all_queries_sql.csv")
        print("  python batch_convert.py export_sample/queries/")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"見つかりません: {input_path}")
        sys.exit(1)

    out_dir = input_path.parent / "converted_python"
    if input_path.is_file():
        out_dir = input_path.parent / "converted_python"
    else:
        out_dir = input_path.parent / "converted_python"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"入力: {input_path}")
    print(f"出力先: {out_dir}\n")

    if input_path.is_file() and input_path.suffix.lower() == ".csv":
        convert_from_csv(input_path, out_dir)
    elif input_path.is_dir():
        convert_from_dir(input_path, out_dir)
    else:
        print("CSVファイルまたはqueries/フォルダを指定してください")
        sys.exit(1)

    print(f"\n完了。出力先: {out_dir}")


if __name__ == "__main__":
    main()
