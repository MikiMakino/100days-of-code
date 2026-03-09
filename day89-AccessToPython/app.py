"""
Day 89: Access SQL → pandas 変換アシスタント (Streamlit版)
"""

import base64
import sys
import threading
from pathlib import Path

import streamlit as st

from converter import SAMPLE_QUERIES, convert

st.set_page_config(
    page_title="Access → pandas 変換アシスタント",
    page_icon="🔄",
    layout="wide",
)

# ── ガイドを開くボタン ──
_guide_path = Path(__file__).parent / "docs" / "user_guide.html"

col_title, col_guide = st.columns([6, 1])
with col_title:
    st.title("🔄 Access → pandas 変換アシスタント")
with col_guide:
    st.write("")  # タイトルと高さを合わせる
    if _guide_path.exists():
        _html_b64 = base64.b64encode(_guide_path.read_bytes()).decode()
        st.markdown(
            f'<a href="data:text/html;base64,{_html_b64}" target="_blank">'
            f'<button style="width:100%;padding:8px 12px;background:#2563eb;color:white;'
            f'border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">'
            f'📖 ガイドを開く</button></a>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("docs/user_guide.html が見つかりません")

tab1, tab2 = st.tabs(["📝 SQL変換", "📦 Accessエクスポート"])


# ===================================================================
# TAB 1: SQL変換
# ===================================================================
with tab1:
    st.caption("AccessのSQLクエリを貼り付けると、pandasコードのたたき台を生成します。")

    # サイドバー
    with st.sidebar:
        st.header("サンプルクエリ")
        sample_names = list(SAMPLE_QUERIES.keys())
        selected = st.radio("サンプルを選んで試す", ["（なし）"] + sample_names)

        st.markdown("---")
        st.markdown("""
**対応している構文**
- SELECT / FROM
- LEFT JOIN / INNER JOIN
- WHERE（基本的な条件）
- GROUP BY + 集計関数
- ORDER BY（ASC / DESC）
- 計算列（AS）
- IsNull → isna()
- IIf → np.where
- Like → str.contains

**注意事項**
- 完全変換ではなくたたき台生成です
- WHERE条件は手修正が必要な場合があります
""")

    default_sql = SAMPLE_QUERIES[selected] if selected != "（なし）" else ""

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Access SQL を入力")
        sql_input = st.text_area(
            "AccessのSQLクエリを貼り付けてください",
            value=default_sql,
            height=350,
            placeholder="SELECT ...\nFROM ...\nWHERE ...",
        )
        convert_btn = st.button("▶ pandas コードに変換", type="primary", use_container_width=True)

    with col2:
        st.subheader("生成された pandas コード")

        if convert_btn or selected != "（なし）":
            if sql_input.strip():
                code, warnings = convert(sql_input)
                st.code(code, language="python")

                if warnings:
                    st.markdown("---")
                    st.warning("**変換時の注意事項**")
                    for w in warnings:
                        st.write(f"⚠️ {w}")

                st.download_button(
                    label="📥 コードをダウンロード (.py)",
                    data=code,
                    file_name="converted_pandas.py",
                    mime="text/plain",
                    use_container_width=True,
                )
            else:
                st.info("左側にAccessのSQLクエリを入力してください。")
        else:
            st.info("左側にSQLを入力して「変換」ボタンを押してください。")

    with st.expander("📖 変換対応表"):
        st.markdown("""
| Access SQL | pandas コード |
|---|---|
| `FROM Orders` | `orders = pd.read_csv("Orders.csv")` |
| `LEFT JOIN Products ON ...` | `.merge(products, ..., how="left")` |
| `WHERE Status = "未処理"` | `df[df["Status"] == "未処理"]` |
| `WHERE 列 <> "値"` | `df[df["列"] != "値"]` |
| `WHERE 列 >= #2024/01/01#` | `df[df["列"] >= "2024/01/01"]` |
| `IsNull(列)` | `df["列"].isna()` |
| `IIf(条件, 真, 偽)` | `np.where(条件, 真, 偽)` |
| `Sum(列) ... GROUP BY` | `.groupby().agg(("列", "sum"))` |
| `ORDER BY 列 DESC` | `.sort_values(ascending=False)` |
""")


# ===================================================================
# TAB 2: Accessエクスポート
# ===================================================================
with tab2:
    st.caption("Accessファイルからクエリ・VBAモジュール・テーブル定義などをテキストで書き出します。")

    # pywin32 チェック
    try:
        import win32com.client
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False

    if not HAS_WIN32:
        st.error("pywin32 が必要です: `pip install pywin32`")
        st.stop()

    # --- 入力フォーム ---
    col_a, col_b = st.columns([2, 1])

    with col_a:
        accdb_path = st.text_input(
            "Accessファイルのパス (.accdb / .mdb)",
            placeholder=r"C:\work\sample.accdb",
        )

    with col_b:
        out_path = st.text_input(
            "出力先フォルダ（省略可）",
            placeholder="省略時: ファイルと同じフォルダ",
        )

    st.markdown("**エクスポートするオブジェクト**")
    obj_cols = st.columns(6)
    obj_types = {
        "query":  obj_cols[0].checkbox("クエリ", value=True),
        "module": obj_cols[1].checkbox("VBAモジュール", value=True),
        "form":   obj_cols[2].checkbox("フォーム", value=False),
        "report": obj_cols[3].checkbox("レポート", value=False),
        "macro":  obj_cols[4].checkbox("マクロ", value=False),
        "table":  obj_cols[5].checkbox("テーブル定義", value=True),
    }

    also_convert = st.checkbox("エクスポート後にクエリSQLも pandas コードに変換する", value=True)

    export_btn = st.button("📦 エクスポート実行", type="primary", use_container_width=True)

    # --- 実行 ---
    if export_btn:
        if not accdb_path.strip():
            st.error("Accessファイルのパスを入力してください。")
        else:
            db = Path(accdb_path.strip())
            if not db.exists():
                st.error(f"ファイルが見つかりません: {db}")
            else:
                out_dir = Path(out_path.strip()) if out_path.strip() else db.parent / f"export_{db.stem}"
                out_dir.mkdir(parents=True, exist_ok=True)

                selected_types = [k for k, v in obj_types.items() if v]
                if not selected_types:
                    st.warning("エクスポートするオブジェクトを1つ以上選んでください。")
                else:
                    st.info(f"エクスポート開始: {db.name} → {out_dir}")
                    log = st.empty()
                    logs = []

                    def add_log(msg: str):
                        logs.append(msg)
                        log.markdown("\n".join(logs))

                    # --- Access COM操作 ---
                    AC_OBJECT_TYPES = {
                        "query":  (1, "queries",  "AllQueries",  "CurrentData"),
                        "form":   (2, "forms",    "AllForms",    "CurrentData"),
                        "report": (3, "reports",  "AllReports",  "CurrentData"),
                        "macro":  (4, "macros",   "AllMacros",   "CurrentData"),
                        "module": (5, "modules",  "AllModules",  "CurrentProject"),
                    }

                    import re
                    import csv

                    def safe_name(name):
                        return re.sub(r'[\\/:*?"<>|]', "_", name)

                    try:
                        app = win32com.client.Dispatch("Access.Application")
                        app.Visible = False
                        app.OpenCurrentDatabase(str(db))
                        add_log(f"✅ オープン完了: `{db.name}`\n")

                        for type_key in [k for k in AC_OBJECT_TYPES if k in selected_types]:
                            ac_type, subdir, coll_attr, proj_attr = AC_OBJECT_TYPES[type_key]
                            type_dir = out_dir / subdir
                            type_dir.mkdir(parents=True, exist_ok=True)

                            try:
                                src = getattr(app, proj_attr)
                                collection = getattr(src, coll_attr)
                                names = [obj.Name for obj in collection]
                            except Exception as e:
                                add_log(f"⚠️ [{type_key}] 一覧取得失敗: {e}")
                                continue

                            add_log(f"**[{type_key}]** {len(names)}件")
                            ok = ng = 0
                            for name in names:
                                out_file = type_dir / f"{safe_name(name)}.txt"
                                try:
                                    app.SaveAsText(ac_type, name, str(out_file))
                                    add_log(f"  ✓ {name}")
                                    ok += 1
                                except Exception as e:
                                    add_log(f"  ✗ {name} → {e}")
                                    ng += 1
                            add_log(f"  → {ok}件完了" + (f", {ng}件失敗" if ng else "") + "\n")

                        # テーブル定義
                        if "table" in selected_types:
                            add_log("**[table - スキーマ定義]**")
                            try:
                                db_obj = app.CurrentDb()
                                tables = db_obj.TableDefs
                                summary_rows = []
                                schema_dir = out_dir / "tables"
                                schema_dir.mkdir(exist_ok=True)

                                for i in range(tables.Count):
                                    try:
                                        tdef = tables.Item(i)
                                        tname = tdef.Name
                                        if tname.startswith("MSys") or tname.startswith("~"):
                                            continue
                                        rows = []
                                        for j in range(tdef.Fields.Count):
                                            f = tdef.Fields.Item(j)
                                            rows.append({
                                                "table": tname, "field": f.Name,
                                                "type": f.Type, "size": f.Size,
                                                "required": bool(f.Required),
                                            })
                                            summary_rows.append(rows[-1])
                                        out_file = schema_dir / f"{safe_name(tname)}.csv"
                                        with open(out_file, "w", newline="", encoding="utf-8-sig") as fp:
                                            w = csv.DictWriter(fp, fieldnames=["table","field","type","size","required"])
                                            w.writeheader(); w.writerows(rows)
                                        add_log(f"  ✓ {tname} ({len(rows)}フィールド)")
                                    except Exception:
                                        continue

                                summary_file = out_dir / "all_tables_schema.csv"
                                with open(summary_file, "w", newline="", encoding="utf-8-sig") as fp:
                                    w = csv.DictWriter(fp, fieldnames=["table","field","type","size","required"])
                                    w.writeheader(); w.writerows(summary_rows)
                                add_log(f"  → まとめCSV: `all_tables_schema.csv`\n")
                            except Exception as e:
                                add_log(f"  ⚠️ テーブル定義取得失敗: {e}\n")

                        # クエリSQL CSV
                        if "query" in selected_types:
                            add_log("**[クエリSQL一覧CSV]**")
                            try:
                                db_obj = app.CurrentDb()
                                qdefs = db_obj.QueryDefs
                                sql_rows = []
                                for i in range(qdefs.Count):
                                    try:
                                        q = qdefs.Item(i)
                                        if not q.Name.startswith("~"):
                                            sql_rows.append({"name": q.Name, "sql": q.SQL.strip()})
                                    except Exception:
                                        continue
                                sql_csv = out_dir / "all_queries_sql.csv"
                                with open(sql_csv, "w", newline="", encoding="utf-8-sig") as fp:
                                    w = csv.DictWriter(fp, fieldnames=["name","sql"])
                                    w.writeheader(); w.writerows(sql_rows)
                                add_log(f"  → `all_queries_sql.csv` ({len(sql_rows)}件)\n")
                            except Exception as e:
                                add_log(f"  ⚠️ クエリSQL取得失敗: {e}\n")

                        # pandas コード変換
                        if also_convert and "query" in selected_types:
                            sql_csv = out_dir / "all_queries_sql.csv"
                            if sql_csv.exists():
                                add_log("**[pandas コード変換]**")
                                conv_dir = out_dir / "converted_python"
                                conv_dir.mkdir(exist_ok=True)
                                with open(sql_csv, encoding="utf-8-sig") as fp:
                                    reader = csv.DictReader(fp)
                                    conv_rows = list(reader)
                                for row in conv_rows:
                                    if not row["sql"].strip():
                                        continue
                                    code, warns = convert(row["sql"])
                                    out_py = conv_dir / f"{safe_name(row['name'])}.py"
                                    out_py.write_text(
                                        f"# 元クエリ名: {row['name']}\n"
                                        f"# ※ 自動生成のたたき台です。手修正してください。\n\n"
                                        + code, encoding="utf-8"
                                    )
                                    add_log(f"  ✓ {row['name']}.py")
                                add_log(f"  → `converted_python/` に {len(conv_rows)}件\n")

                    except Exception as e:
                        add_log(f"\n❌ エラー: {e}")
                    finally:
                        try:
                            app.CloseCurrentDatabase()
                        except Exception:
                            pass
                        try:
                            app.Quit()
                        except Exception:
                            pass

                    add_log(f"\n---\n✅ **完了** → 出力先: `{out_dir}`")

                    # 出力ファイル一覧
                    st.markdown("---")
                    st.markdown("**出力ファイル一覧**")
                    all_files = sorted(out_dir.rglob("*"))
                    file_list = [f"- `{f.relative_to(out_dir)}`" for f in all_files if f.is_file()]
                    st.markdown("\n".join(file_list[:50]))
                    if len(file_list) > 50:
                        st.caption(f"… 他 {len(file_list)-50}件")
