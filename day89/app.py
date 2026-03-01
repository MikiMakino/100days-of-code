"""
お弁当発注管理アプリ - Day 89
要件定義書（Power Apps/SharePoint仕様）を Python/Streamlit/SQLite で実装

起動: streamlit run app.py
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar as cal_module

import database as db
import utils

# ─── ページ設定 ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🍱 お弁当発注管理",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

# ─── CSS ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.cal-cell {
    text-align: center; border: 1px solid #ddd; border-radius: 6px;
    padding: 6px 2px; min-height: 64px; font-size: 13px;
}
.cal-ordered  { background: #d4edda; border-color: #28a745; }
.cal-holiday  { background: #f8d7da; color: #721c24; }
.cal-today    { border: 3px solid #007bff !important; }
.cal-weekend  { color: #dc3545; }
.cal-past     { opacity: 0.5; }
.stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)


# ─── 認証ヘルパー ──────────────────────────────────────────────────────────────────
def check_auth():
    if "user" not in st.session_state or st.session_state.user is None:
        _show_login()
        st.stop()


def _show_login():
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("<h1 style='text-align:center'>🍱 お弁当発注管理</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:grey'>社内・出向者向け弁当注文システム</p>", unsafe_allow_html=True)
        st.markdown("---")
        with st.form("login"):
            email = st.text_input("メールアドレス", placeholder="xxx@company.com")
            password = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True, type="primary"):
                user = db.authenticate(email, password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "order"
                    st.rerun()
                else:
                    st.error("メールアドレスまたはパスワードが違います")
        with st.expander("デモアカウント"):
            st.markdown("""
