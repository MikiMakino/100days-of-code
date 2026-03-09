"""
Day 89: Access SQL → pandas 変換アシスタント

AccessのSQLクエリを貼ると、pandasコードのたたき台を返します。
"""

import re


# -----------------------------------------------------------------------
# サンプルクエリ集
# -----------------------------------------------------------------------
SAMPLE_QUERIES = {
    "抽出クエリ（WHERE + ORDER BY）": """SELECT
    OrderID,
    ProductCode,
    Quantity,
    OrderDate
FROM Orders
WHERE Status = "未処理"
ORDER BY OrderDate;""",

    "結合クエリ（LEFT JOIN）": """SELECT
    o.OrderID,
    o.ProductCode,
    p.ProductName,
    o.Quantity,
    p.UnitPrice,
    o.Quantity * p.UnitPrice AS Amount
FROM Orders AS o
LEFT JOIN Products AS p
    ON o.ProductCode = p.ProductCode
WHERE o.Status = "未処理"
ORDER BY o.OrderDate;""",

    "集計クエリ（GROUP BY）": """SELECT
    ProductCode,
    Sum(Quantity) AS TotalQty,
    Count(OrderID) AS OrderCount
FROM Orders
WHERE OrderDate >= #2024/01/01#
GROUP BY ProductCode
ORDER BY TotalQty DESC;""",

    "IIf / Is Null 使用例": """SELECT
    CustomerID,
    CustomerName,
    IIf(IsNull(Phone), "未登録", Phone) AS PhoneDisplay,
    IIf(Region = "広島", "中国地方", "その他") AS Area
FROM Customers
WHERE IsNull(DeletedAt)
ORDER BY CustomerID;""",

    "INNER JOIN": """SELECT
    e.EmployeeID,
    e.Name,
    d.DeptName
FROM Employees AS e
INNER JOIN Departments AS d
    ON e.DeptID = d.DeptID
WHERE d.DeptName <> "退職"
ORDER BY e.Name;""",
}


# -----------------------------------------------------------------------
# 変換ロジック
# -----------------------------------------------------------------------

def clean_sql(sql: str) -> str:
    """改行・余分な空白を整理"""
    lines = [ln.strip() for ln in sql.strip().splitlines()]
    return " ".join(ln for ln in lines if ln)


def extract_aliases(sql: str) -> dict:
    """テーブルのエイリアス → 実名 のマップを作る"""
    pattern = re.findall(r'\b(\w+)\s+AS\s+(\w+)\b', sql, re.IGNORECASE)
    return {alias.lower(): real.lower() for real, alias in pattern}


def parse_from(sql: str) -> str | None:
    m = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
    return m.group(1) if m else None


def parse_joins(sql: str) -> list[dict]:
    pattern = re.finditer(
        r'\b(LEFT JOIN|INNER JOIN|RIGHT JOIN|JOIN)\s+(\w+)(?:\s+AS\s+(\w+))?\s+ON\s+([\w\.]+)\s*=\s*([\w\.]+)',
        sql, re.IGNORECASE
    )
    joins = []
    for m in pattern:
        join_type = m.group(1).upper()
        table = m.group(2)
        alias = m.group(3) or table
        left_key = m.group(4).split(".")[-1]
        right_key = m.group(5).split(".")[-1]
        how = "left" if "LEFT" in join_type else ("right" if "RIGHT" in join_type else "inner")
        joins.append({
            "table": table,
            "alias": alias,
            "left_key": left_key,
            "right_key": right_key,
            "how": how,
        })
    return joins


def split_select_columns(cols_raw: str) -> list[str]:
    """括弧の深さを考慮してSELECT列をカンマ分割する"""
    cols, depth, current = [], 0, []
    for ch in cols_raw:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            cols.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        cols.append("".join(current).strip())
    return cols


def parse_select_columns(sql: str) -> list[str]:
    m = re.search(r'\bSELECT\s+(.+?)\s+\bFROM\b', sql, re.IGNORECASE)
    if not m:
        return []
    cols_raw = m.group(1)
    cols = split_select_columns(cols_raw)
    result = []
    for col in cols:
        # エイリアス除去: "expr AS name" → name
        as_m = re.search(r'\bAS\s+(\w+)\s*$', col, re.IGNORECASE)
        if as_m:
            result.append(as_m.group(1))
        elif re.search(r'[\*\+\-/]', col):
            # 計算列はそのまま残す（後でコメント付き）
            result.append(col)
        else:
            # テーブル.列 → 列名だけ
            result.append(col.split(".")[-1].strip())
    return result


