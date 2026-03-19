import pandas as pd

from task import Task


def to_csv_bytes(tasks: list[Task]) -> bytes:
    df = pd.DataFrame([
        {
            "ID":     t.id,
            "タイトル": t.title,
            "メモ":    t.memo,
            "期限":    str(t.due_date) if t.due_date else "",
            "優先度":  t.priority,
            "完了":    "済" if t.done else "",
        }
        for t in tasks
    ])
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
