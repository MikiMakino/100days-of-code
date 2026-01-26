"""
Day 79: 作業スケジューラ最適化アプリ（tkinter）
- 総当たり法（最適） vs ヒューリスティック法（EDF / SPT） vs 改善（EDF+Swap）
- 目的：締切遅延（tardiness = max(0, 完了時刻 - 締切)）の合計を最小化
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from itertools import permutations
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
import math
import threading


# -----------------------------
# Data Models
# -----------------------------
@dataclass(frozen=True)
class Task:
    """タスクを表すデータクラス"""
    name: str
    duration: int      # 所要時間（分）
    deadline: int      # 締切（開始からの分数）

    def __str__(self) -> str:
        return f"{self.name} ({self.duration}分, 締切:{self.deadline}分)"


class ScheduleResult:
    """スケジューリング結果"""
    def __init__(self, order: List[Task], total_delay: int, computation_time: float, candidates: int = 1):
        self.order = order
        self.total_delay = total_delay
        self.computation_time = computation_time
        self.candidates = candidates  # 試した候補数
        self.schedule: List[Tuple[Task, int, int, int]] = []  # (task, start, end, delay)
        self._calculate_schedule()

    def _calculate_schedule(self) -> None:
        """スケジュール詳細を計算"""
        self.schedule.clear()
        current_time = 0
        for task in self.order:
            start = current_time
            end = current_time + task.duration
            delay = max(0, end - task.deadline)
            self.schedule.append((task, start, end, delay))
            current_time = end

    @property
    def makespan(self) -> int:
        if not self.schedule:
            return 0
        return self.schedule[-1][2]

    @property
    def tardy_count(self) -> int:
        return sum(1 for *_, delay in self.schedule if delay > 0)

    @property
    def max_delay(self) -> int:
        return max((delay for *_, delay in self.schedule), default=0)


# -----------------------------
# Core Optimization Logic
# -----------------------------
def calculate_total_delay(order: List[Task]) -> int:
    """総遅延時間（Σ max(0, 完了 - 締切)）を計算"""
    current_time = 0
    total_delay = 0
    for task in order:
        current_time += task.duration
        total_delay += max(0, current_time - task.deadline)
    return total_delay


def improve_by_swaps(order: List[Task], max_iters: int = 4000) -> Tuple[List[Task], int]:
    """
    ローカル探索（swap改善）:
    2つのタスクを入れ替えて遅延合計が改善するなら採用、を繰り返す。
    返り値: (改善後の順序, 試したswap候補数)
    """
    best = order[:]
    best_delay = calculate_total_delay(best)
    n = len(best)
    candidates = 0

    for _ in range(max_iters):
        improved = False
        for i in range(n):
            for j in range(i + 1, n):
                candidates += 1
                trial = best[:]
                trial[i], trial[j] = trial[j], trial[i]
                d = calculate_total_delay(trial)
                if d < best_delay:
                    best, best_delay = trial, d
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break

    return best, candidates


# -----------------------------
# App
# -----------------------------
class TaskSchedulerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("作業スケジューラ最適化 - Day 79")
        self.root.geometry("1200x820")
        self.root.configure(bg="#1a1a2e")

        self.font_family = "Yu Gothic UI"
        self.font_mono = "MS Gothic"

        self.tasks: List[Task] = []

        # results
        self.res_edf: Optional[ScheduleResult] = None
        self.res_spt: Optional[ScheduleResult] = None
        self.res_edf_improved: Optional[ScheduleResult] = None
        self.res_bruteforce: Optional[ScheduleResult] = None

        # selection for gantt
        self.gantt_mode = tk.StringVar(value="4")  # "4" or "2"

        self.setup_ui()
        self.add_sample_tasks()

    # -------------------------
    # UI
    # -------------------------
    def setup_ui(self) -> None:
        main_frame = tk.Frame(self.root, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        title = tk.Label(
            main_frame,
            text="🗓️ 作業スケジューラ最適化（EDF / SPT / EDF+改善 / 最適）",
            font=(self.font_family, 20, "bold"),
            bg="#1a1a2e",
            fg="#e94560",
        )
        title.pack(pady=(0, 12))

        # -------------------------
        # Input
        # -------------------------
        input_frame = tk.Frame(main_frame, bg="#16213e", relief=tk.RIDGE, bd=2)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        entry_frame = tk.Frame(input_frame, bg="#16213e")
        entry_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(entry_frame, text="タスク名:", bg="#16213e", fg="white",
                 font=(self.font_family, 11)).pack(side=tk.LEFT, padx=5)
        self.name_entry = tk.Entry(entry_frame, width=16, font=(self.font_family, 11))
        self.name_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(entry_frame, text="所要時間(分):", bg="#16213e", fg="white",
                 font=(self.font_family, 11)).pack(side=tk.LEFT, padx=5)
        self.duration_entry = tk.Entry(entry_frame, width=8, font=(self.font_family, 11))
        self.duration_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(entry_frame, text="締切(分後):", bg="#16213e", fg="white",
                 font=(self.font_family, 11)).pack(side=tk.LEFT, padx=5)
        self.deadline_entry = tk.Entry(entry_frame, width=8, font=(self.font_family, 11))
        self.deadline_entry.pack(side=tk.LEFT, padx=5)

        btn_frame = tk.Frame(input_frame, bg="#16213e")
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(
            btn_frame, text="➕ タスク追加", command=self.add_task,
            bg="#0f3460", fg="white", font=(self.font_family, 10, "bold"),
            relief=tk.FLAT, padx=15, pady=5
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="🗑️ 選択削除", command=self.delete_task,
            bg="#e94560", fg="white", font=(self.font_family, 10, "bold"),
            relief=tk.FLAT, padx=15, pady=5
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="🔄 全クリア", command=self.clear_tasks,
            bg="#6c757d", fg="white", font=(self.font_family, 10, "bold"),
            relief=tk.FLAT, padx=15, pady=5
        ).pack(side=tk.LEFT, padx=5)

        # Radio: Gantt show mode
        mode_frame = tk.Frame(btn_frame, bg="#16213e")
        mode_frame.pack(side=tk.LEFT, padx=15)

        tk.Label(mode_frame, text="ガント表示:", bg="#16213e", fg="#aaa",
                 font=(self.font_family, 10)).pack(side=tk.LEFT, padx=(0, 5))
        tk.Radiobutton(
            mode_frame, text="4本", variable=self.gantt_mode, value="4",
            bg="#16213e", fg="white", selectcolor="#16213e",
            activebackground="#16213e", activeforeground="white",
            font=(self.font_family, 10),
            command=self.draw_gantt_chart_safe
        ).pack(side=tk.LEFT)
        tk.Radiobutton(
            mode_frame, text="2本（最適と比較）", variable=self.gantt_mode, value="2",
            bg="#16213e", fg="white", selectcolor="#16213e",
            activebackground="#16213e", activeforeground="white",
            font=(self.font_family, 10),
            command=self.draw_gantt_chart_safe
        ).pack(side=tk.LEFT)

        self.optimize_btn = tk.Button(
            btn_frame, text="⚡ 最適化実行", command=self.optimize,
            bg="#00d9ff", fg="black", font=(self.font_family, 11, "bold"),
            relief=tk.FLAT, padx=22, pady=5
        )
        self.optimize_btn.pack(side=tk.RIGHT, padx=5)

        # -------------------------
        # Middle: list + results
        # -------------------------
        middle_frame = tk.Frame(main_frame, bg="#1a1a2e")
        middle_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(middle_frame, bg="#16213e", relief=tk.RIDGE, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(
            left_frame, text="📋 タスク一覧",
            font=(self.font_family, 12, "bold"),
            bg="#16213e", fg="#00d9ff"
        ).pack(pady=5)

        columns = ("name", "duration", "deadline")
        self.task_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=10)
        self.task_tree.heading("name", text="タスク名")
        self.task_tree.heading("duration", text="所要時間")
        self.task_tree.heading("deadline", text="締切")
        self.task_tree.column("name", width=160)
        self.task_tree.column("duration", width=90, anchor=tk.CENTER)
        self.task_tree.column("deadline", width=90, anchor=tk.CENTER)
        self.task_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.info_label = tk.Label(
            left_frame, text="", font=(self.font_family, 10),
            bg="#16213e", fg="#aaa"
        )
        self.info_label.pack(pady=5)

        right_frame = tk.Frame(middle_frame, bg="#16213e", relief=tk.RIDGE, bd=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(
            right_frame, text="📊 最適化結果（4比較）",
            font=(self.font_family, 12, "bold"),
            bg="#16213e", fg="#00d9ff"
        ).pack(pady=5)

        self.result_text = tk.Text(
            right_frame, height=12,
            bg="#0f3460", fg="white",
            font=(self.font_mono, 10),
            relief=tk.FLAT
        )
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # -------------------------
        # Gantt
        # -------------------------
        chart_frame = tk.Frame(main_frame, bg="#16213e", relief=tk.RIDGE, bd=2)
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        tk.Label(
            chart_frame, text="📈 スケジュール比較（ガントチャート）",
            font=(self.font_family, 12, "bold"),
            bg="#16213e", fg="#00d9ff"
        ).pack(pady=5)

        self.canvas = tk.Canvas(chart_frame, bg="#0f3460", height=260, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # -------------------------
    # Task operations
    # -------------------------
    def add_sample_tasks(self) -> None:
        samples = [
            ("レポート作成", 30, 60),
            ("メール返信", 15, 30),
            ("会議準備", 20, 45),
            ("データ整理", 25, 90),
            ("資料確認", 10, 40),
        ]
        self.tasks.clear()
        for name, duration, deadline in samples:
            self.tasks.append(Task(name, duration, deadline))
        self.update_task_list()

    def add_task(self) -> None:
        try:
            name = self.name_entry.get().strip()
            duration = int(self.duration_entry.get())
            deadline = int(self.deadline_entry.get())

            if not name:
                messagebox.showwarning("入力エラー", "タスク名を入力してください")
                return
            if duration <= 0 or deadline <= 0:
                messagebox.showwarning("入力エラー", "正の数を入力してください")
                return

            self.tasks.append(Task(name, duration, deadline))
            self.update_task_list()

            self.name_entry.delete(0, tk.END)
            self.duration_entry.delete(0, tk.END)
            self.deadline_entry.delete(0, tk.END)

        except ValueError:
            messagebox.showwarning("入力エラー", "数値を正しく入力してください")

    def delete_task(self) -> None:
        selected = self.task_tree.selection()
        if selected:
            idx = self.task_tree.index(selected[0])
            if 0 <= idx < len(self.tasks):
                del self.tasks[idx]
            self.update_task_list()

    def clear_tasks(self) -> None:
        self.tasks.clear()
        self.update_task_list()
        self.result_text.delete(1.0, tk.END)
        self.canvas.delete("all")
        self.res_edf = self.res_spt = self.res_edf_improved = self.res_bruteforce = None

    def update_task_list(self) -> None:
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        for task in self.tasks:
            self.task_tree.insert("", tk.END, values=(task.name, f"{task.duration}分", f"{task.deadline}分後"))

        n = len(self.tasks)
        if n > 0:
            factorial = math.factorial(n)
            info = f"タスク数: {n}個 | 総当たり: {n}! = {factorial:,}通り"
            if n > 10:
                info += " ⚠️ 非常に時間がかかる可能性"
            self.info_label.config(text=info)
        else:
            self.info_label.config(text="")

    # -------------------------
    # Optimization methods
    # -------------------------
    def heuristic_edf(self) -> ScheduleResult:
        """EDF/EDD: 締切が早い順"""
        start = time.perf_counter()
        order = sorted(self.tasks, key=lambda t: t.deadline)
        total_delay = calculate_total_delay(order)
        elapsed = time.perf_counter() - start
        return ScheduleResult(order, total_delay, elapsed, candidates=1)

    def heuristic_spt(self) -> ScheduleResult:
        """SPT: 所要時間が短い順"""
        start = time.perf_counter()
        order = sorted(self.tasks, key=lambda t: t.duration)
        total_delay = calculate_total_delay(order)
        elapsed = time.perf_counter() - start
        return ScheduleResult(order, total_delay, elapsed, candidates=1)

    def heuristic_edf_improve(self) -> ScheduleResult:
        """EDF → swap改善（ローカル探索）"""
        start = time.perf_counter()
        base = sorted(self.tasks, key=lambda t: t.deadline)
        improved, cands = improve_by_swaps(base, max_iters=6000)
        total_delay = calculate_total_delay(improved)
        elapsed = time.perf_counter() - start
        return ScheduleResult(improved, total_delay, elapsed, candidates=(1 + cands))

    def brute_force_optimize(self) -> ScheduleResult:
        """総当たりで最適解を探す（nが大きいと爆発）"""
        start = time.perf_counter()

        best_order: Optional[List[Task]] = None
        best_delay = float("inf")
        candidates = 0

        for perm in permutations(self.tasks):
            candidates += 1
            order = list(perm)
            delay = calculate_total_delay(order)
            if delay < best_delay:
                best_delay = delay
                best_order = order

        elapsed = time.perf_counter() - start
        return ScheduleResult(best_order or [], int(best_delay), elapsed, candidates=candidates)

    # -------------------------
    # Optimize (threaded)
    # -------------------------
    def optimize(self) -> None:
        if len(self.tasks) < 2:
            messagebox.showwarning("エラー", "2つ以上のタスクを追加してください")
            return

        # bruteforce safety
        n = len(self.tasks)
        if n > 10:
            if not messagebox.askyesno(
                "確認",
                f"タスクが{n}個あります。\n総当たり計算（{n}!）は時間がかかる可能性があります。\n続行しますか？"
            ):
                return

        self.optimize_btn.config(state=tk.DISABLED)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "⏳ 計算中...（EDF / SPT / EDF+改善 / 総当たり）\n")
        self.root.update()

        def worker():
            # Run light ones first (gives earlier feel, though we update at end)
            res_edf = self.heuristic_edf()
            res_spt = self.heuristic_spt()
            res_edf_imp = self.heuristic_edf_improve()

            # Bruteforce last
            res_bf = self.brute_force_optimize()

            def done():
                self.res_edf = res_edf
                self.res_spt = res_spt
                self.res_edf_improved = res_edf_imp
                self.res_bruteforce = res_bf

                self.display_results()
                self.draw_gantt_chart_safe()
                self.optimize_btn.config(state=tk.NORMAL)

            self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------
    # Display
    # -------------------------
    def display_results(self) -> None:
        self.result_text.delete(1.0, tk.END)

        if not (self.res_edf and self.res_spt and self.res_edf_improved and self.res_bruteforce):
            self.result_text.insert(tk.END, "結果がありません。\n")
            return

        # Make summary table
        rows = [
            ("EDF（締切順）", self.res_edf),
            ("SPT（短い順）", self.res_spt),
            ("EDF+改善（swap）", self.res_edf_improved),
            ("最適（総当たり）", self.res_bruteforce),
        ]

        def line_res(name: str, r: ScheduleResult) -> str:
            order = " → ".join(t.name for t in r.order)
            return (
                f"[{name}]\n"
                f"  計算: {r.computation_time*1000:.3f} ms | 候補: {r.candidates:,}\n"
                f"  Σ遅延: {r.total_delay}分 | 遅延件数: {r.tardy_count} | 最大遅延: {r.max_delay} | 総所要: {r.makespan}\n"
                f"  順序: {order}\n"
            )

        self.result_text.insert(tk.END, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        self.result_text.insert(tk.END, "📌 目的：Σ max(0, 完了時刻 - 締切) を最小化\n")
        self.result_text.insert(tk.END, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

        for name, r in rows:
            self.result_text.insert(tk.END, line_res(name, r))
            self.result_text.insert(tk.END, "\n")

        # Comparison with optimal
        opt = self.res_bruteforce.total_delay
        self.result_text.insert(tk.END, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        self.result_text.insert(tk.END, "📊 最適（総当たり）との比較（差分=多いほど悪い）\n")
        self.result_text.insert(tk.END, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        for name, r in rows[:-1]:
            diff = r.total_delay - opt
            if diff == 0:
                self.result_text.insert(tk.END, f"✅ {name}: 最適と同じ（差分0）\n")
            else:
                self.result_text.insert(tk.END, f"⚠️ {name}: 差分 +{diff}分\n")

        # Speed overview (vs brute)
        bf_ms = max(self.res_bruteforce.computation_time * 1000, 0.001)
        edf_ms = max(self.res_edf.computation_time * 1000, 0.001)
        spt_ms = max(self.res_spt.computation_time * 1000, 0.001)
        imp_ms = max(self.res_edf_improved.computation_time * 1000, 0.001)

        self.result_text.insert(tk.END, "\n⚡ 速度（総当たりを1.0xとした相対）\n")
        self.result_text.insert(tk.END, f"  EDF: {bf_ms/edf_ms:.1f}x\n")
        self.result_text.insert(tk.END, f"  SPT: {bf_ms/spt_ms:.1f}x\n")
        self.result_text.insert(tk.END, f"  EDF+改善: {bf_ms/imp_ms:.1f}x\n")

    def draw_gantt_chart_safe(self) -> None:
        # results not ready
        if not self.res_bruteforce:
            return
        self.draw_gantt_chart()

    def draw_gantt_chart(self) -> None:
        """ガントチャートを描画（4本 or 2本）"""
        self.canvas.delete("all")

        if not (self.res_edf and self.res_spt and self.res_edf_improved and self.res_bruteforce):
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width < 200:
            canvas_width = 1100
        if canvas_height < 200:
            canvas_height = 260

        # max time scale
        max_time = max(
            sum(t.duration for t in self.tasks),
            max((t.deadline for t in self.tasks), default=0),
            self.res_bruteforce.makespan
        )
        max_time = max(max_time, 1)

        margin_left = 170
        margin_right = 20
        margin_top = 30
        bar_height = 30
        gap = 12

        chart_width = canvas_width - margin_left - margin_right
        scale = chart_width / max_time

        self.canvas.create_text(
            canvas_width // 2, 15,
            text="スケジュール比較（バー=作業、赤点線=締切）",
            fill="white", font=(self.font_family, 11, "bold")
        )

        colors = ["#e94560", "#00d9ff", "#f39c12", "#2ecc71", "#9b59b6", "#1abc9c", "#ff9ff3", "#48dbfb"]

        rows_all = [
            ("EDF（締切順）", self.res_edf),
            ("SPT（短い順）", self.res_spt),
            ("EDF+改善（swap）", self.res_edf_improved),
            ("最適（総当たり）", self.res_bruteforce),
        ]

        if self.gantt_mode.get() == "2":
            # compare "best heuristic" vs optimal
            # pick the best among EDF/SPT/EDF+improve by delay
            best_h = min(
                [("EDF", self.res_edf), ("SPT", self.res_spt), ("EDF+改善", self.res_edf_improved)],
                key=lambda x: x[1].total_delay
            )
            rows = [
                (f"{best_h[0]}（ヒューリ）", best_h[1]),
                ("最適（総当たり）", self.res_bruteforce),
            ]
        else:
            rows = rows_all

        # draw each row
        for row_idx, (label, result) in enumerate(rows):
            y = margin_top + 10 + row_idx * (bar_height + gap + 14)

            # label
            self.canvas.create_text(
                margin_left - 10, y + bar_height // 2,
                text=f"{label}\nΣ遅延:{result.total_delay}",
                fill="white", anchor=tk.E, font=(self.font_family, 10)
            )

            # bars
            current_x = margin_left
            for i, (task, start, end, delay) in enumerate(result.schedule):
                width = (end - start) * scale
                color = colors[i % len(colors)]

                self.canvas.create_rectangle(
                    current_x, y, current_x + width, y + bar_height,
                    fill=color, outline="white", width=1
                )

                if width > 35:
                    self.canvas.create_text(
                        current_x + width / 2, y + bar_height / 2,
                        text=task.name[:8], fill="white",
                        font=(self.font_family, 9, "bold")
                    )

                if delay > 0:
                    self.canvas.create_text(
                        current_x + width / 2, y + bar_height + 10,
                        text=f"⚠️{delay}分遅延", fill="#ff6b6b",
                        font=(self.font_family, 8)
                    )
                current_x += width

            # deadline lines: draw once per row but only for each task deadline
            for task in self.tasks:
                deadline_x = margin_left + task.deadline * scale
                self.canvas.create_line(
                    deadline_x, y - 5, deadline_x, y + bar_height + 5,
                    fill="#ff6b6b", dash=(3, 3), width=1
                )

        # axis
        axis_y = margin_top + 10 + len(rows) * (bar_height + gap + 14) + 10
        axis_y = min(axis_y, canvas_height - 35)

        self.canvas.create_line(
            margin_left, axis_y, canvas_width - margin_right, axis_y,
            fill="white", width=2
        )

        step = max(10, max_time // 10)
        for t in range(0, max_time + 1, step):
            x = margin_left + t * scale
            self.canvas.create_line(x, axis_y - 5, x, axis_y + 5, fill="white", width=1)
            self.canvas.create_text(x, axis_y + 15, text=f"{t}分", fill="white",
                                    font=(self.font_family, 9))


def main() -> None:
    root = tk.Tk()
    app = TaskSchedulerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
