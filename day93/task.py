from dataclasses import dataclass
from datetime import datetime


@dataclass
class Task:
    title: str
    priority: str  # 高 / 中 / 低
    id: int = 0
    memo: str = ""
    due_date: datetime | None = None
    done: bool = False