def parse_where(sql: str) -> str | None:
    m = re.search(r'\bWHERE\s+(.+?)(?:\bGROUP BY\b|\bORDER BY\b|\bHAVING\b|;|$)', sql, re.IGNORECASE)
    return m.group(1).strip() if m else None


def parse_groupby(sql: str) -> list[str] | None:
    m = re.search(r'\bGROUP BY\s+(.+?)(?:\bHAVING\b|\bORDER BY\b|;|$)', sql, re.IGNORECASE)
    if not m:
        return None
    return [c.strip().split(".")[-1] for c in m.group(1).split(",")]


def parse_orderby(sql: str) -> tuple[list[str], list[bool]] | tuple[None, None]:
    m = re.search(r'\bORDER BY\s+(.+?)(?:;|$)', sql, re.IGNORECASE)
    if not m:
        return None, None
    cols, asc_flags = [], []
    for item in m.group(1).split(","):
        item = item.strip()
        if item.upper().endswith(" DESC"):
            cols.append(item[:-5].strip().split(".")[-1])
            asc_flags.append(False)
        else:
            col = re.sub(r'\s+ASC$', '', item, flags=re.IGNORECASE).strip().split(".")[-1]
            cols.append(col)
            asc_flags.append(True)
    return cols, asc_flags


