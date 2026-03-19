from datetime import date, datetime, time

import streamlit as st

import db
import exporter
from task import Task

PRIORITY_ORDER = {"高": 0, "中": 1, "低": 2}
PRIORITY_BADGE = {"高": "🔴", "中": "🟡", "低": "🟢"}


def init_session() -> None:
    st.session_state.setdefault("edit_id", None)
    st.session_state.setdefault("confirm_delete_id", None)
    st.session_state.setdefault("confirm_clear", False)


def render_sidebar(tasks: list[Task]) -> tuple[str, str]:
    with st.sidebar:
        st.header("フィルター / ソート")
        filter_status = st.radio("ステータス", ["全件", "未完了", "完了済み"], index=1)
        sort_by = st.selectbox("ソート", ["登録順", "優先度", "期限"])

        st.divider()

        csv = exporter.to_csv_bytes(tasks)
        st.download_button(
            "📥 CSV エクスポート",
            data=csv,
            file_name="todo.csv",
            mime="text/csv",
        )

        st.divider()
        render_clear_completed()

    return filter_status, sort_by


def render_clear_completed() -> None:
    if not st.session_state.confirm_clear:
        if st.button("🗑️ 完了済みを一括削除", use_container_width=True):
            st.session_state.confirm_clear = True
            st.rerun()
    else:
        st.warning("完了済みタスクを全て削除します。よろしいですか？")
        yes, no = st.columns(2)
        if yes.button("はい", type="primary"):
            db.delete_completed_tasks()
            st.session_state.confirm_clear = False
            st.rerun()
        if no.button("いいえ"):
            st.session_state.confirm_clear = False
            st.rerun()


def render_add_form() -> None:
    with st.expander("➕ タスクを追加", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            title = st.text_input("タイトル *", max_chars=100)
            memo = st.text_area("メモ", height=80)
            col1, col2, col3 = st.columns(3)
            due_date = col1.date_input("期限（日付）", value=None)
            due_time = col2.time_input("期限（時刻）", value=time(0, 0))
            priority = col3.selectbox("優先度", ["高", "中", "低"], index=1)

            if st.form_submit_button("追加", type="primary"):
                if not title.strip():
                    st.error("タイトルは必須です。")
                else:
                    due_dt = datetime.combine(due_date, due_time) if due_date else None
                    db.add_task(Task(title=title.strip(), memo=memo, due_date=due_dt, priority=priority))
                    st.success("タスクを追加しました。")
                    st.rerun()


def filter_and_sort(tasks: list[Task], filter_status: str, sort_by: str) -> list[Task]:
    match filter_status:
        case "未完了":
            tasks = [t for t in tasks if not t.done]
        case "完了済み":
            tasks = [t for t in tasks if t.done]

    match sort_by:
        case "優先度":
            tasks = sorted(tasks, key=lambda t: PRIORITY_ORDER.get(t.priority, 1))
        case "期限":
            tasks = sorted(tasks, key=lambda t: (t.due_date is None, t.due_date or datetime.max))

    return tasks


def render_edit_form(task: Task) -> None:
    with st.container(border=True):
        st.markdown("**編集中**")
        with st.form(f"edit_form_{task.id}"):
            edit_title = st.text_input("タイトル *", value=task.title)
            edit_memo = st.text_area("メモ", value=task.memo, height=80)
            col1, col2, col3 = st.columns(3)
            edit_due_date = col1.date_input(
                "期限（日付）",
                value=task.due_date.date() if task.due_date else None,
            )
            edit_due_time = col2.time_input(
                "期限（時刻）",
                value=task.due_date.time() if task.due_date else time(0, 0),
            )
            edit_priority = col3.selectbox(
                "優先度", ["高", "中", "低"],
                index=["高", "中", "低"].index(task.priority),
            )
            save_col, cancel_col = st.columns(2)
            if save_col.form_submit_button("保存", type="primary"):
                if not edit_title.strip():
                    st.error("タイトルは必須です。")
                else:
                    edit_due_dt = datetime.combine(edit_due_date, edit_due_time) if edit_due_date else None
                    db.update_task(Task(
                        id=task.id, title=edit_title.strip(), memo=edit_memo,
                        due_date=edit_due_dt, priority=edit_priority, done=task.done,
                    ))
                    st.session_state.edit_id = None
                    st.rerun()
            if cancel_col.form_submit_button("キャンセル"):
                st.session_state.edit_id = None
                st.rerun()


def render_task_row(task: Task, now: datetime) -> None:
    is_overdue = task.due_date and task.due_date < now and not task.done

    with st.container(border=True):
        col_check, col_info, col_actions = st.columns([0.5, 6, 2])

        new_done = col_check.checkbox("", value=task.done, key=f"done_{task.id}")
        if new_done != task.done:
            db.toggle_done(task.id)
            st.rerun()

        with col_info:
            badge = PRIORITY_BADGE.get(task.priority, "")
            if task.done:
                st.markdown(f"~~{task.title}~~ {badge}")
            elif is_overdue:
                st.markdown(f"**:red[{task.title}]** {badge} :red[⚠️ 期限切れ]")
            else:
                st.markdown(f"**{task.title}** {badge}")

            meta = []
            if task.due_date:
                meta.append(f"📅 {task.due_date.strftime('%Y-%m-%d %H:%M')}")
            if task.memo:
                meta.append(f"📝 {task.memo}")
            if meta:
                st.caption(" ｜ ".join(meta))

        with col_actions:
            edit_col, del_col = st.columns(2)
            if edit_col.button("編集", key=f"edit_{task.id}", disabled=task.done):
                st.session_state.edit_id = task.id
                st.rerun()
            if del_col.button("削除", key=f"del_{task.id}"):
                st.session_state.confirm_delete_id = task.id
                st.rerun()

    if st.session_state.confirm_delete_id == task.id:
        with st.container(border=True):
            st.warning(f"「{task.title}」を削除しますか？")
            yes, no = st.columns(2)
            if yes.button("削除する", key=f"confirm_yes_{task.id}", type="primary"):
                db.delete_task(task.id)
                st.session_state.confirm_delete_id = None
                st.rerun()
            if no.button("キャンセル", key=f"confirm_no_{task.id}"):
                st.session_state.confirm_delete_id = None
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="ToDoアプリ", page_icon="✅", layout="wide")
    db.init_db()
    init_session()

    st.title("✅ ToDoアプリ")

    all_tasks = db.get_all_tasks()
    filter_status, sort_by = render_sidebar(all_tasks)
    render_add_form()

    tasks = filter_and_sort(all_tasks, filter_status, sort_by)

    st.subheader(f"タスク一覧（{len(tasks)} 件）")

    if not tasks:
        st.info("タスクがありません。")
        return

    now = datetime.now()
    for task in tasks:
        if st.session_state.edit_id == task.id:
            render_edit_form(task)
        else:
            render_task_row(task, now)


if __name__ == "__main__":
    main()