| メール | パスワード | 権限 |
|---|---|---|
| admin@company.com | admin123 | 管理者 |
| tanaka@company.com | pass123 | 一般（現金） |
| suzuki@company.com | pass123 | 一般（非現金） |
| sato@partner.com | pass123 | 出向者（現金） |
            """)


def require_admin():
    if not st.session_state.user.get("is_admin"):
        st.error("⛔ この機能は管理者専用です")
        st.stop()


# ─── サイドバー ────────────────────────────────────────────────────────────────────
def render_sidebar():
    user = st.session_state.user
    with st.sidebar:
        st.markdown("### 🍱 お弁当発注管理")
        st.markdown(f"**{user['name']}**")
        badge = "👑 管理者" if user["is_admin"] else "👤 一般"
        st.markdown(f"{badge}　|　{user['affiliation']}　|　{user['payment_type']}")
        st.markdown("---")

        nav_items = [
            ("🏠 注文画面",           "order",     False),
            ("📅 カレンダー",          "calendar",  False),
            ("🔄 代理注文",            "proxy",     False),
            ("📊 管理者ダッシュボード", "dashboard", True),
            ("👥 ユーザー管理",        "users",     True),
            ("💰 費用集計",            "cost",      True),
        ]
        for label, page_id, admin_only in nav_items:
            if admin_only and not user["is_admin"]:
                continue
            active = st.session_state.get("page") == page_id
            btn_type = "primary" if active else "secondary"
            if st.button(label, key=f"nav_{page_id}", type=btn_type, use_container_width=True):
                st.session_state.page = page_id
                st.rerun()

        st.markdown("---")
        if st.button("🚪 ログアウト", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "order"
            st.rerun()


# ─── ページ：注文画面 ─────────────────────────────────────────────────────────────
def page_order():
    user = st.session_state.user
    st.title("🏠 注文画面")

    # 締め切りバナー
    past_deadline, status_msg = utils.deadline_status()
    if past_deadline:
        st.warning(status_msg)
    else:
        st.info(status_msg)

    today = date.today()
    unit_price = db.get_unit_price()

    left, right = st.columns([1, 1], gap="large")

    # ── 左：注文登録 ────────────────────────────────────────────
    with left:
        st.subheader("📝 新規注文")

        order_date = st.date_input("日付を選択", min_value=today, value=today, key="single_date")

        if st.button("注文する", type="primary"):
            ok, msg = utils.can_order(order_date)
            if not ok:
                st.error(msg)
            else:
                ok2, msg2 = db.place_order(user["user_id"], str(order_date), user["user_id"])
                st.success(msg2) if ok2 else st.error(msg2)
                if ok2:
                    st.rerun()

        st.markdown("---")
        st.subheader("📆 一括注文（長期予約）")
        ca, cb = st.columns(2)
        with ca:
            bulk_start = st.date_input("開始日", min_value=today, value=today, key="bs")
        with cb:
            bulk_end = st.date_input("終了日", min_value=today, value=today + timedelta(days=13), key="be")
        skip_weekend = st.checkbox("土日を除く", value=True)

        if st.button("一括注文する"):
            if bulk_end < bulk_start:
                st.error("終了日は開始日以降にしてください")
            else:
                ok_cnt = fail_cnt = skip_cnt = 0
                d = bulk_start
                while d <= bulk_end:
                    if skip_weekend and d.weekday() >= 5:
                        skip_cnt += 1
                        d += timedelta(days=1)
                        continue
                    can, _ = utils.can_order(d)
                    if can:
                        ok2, _ = db.place_order(user["user_id"], str(d), user["user_id"])
                        if ok2:
                            ok_cnt += 1
                        else:
                            fail_cnt += 1
                    d += timedelta(days=1)
                st.success(f"✅ {ok_cnt}件 注文完了" + (f"（重複等で {fail_cnt}件スキップ）" if fail_cnt else ""))
                st.rerun()

    # ── 右：今月の注文一覧 ────────────────────────────────────
    with right:
        st.subheader(f"📋 {today.year}年{today.month}月の注文")
        orders_df = db.get_user_orders(user["user_id"], today.year, today.month)
        total_cost = len(orders_df) * unit_price

        m1, m2 = st.columns(2)
        m1.metric("注文数", f"{len(orders_df)} 件")
        m2.metric("今月の合計", f"¥{total_cost:,}")

        if orders_df.empty:
            st.info("今月の注文はありません")
        else:
            for _, row in orders_df.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                    c1.markdown(f"📅 **{row['order_date']}**" + (" 🔄" if row["is_proxy"] else ""))
                    c2.markdown(f"¥{unit_price:,}")
                    can, _ = utils.can_order(date.fromisoformat(row["order_date"]))
                    if can:
                        if c3.button("取消", key=f"cxl_{row['order_id']}"):
                            ok, msg = db.cancel_order(row["order_id"], user["user_id"], bool(user["is_admin"]))
                            st.success(msg) if ok else st.error(msg)
                            if ok:
                                st.rerun()
                    else:
                        c3.markdown("🔒")
                    if row["is_proxy"]:
                        c4.markdown(f"by {row['orderer_name']}", help="代理注文")


# ─── ページ：カレンダー ───────────────────────────────────────────────────────────
def page_calendar():
    user = st.session_state.user
    st.title("📅 カレンダー")

    today = date.today()
    if "cal_y" not in st.session_state:
        st.session_state.cal_y = today.year
        st.session_state.cal_m = today.month

    hd_col, title_col, nd_col = st.columns([1, 4, 1])
    with hd_col:
        if st.button("◀ 前月"):
            m = st.session_state.cal_m - 1
            y = st.session_state.cal_y
            if m == 0:
                m, y = 12, y - 1
            st.session_state.cal_y, st.session_state.cal_m = y, m
            st.rerun()
    with title_col:
        st.markdown(
            f"<h3 style='text-align:center'>{st.session_state.cal_y}年 {st.session_state.cal_m}月</h3>",
            unsafe_allow_html=True
        )
    with nd_col:
        if st.button("翌月 ▶"):
            m = st.session_state.cal_m + 1
            y = st.session_state.cal_y
            if m == 13:
                m, y = 1, y + 1
            st.session_state.cal_y, st.session_state.cal_m = y, m
            st.rerun()

    year, month = st.session_state.cal_y, st.session_state.cal_m
    orders_df = db.get_user_orders(user["user_id"], year, month)
    ordered_dates = set(orders_df["order_date"].tolist()) if not orders_df.empty else set()
    holidays_df = db.get_holidays(year, month)
    holiday_dates = {row["holiday_date"]: row["description"] for _, row in holidays_df.iterrows()}

    # 凡例
    st.markdown("🟢 注文済　🔴 休日・土日　🔵 今日（枠）　⬜ 注文可能")
    st.markdown("---")

    # 曜日ヘッダー
    headers = ["月", "火", "水", "木", "金", "土", "日"]
    h_cols = st.columns(7)
    for i, h in enumerate(headers):
        color = "#dc3545" if i >= 5 else "#333"
        h_cols[i].markdown(f"<div style='text-align:center;font-weight:bold;color:{color}'>{h}</div>",
                           unsafe_allow_html=True)

    # カレンダーグリッド
    weeks = cal_module.monthcalendar(year, month)
    for week in weeks:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:64px'></div>", unsafe_allow_html=True)
                    continue

                d = date(year, month, day)
                date_str = d.strftime("%Y-%m-%d")
                is_today = d == today
                is_ordered = date_str in ordered_dates
                is_hol = date_str in holiday_dates or i >= 5
                is_past = d < today

                style = "border:1px solid #ddd;border-radius:6px;padding:6px 2px;text-align:center;min-height:64px;"
                if is_today:
                    style += "border:3px solid #007bff !important;"
                if is_ordered:
                    style += "background:#d4edda;"
                elif is_hol:
                    style += "background:#f8d7da;color:#721c24;"
                elif is_past:
                    style += "opacity:0.5;"

                icon = "🍱" if is_ordered else ("🔴" if is_hol else "")
                tip = holiday_dates.get(date_str, "")
                day_label = f"<b>{day}</b><br>{icon}"
                if tip:
                    day_label += f"<br><small>{tip}</small>"

                st.markdown(f"<div style='{style}'>{day_label}</div>", unsafe_allow_html=True)

    # 日付指定で注文/キャンセル
    st.markdown("---")
    st.subheader("📝 日付を指定して注文 / キャンセル")
    sel_date = st.date_input("日付", value=today, key="cal_sel")
    date_str = str(sel_date)
    can, reason = utils.can_order(sel_date)

    # 当日の注文確認
    existing = orders_df[orders_df["order_date"] == date_str] if not orders_df.empty else pd.DataFrame()

    if not can:
        st.warning(f"🔒 {reason}")
    elif db.is_holiday(date_str) or sel_date.weekday() >= 5:
        st.warning("🔴 休日または土日のため注文できません")
    elif not existing.empty:
        st.info("✅ この日はすでに注文済みです")
        if st.button("キャンセルする", type="secondary"):
            ok, msg = db.cancel_order(existing.iloc[0]["order_id"], user["user_id"], bool(user["is_admin"]))
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()
    else:
        if st.button("注文する", type="primary"):
            ok, msg = db.place_order(user["user_id"], date_str, user["user_id"])
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()


# ─── ページ：代理注文 ─────────────────────────────────────────────────────────────
def page_proxy():
    user = st.session_state.user
    st.title("🔄 代理注文")
    st.info("他のユーザーの代わりに注文・キャンセルを行えます。費用は対象者に計上されます。")

    users_df = db.get_all_users()
    others = users_df[users_df["user_id"] != user["user_id"]]
    if others.empty:
        st.warning("対象ユーザーがいません")
        return

    options = {f"{r['name']}（{r['affiliation']} / {r['payment_type']}）": r["user_id"]
               for _, r in others.iterrows()}
    selected_label = st.selectbox("対象者を選択", list(options.keys()))
    target_id = options[selected_label]

    today = date.today()
    order_date = st.date_input("注文日", min_value=today, value=today, key="proxy_date")
    can, reason = utils.can_order(order_date)
    if not can:
        st.warning(f"🔒 {reason}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("代理注文する", type="primary", disabled=not can):
            ok, msg = db.place_order(target_id, str(order_date), user["user_id"])
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()
    with c2:
        if st.button("代理キャンセル", disabled=not can):
            target_orders = db.get_user_orders(target_id, order_date.year, order_date.month)
            match = target_orders[target_orders["order_date"] == str(order_date)] if not target_orders.empty else pd.DataFrame()
            if match.empty:
                st.warning("該当日の有効な注文が見つかりません")
            else:
                ok, msg = db.cancel_order(match.iloc[0]["order_id"], user["user_id"], bool(user["is_admin"]))
                st.success(msg) if ok else st.error(msg)
                if ok:
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 代理注文履歴")
    hist = db.get_proxy_history(user["user_id"])
    if hist.empty:
        st.info("代理注文の履歴はありません")
    else:
        display = hist[["order_date", "target_name", "orderer_name", "status", "registered_at"]].copy()
        display.columns = ["注文日", "対象者", "注文者（操作者）", "ステータス", "登録日時"]
        st.dataframe(display, use_container_width=True, hide_index=True)


# ─── ページ：管理者ダッシュボード ────────────────────────────────────────────────
def page_dashboard():
    require_admin()
    st.title("📊 管理者ダッシュボード")

    today = date.today()
    ya, ma = st.columns(2)
    with ya:
        sel_year = st.selectbox("年", list(range(today.year - 1, today.year + 2)), index=1)
    with ma:
        sel_month = st.selectbox("月", list(range(1, 13)), index=today.month - 1)

    orders_df = db.get_all_orders(sel_year, sel_month)
    unit_price = db.get_unit_price()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("総注文数", f"{len(orders_df)} 件")
    m2.metric("注文者数", f"{orders_df['user_id'].nunique() if not orders_df.empty else 0} 人")
    m3.metric("売上合計", f"¥{len(orders_df) * unit_price:,}")
    m4.metric("弁当単価", f"¥{unit_price:,}")

    st.markdown("---")

    if not orders_df.empty:
        # 日別グラフ
        st.subheader("📈 日別注文数")
        daily = orders_df.groupby("order_date").size().reset_index(name="注文数")
        st.bar_chart(daily.set_index("order_date"))

        # 注文一覧テーブル
        st.subheader("📋 注文一覧")
        disp = orders_df[["order_date", "user_name", "affiliation", "payment_type",
                           "orderer_name", "is_proxy", "registered_at"]].copy()
        disp.columns = ["注文日", "対象者", "所属", "支払区分", "注文者（操作者）", "代理", "登録日時"]
        disp["代理"] = disp["代理"].map({0: "", 1: "✓"})
        st.dataframe(disp, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📤 データエクスポート")
        dl1, dl2 = st.columns(2)

        with dl1:
            csv = disp.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 CSV ダウンロード",
                csv,
                f"orders_{sel_year}{sel_month:02d}.csv",
                "text/csv",
                use_container_width=True,
            )

        with dl2:
            xlsx = utils.export_orders_excel(disp, sel_year, sel_month)
            st.download_button(
                "📊 Excel ダウンロード",
                xlsx,
                f"orders_{sel_year}{sel_month:02d}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # 発注書 PDF
        st.markdown("---")
        st.subheader("📄 発注書 PDF 生成 / FAX 送信（シミュレーション）")
        fax_col1, fax_col2 = st.columns([2, 2])
        with fax_col1:
            export_date = st.date_input("発注書の日付（弁当受取日）",
                                        value=today + timedelta(days=1), key="fax_date")
        with fax_col2:
            qty = len(orders_df[orders_df["order_date"] == str(export_date)])
            st.metric("当日の注文数", f"{qty} 件")

        if st.button(f"📄 発注書PDF を生成して FAX 送信（{qty}件）", type="primary"):
            try:
                pdf_bytes = utils.generate_order_pdf(str(export_date), qty, unit_price)
                db.log_fax(str(export_date), qty, "送信済み（シミュレーション）")
                st.success("✅ PDF 生成・FAX 送信完了（シミュレーション）")
                st.download_button(
                    "📥 発注書PDF をダウンロード",
                    pdf_bytes,
                    f"order_{export_date}.pdf",
                    "application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF 生成エラー: {e}")

        # FAX ログ
        with st.expander("📋 FAX 送信ログ"):
            fax_df = db.get_fax_logs()
            if fax_df.empty:
                st.info("ログなし")
            else:
                st.dataframe(fax_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"{sel_year}年{sel_month}月の注文データはありません")

    # ─── 会社カレンダー管理 ──────────────────────────────────────
    st.markdown("---")
    st.subheader("📆 会社カレンダー管理（休日・休業日設定）")

    hcol1, hcol2 = st.columns(2)
    with hcol1:
        st.markdown("**休日を追加**")
        new_hdate = st.date_input("日付", key="new_hday")
        new_hdesc = st.text_input("説明（例：夏季休暇）", value="休日")
        if st.button("追加", type="primary"):
            ok = db.add_holiday(str(new_hdate), new_hdesc)
            st.success(f"{new_hdate} を休日登録しました") if ok else st.error("すでに登録済みです")
            st.rerun()

    with hcol2:
        st.markdown(f"**{sel_year}年の休日一覧**")
        h_df = db.get_holidays(sel_year)
        if h_df.empty:
            st.info("登録なし")
        else:
            for _, hr in h_df.iterrows():
                rc1, rc2 = st.columns([4, 1])
                rc1.write(f"📅 {hr['holiday_date']}（{hr['description']}）")
                if rc2.button("削除", key=f"dh_{hr['id']}"):
                    db.remove_holiday(hr["id"])
                    st.rerun()

    # ─── 弁当単価設定 ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚙️ 弁当設定")
    cur_price = db.get_unit_price()
    new_price = st.number_input("弁当単価（円）", value=cur_price, min_value=1, step=10)
    if st.button("単価を更新"):
        db.update_unit_price(int(new_price))
        st.success(f"単価を ¥{new_price:,} に更新しました")
        st.rerun()


# ─── ページ：ユーザー管理 ──────────────────────────────────────────────────────────
def page_users():
    require_admin()
    st.title("👥 ユーザー管理")

    tab_list, tab_edit = st.tabs(["ユーザー一覧", "追加 / 編集"])

    with tab_list:
        df = db.get_all_users(include_inactive=True)
        if df.empty:
            st.info("ユーザーなし")
        else:
            disp = df[["user_id", "name", "affiliation", "payment_type", "is_active", "is_admin"]].copy()
            disp.columns = ["メール(ID)", "氏名", "所属区分", "支払区分", "有効", "管理者"]
            disp["有効"] = disp["有効"].map({1: "✅", 0: "❌"})
            disp["管理者"] = disp["管理者"].map({1: "👑", 0: ""})
            st.dataframe(disp, use_container_width=True, hide_index=True)

    with tab_edit:
        all_users = db.get_all_users(include_inactive=True)
        options = ["(新規追加)"] + [
            f"{r['name']} <{r['user_id']}>" for _, r in all_users.iterrows()
        ]
        selected = st.selectbox("ユーザーを選択（編集）または新規追加", options)

        if selected == "(新規追加)":
            edit_id = None
            def_vals = {"user_id": "", "name": "", "affiliation": "社内",
                        "payment_type": "非現金", "email": "", "is_active": 1, "is_admin": 0}
        else:
            edit_id = selected.split("<")[1].rstrip(">")
            row = all_users[all_users["user_id"] == edit_id].iloc[0]
            def_vals = row.to_dict()

        with st.form("user_form"):
            if edit_id:
                st.text_input("メールアドレス（ID）", value=def_vals["user_id"], disabled=True)
                user_id_input = edit_id
            else:
                user_id_input = st.text_input("メールアドレス（ID）", value="")

            name = st.text_input("氏名", value=def_vals["name"])
            affil = st.selectbox("所属区分", ["社内", "出向者"],
                                 index=0 if def_vals["affiliation"] == "社内" else 1)
            payment = st.selectbox("支払区分", ["現金", "非現金"],
                                   index=0 if def_vals["payment_type"] == "現金" else 1)
            email = st.text_input("メールアドレス（通知先）", value=def_vals.get("email", ""))
            is_active = st.checkbox("有効", value=bool(def_vals["is_active"]))
            is_admin = st.checkbox("管理者権限", value=bool(def_vals["is_admin"]))
            pw = st.text_input("パスワード（変更する場合のみ入力）", type="password")

            if st.form_submit_button("保存", type="primary"):
                uid = user_id_input.strip()
                if not uid or not name:
                    st.error("ID と氏名は必須です")
                else:
                    db.upsert_user(uid, name, affil, payment, email or uid,
                                   is_active, is_admin, pw or None)
                    action = "更新" if edit_id else "登録"
                    st.success(f"✅ {name} を{action}しました")
                    st.rerun()


# ─── ページ：費用集計 ──────────────────────────────────────────────────────────────
def page_cost():
    user = st.session_state.user
    # 管理者は全員、一般ユーザーは自分のみ
    is_admin = bool(user["is_admin"])

    st.title("💰 費用集計")

    today = date.today()
    ya, ma = st.columns(2)
    with ya:
        sel_year = st.selectbox("年", list(range(today.year - 1, today.year + 2)), index=1)
    with ma:
        sel_month = st.selectbox("月", list(range(1, 13)), index=today.month - 1)

    summary_df, unit_price = db.get_monthly_summary(sel_year, sel_month)

    if not is_admin:
        # 一般ユーザーは自分のみ表示
        summary_df = summary_df[summary_df["user_id"] == user["user_id"]]

    total_orders = int(summary_df["order_count"].sum())
    total_amount = int(summary_df["total_amount"].sum())
    cash_amount = int(summary_df[summary_df["payment_type"] == "現金"]["total_amount"].sum())

    m1, m2, m3 = st.columns(3)
    m1.metric("注文数合計", f"{total_orders} 件")
    m2.metric("合計金額", f"¥{total_amount:,}")
    if is_admin:
        m3.metric("現金払い合計", f"¥{cash_amount:,}")

    st.markdown("---")

    if is_admin:
        tab_cash, tab_noncash, tab_all = st.tabs(["現金払い", "非現金払い", "全件"])

        with tab_cash:
            df_c = summary_df[summary_df["payment_type"] == "現金"].copy()
            _render_cost_table(df_c)
            if not df_c.empty and st.button("📧 現金払いユーザーへ月次通知メール送信（シミュレーション）"):
                for _, r in df_c.iterrows():
                    if r["order_count"] > 0:
                        st.info(f"📧 → {r['name']}（{r['email'] if 'email' in r else r['user_id']}）: "
                                f"{sel_year}/{sel_month} お弁当代 ¥{r['total_amount']:,}")
                st.success("通知送信完了（シミュレーション）")

        with tab_noncash:
            df_n = summary_df[summary_df["payment_type"] == "非現金"].copy()
            _render_cost_table(df_n)

        with tab_all:
            _render_cost_table(summary_df)
            xlsx = utils.export_orders_excel(
                summary_df[["name", "affiliation", "payment_type", "order_count", "total_amount"]].rename(
                    columns={"name": "氏名", "affiliation": "所属", "payment_type": "支払区分",
                             "order_count": "注文数", "total_amount": "合計金額"}
                ),
                sel_year, sel_month
            )
            st.download_button(
                f"📊 費用集計 Excel（{sel_year}年{sel_month}月）",
                xlsx,
                f"cost_{sel_year}{sel_month:02d}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    else:
        # 自分の集計のみ
        my = summary_df.iloc[0] if not summary_df.empty else None
        if my is not None:
            st.markdown(f"**{sel_year}年{sel_month}月の注文状況**")
            with st.container(border=True):
                st.markdown(f"- 注文数：**{int(my['order_count'])} 件**")
                st.markdown(f"- 合計金額：**¥{int(my['total_amount']):,}**")
                st.markdown(f"- 支払区分：{my['payment_type']}")


def _render_cost_table(df: pd.DataFrame):
    if df.empty:
        st.info("データなし")
        return
    disp = df[["name", "affiliation", "payment_type", "order_count", "total_amount"]].copy()
    disp.columns = ["氏名", "所属", "支払区分", "注文数", "合計金額（円）"]
    disp["合計金額（円）"] = disp["合計金額（円）"].apply(lambda x: f"¥{int(x):,}")
    st.dataframe(disp, use_container_width=True, hide_index=True)


# ─── メイン ────────────────────────────────────────────────────────────────────────
def main():
    check_auth()

    if "page" not in st.session_state:
        st.session_state.page = "order"

    render_sidebar()

    page = st.session_state.page
    dispatch = {
        "order":     page_order,
        "calendar":  page_calendar,
        "proxy":     page_proxy,
        "dashboard": page_dashboard,
        "users":     page_users,
        "cost":      page_cost,
    }
    dispatch.get(page, page_order)()


if __name__ == "__main__":
    main()