def convert_where_to_pandas(where: str) -> tuple[list[str], list[str]]:
    """
    WHERE句をpandas条件式に変換。
    完全変換は難しいのでコメントも一緒に返す。
    """
    notes = []
    expr = where

    # Access の日付リテラル #yyyy/mm/dd# → "yyyy-mm-dd"
    expr = re.sub(r'#([\d/]+)#', lambda m: f'"{m.group(1)}"', expr)

    # IsNull(x) → df["x"].isna()
    def isnull_repl(m):
        col = m.group(1).split(".")[-1]
        return f'df["{col}"].isna()'
    expr = re.sub(r'\bIsNull\s*\(\s*([\w\.]+)\s*\)', isnull_repl, expr, flags=re.IGNORECASE)

    # Not IsNull → notna()
    expr = re.sub(r'\bNot\s+df\["(\w+)"\]\.isna\(\)', r'df["\1"].notna()', expr)

    # <> を先に処理（= より前）: テーブル.列 <> 値 → df["列"] != 値
    def ne_repl(m):
        col = m.group(1).split(".")[-1]
        val = m.group(2)
        return f'df["{col}"] != {val}'
    expr = re.sub(r'([\w\.]+)\s*<>\s*("[\w\s]+"|\d+)', ne_repl, expr)

    # >= / <= の列名変換: テーブル.列 >= 値 → df["列"] >= 値
    def cmp_repl(m):
        col = m.group(1).split(".")[-1]
        op = m.group(2)
        val = m.group(3)
        return f'df["{col}"] {op} {val}'
    expr = re.sub(r'([\w\.]+)\s*(>=|<=|>|<)\s*("[\w\s/]+"|\d+)', cmp_repl, expr)

    # "列名 = 値" → df["列名"] == 値 (単純な等号のみ)
    def eq_repl(m):
        col = m.group(1).split(".")[-1]
        val = m.group(2)
        return f'df["{col}"] == {val}'
    expr = re.sub(r'([\w\.]+)\s*=\s*("[\w\s]+"|\d+)', eq_repl, expr)

    # >= / <= はそのまま通る (pandas OK)
    # Like → str.contains (近似)
    like_m = re.search(r'([\w\.]+)\s+Like\s+"([^"]+)"', expr, re.IGNORECASE)
    if like_m:
        col = like_m.group(1).split(".")[-1]
        pattern = like_m.group(2).replace("*", "")
        expr = re.sub(
            r'([\w\.]+)\s+Like\s+"[^"]+"',
            f'df["{col}"].str.contains("{pattern}")',
            expr, flags=re.IGNORECASE
        )
        notes.append('Like句は str.contains() に変換しました（ワイルドカードは除去）')

    # AND / OR
    expr = re.sub(r'\bAND\b', '&', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bOR\b', '|', expr, flags=re.IGNORECASE)

    return expr, notes


def split_args(args_str: str) -> list[str]:
    """括弧の深さを考慮してカンマ分割する"""
    args, depth, current = [], 0, []
    for ch in args_str:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append("".join(current).strip())
    return args


def convert_iif(expr: str) -> str:
    """IIf(条件, 真, 偽) → np.where(条件, 真, 偽)（括弧ネスト対応）"""
    result = []
    i = 0
    while i < len(expr):
        m = re.match(r'IIf\s*\(', expr[i:], re.IGNORECASE)
        if m:
            prefix_end = i + m.end()
            depth, j = 1, prefix_end
            while j < len(expr) and depth > 0:
                if expr[j] == "(":
                    depth += 1
                elif expr[j] == ")":
                    depth -= 1
                j += 1
            inner = expr[prefix_end:j-1]
            args = split_args(inner)
            if len(args) == 3:
                cond, true_val, false_val = args
                result.append(f"np.where({cond}, {true_val}, {false_val})")
            else:
                result.append(expr[i:j])  # 変換失敗時はそのまま
            i = j
        else:
            result.append(expr[i])
            i += 1
    return "".join(result)


def parse_select_expressions(sql: str) -> list[dict]:
    """SELECT列を {alias, expr, is_calc} のリストで返す"""
    m = re.search(r'\bSELECT\s+(.+?)\s+\bFROM\b', sql, re.IGNORECASE)
    if not m:
        return []
    cols_raw = m.group(1)
    result = []
    for col in split_select_columns(cols_raw):
        col = col.strip()
        as_m = re.search(r'^(.+?)\s+AS\s+(\w+)$', col, re.IGNORECASE)
        if as_m:
            expr = as_m.group(1).strip()
            alias = as_m.group(2)
        else:
            expr = col
            alias = col.split(".")[-1].strip()
        is_calc = bool(re.search(r'[\*\+\-/]|IIf|Sum|Count|Avg|Max|Min', expr, re.IGNORECASE))
        result.append({"alias": alias, "expr": expr, "is_calc": is_calc})
    return result


def has_aggregates(select_exprs: list[dict]) -> bool:
    agg_funcs = re.compile(r'\b(Sum|Count|Avg|Max|Min)\s*\(', re.IGNORECASE)
    return any(agg_funcs.search(c["expr"]) for c in select_exprs)


def convert_agg_expr(expr: str, col: str) -> str:
    """Sum(x) → ("x", "sum") 形式の文字列を返す"""
    m = re.match(r'\b(Sum|Count|Avg|Max|Min)\s*\(\s*([\w\.]+)\s*\)', expr, re.IGNORECASE)
    if m:
        func = m.group(1).lower()
        if func == "sum":
            return f'("{col}", "sum")'
        elif func == "count":
            return f'("{col}", "count")'
        elif func == "avg":
            return f'("{col}", "mean")'
        elif func == "max":
            return f'("{col}", "max")'
        elif func == "min":
            return f'("{col}", "min")'
    return f'("{col}", "first")'


# -----------------------------------------------------------------------
# メイン変換関数
# -----------------------------------------------------------------------

def convert(sql: str) -> tuple[str, list[str]]:
    """
    AccessのSQL文字列 → pandasコード文字列
    戻り値: (コード文字列, 注意事項リスト)
    """
    warnings = []
    clean = clean_sql(sql)

    main_table = parse_from(clean)
    if not main_table:
        return "# FROM句が見つかりませんでした。", []

    joins = parse_joins(clean)
    select_exprs = parse_select_expressions(clean)
    where_str = parse_where(clean)
    groupby_cols = parse_groupby(clean)
    order_cols, order_asc = parse_orderby(clean)
    is_agg = has_aggregates(select_exprs)

    use_numpy = any("IIf" in c["expr"] for c in select_exprs)

    lines = []
    lines.append("import pandas as pd")
    if use_numpy:
        lines.append("import numpy as np")
    lines.append("")

    # テーブル読み込み
    lines.append(f'{main_table.lower()} = pd.read_csv("{main_table}.csv")')
    for j in joins:
        lines.append(f'{j["table"].lower()} = pd.read_csv("{j["table"]}.csv")')
    lines.append("")

    # JOIN
    if joins:
        prev = main_table.lower()
        for i, j in enumerate(joins):
            var = "df" if i == 0 else f"df_{i+1}"
            lines.append(
                f'{var} = {prev}.merge({j["table"].lower()}, '
                f'left_on="{j["left_key"]}", right_on="{j["right_key"]}", '
                f'how="{j["how"]}")'
            )
            prev = var
        if len(joins) > 1:
            lines[-1] = lines[-1].replace(f"df_{len(joins)}", "df")
    else:
        lines.append(f"df = {main_table.lower()}.copy()")

    # WHERE
    if where_str:
        pandas_where, where_notes = convert_where_to_pandas(where_str)
        warnings.extend(where_notes)
        lines.append("")
        lines.append("# --- WHERE ---")
        lines.append(f"# Access: {where_str}")
        lines.append(f"df = df[{pandas_where}].copy()")

    # 計算列（非集計）
    calc_cols = [c for c in select_exprs if c["is_calc"] and not has_aggregates([c])]
    if calc_cols and not is_agg:
        lines.append("")
        lines.append("# --- 計算列 ---")
        for c in calc_cols:
            expr = c["expr"]
            # IsNull(x) → df["x"].isna()
            def isnull_in_expr(m):
                col = m.group(1).split(".")[-1]
                return f'df["{col}"].isna()'
            expr = re.sub(r'\bIsNull\s*\(\s*([\w\.]+)\s*\)', isnull_in_expr, expr, flags=re.IGNORECASE)
            # IIf を先に変換（括弧ネスト対応）
            if re.search(r'\bIIf\b', expr, re.IGNORECASE):
                expr = convert_iif(expr)
                warnings.append('IIf → np.where に変換しました（条件式は手修正してください）')
            # テーブル.列 → df["列"]（IIf変換後に適用、np.は除外）
            expr = re.sub(r'\b(?!np\b)(?!pd\b)(\w+)\.([\w]+)\b', r'df["\2"]', expr)
            lines.append(f'df["{c["alias"]}"] = {expr}')

    # GROUP BY + 集計
    if is_agg and groupby_cols:
        agg_cols = [c for c in select_exprs if has_aggregates([c])]
        agg_dict_parts = []
        for c in agg_cols:
            agg_dict_parts.append(convert_agg_expr(c["expr"], c["alias"]))
        lines.append("")
        lines.append("# --- GROUP BY + 集計 ---")
        lines.append(f"df = df.groupby({groupby_cols}).agg(")
        for part in agg_dict_parts:
            lines.append(f"    {part},")
        lines.append(").reset_index()")

    # ORDER BY
    if order_cols:
        asc_list = str(order_asc) if len(order_asc) > 1 else str(order_asc[0])
        col_list = str(order_cols) if len(order_cols) > 1 else f'"{order_cols[0]}"'
        lines.append("")
        lines.append("# --- ORDER BY ---")
        lines.append(f"df = df.sort_values({col_list}, ascending={asc_list})")

    # SELECT列の絞り込み
    # GROUP BY後は alias（集計列名）を全列含める
    all_aliases = [c["alias"].split(".")[-1] for c in select_exprs]
    # * は絞り込みしない
    if all_aliases and all_aliases != ["*"]:
        lines.append("")
        lines.append("# --- SELECT列を絞る ---")
        lines.append(f"# ※ 列名が実際のDataFrameと異なる場合は調整してください")
        lines.append(f"result = df[{all_aliases}]")
    else:
        lines.append("")
        lines.append("result = df")

    lines.append("")
    lines.append("print(result.head(20))")

    return "\n".join(lines), warnings


# -----------------------------------------------------------------------
# CLI で動かす場合
# -----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Access SQL → pandas 変換アシスタント (CLI版)")
    print("=" * 60)
    print()
    print("サンプルクエリの変換結果を表示します。")
    print()

    for name, sql in SAMPLE_QUERIES.items():
        print(f"【{name}】")
        print("-" * 40)
        print("■ Access SQL:")
        print(sql)
        print()
        code, warns = convert(sql)
        print("■ pandas コード:")
        print(code)
        if warns:
            print()
            print("■ 注意:")
            for w in warns:
                print(f"  ⚠ {w}")
        print()
        print("=" * 60)
        print()
