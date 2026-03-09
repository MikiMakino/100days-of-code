"""
Day 89: Access オブジェクト一括エクスポーター

Accessファイル(.accdb/.mdb)から
クエリ・VBAモジュール・フォーム・レポート・マクロを
テキストファイルとして吐き出します。

使い方:
  python export_access.py sample.accdb
  python export_access.py sample.accdb --out ./export_output
  python export_access.py sample.accdb --type query module
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import win32com.client
except ImportError:
    print("pywin32 が必要です: pip install pywin32")
    sys.exit(1)


# Access AcObjectType 定数
AC_OBJECT_TYPES = {
    "query":   (1,  "queries",  "AllQueries"),
    "form":    (2,  "forms",    "AllForms"),
    "report":  (3,  "reports",  "AllReports"),
    "macro":   (4,  "macros",   "AllMacros"),
    "module":  (5,  "modules",  "AllModules"),
}


def safe_name(name: str) -> str:
    """ファイル名に使えない文字を置換"""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def get_object_names(app, type_key: str) -> list[str]:
    """指定タイプのオブジェクト名一覧を取得"""
    _, _, collection_attr = AC_OBJECT_TYPES[type_key]
    try:
        if type_key in ("query", "form", "report", "macro"):
            collection = getattr(app.CurrentData, collection_attr)
        else:
            collection = getattr(app.CurrentProject, collection_attr)
        return [obj.Name for obj in collection]
    except Exception as e:
        print(f"  [{type_key}] 一覧取得失敗: {e}")
        return []


def export_objects(app, type_key: str, out_dir: Path) -> tuple[int, int]:
    """1タイプ分のオブジェクトをすべてエクスポート"""
    ac_type, subdir, _ = AC_OBJECT_TYPES[type_key]
    target_dir = out_dir / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    names = get_object_names(app, type_key)
    if not names:
        return 0, 0

    ok, ng = 0, 0
    for name in names:
        out_file = target_dir / f"{safe_name(name)}.txt"
        try:
            app.SaveAsText(ac_type, name, str(out_file))
            print(f"  ✓ {name}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {name} → {e}")
            ng += 1

    return ok, ng


def export_table_schema(app, out_dir: Path) -> None:
    """テーブル定義をCSV形式でエクスポート（テーブル名・フィールド名・型）"""
    import csv

    schema_dir = out_dir / "tables"
    schema_dir.mkdir(parents=True, exist_ok=True)

    try:
        db = app.CurrentDb()
        tables = db.TableDefs
    except Exception as e:
        print(f"  [tables] 取得失敗: {e}")
        return

    summary_rows = []

    for i in range(tables.Count):
        try:
            tdef = tables.Item(i)
            tname = tdef.Name

            # システムテーブル・リンクテーブルはスキップ
            if tname.startswith("MSys") or tname.startswith("~"):
                continue

            rows = []
            for j in range(tdef.Fields.Count):
                f = tdef.Fields.Item(j)
                rows.append({
                    "table": tname,
                    "field": f.Name,
                    "type": f.Type,
                    "size": f.Size,
                    "required": bool(f.Required),
                })
                summary_rows.append(rows[-1])

            # テーブルごとのCSV
            out_file = schema_dir / f"{safe_name(tname)}.csv"
            with open(out_file, "w", newline="", encoding="utf-8-sig") as fp:
                writer = csv.DictWriter(fp, fieldnames=["table", "field", "type", "size", "required"])
                writer.writeheader()
                writer.writerows(rows)
            print(f"  ✓ {tname} ({len(rows)}フィールド)")

        except Exception as e:
            print(f"  ✗ テーブル取得エラー: {e}")
            continue

    # 全テーブルまとめCSV
    summary_file = out_dir / "all_tables_schema.csv"
    with open(summary_file, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=["table", "field", "type", "size", "required"])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\n  → 全テーブル定義まとめ: {summary_file}")


def export_query_sql(app, out_dir: Path) -> None:
    """クエリのSQL文だけを抽出してCSVにまとめる"""
    import csv

    try:
        db = app.CurrentDb()
        queries = db.QueryDefs
    except Exception as e:
        print(f"  [query SQL] 取得失敗: {e}")
        return

    rows = []
    for i in range(queries.Count):
        try:
            q = queries.Item(i)
            if q.Name.startswith("~"):
                continue
            rows.append({"name": q.Name, "sql": q.SQL.strip()})
        except Exception:
            continue

    out_file = out_dir / "all_queries_sql.csv"
    with open(out_file, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=["name", "sql"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  → クエリSQL一覧CSV: {out_file} ({len(rows)}件)")


def main():
    parser = argparse.ArgumentParser(
        description="AccessファイルからクエリやVBAをテキストにエクスポート"
    )
    parser.add_argument("accdb", help="Accessファイルのパス (.accdb / .mdb)")
    parser.add_argument(
        "--out", default=None,
        help="出力先フォルダ（省略時: accdbと同フォルダに export_ プレフィックス）"
    )
    parser.add_argument(
        "--type", nargs="+",
        choices=list(AC_OBJECT_TYPES.keys()) + ["table", "all"],
        default=["all"],
        help="エクスポートするオブジェクト種別 (デフォルト: all)"
    )
    args = parser.parse_args()

    db_path = Path(args.accdb).resolve()
    if not db_path.exists():
        print(f"ファイルが見つかりません: {db_path}")
        sys.exit(1)

    out_dir = Path(args.out) if args.out else db_path.parent / f"export_{db_path.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)

    target_types = set(args.type)
    if "all" in target_types:
        target_types = set(AC_OBJECT_TYPES.keys()) | {"table"}

    print(f"\nAccessファイル : {db_path}")
    print(f"出力先         : {out_dir}")
    print(f"対象           : {', '.join(sorted(target_types))}")
    print()

    app = win32com.client.Dispatch("Access.Application")
    app.Visible = False

    try:
        app.OpenCurrentDatabase(str(db_path))
        print(f"オープン完了: {db_path.name}\n")

        total_ok, total_ng = 0, 0

        for type_key in AC_OBJECT_TYPES:
            if type_key not in target_types:
                continue
            print(f"[{type_key}]")
            ok, ng = export_objects(app, type_key, out_dir)
            total_ok += ok
            total_ng += ng
            print(f"  → {ok}件 出力完了" + (f", {ng}件 失敗" if ng else ""))
            print()

        if "table" in target_types:
            print("[table - スキーマ定義]")
            export_table_schema(app, out_dir)
            print()

            print("[query - SQLのみCSV]")
            export_query_sql(app, out_dir)
            print()

    finally:
        try:
            app.CloseCurrentDatabase()
        except Exception:
            pass
        app.Quit()

    print("=" * 50)
    print(f"完了: 合計 {total_ok}件 成功" + (f", {total_ng}件 失敗" if total_ng else ""))
    print(f"出力先: {out_dir}")


if __name__ == "__main__":
    main()
