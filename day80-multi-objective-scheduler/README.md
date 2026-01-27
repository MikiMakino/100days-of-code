# Day 80: Multi-Objective Task Scheduler

A task scheduling optimization application with selectable objective functions.

## Features

- **Multiple Objective Functions**: Choose from 4 different optimization goals
  - Total Tardiness (Σ tardiness)
  - Tardy Task Count
  - Maximum Tardiness
  - Total Completion Time

- **Algorithm Comparison**: Compare 4 scheduling algorithms
  - EDF (Earliest Deadline First)
  - SPT (Shortest Processing Time)
  - EDF + Local Search (Swap Improvement)
  - Brute Force (Optimal)

- **Visual Gantt Chart**: Interactive schedule visualization with deadline markers

- **Performance Metrics**: Computation time and candidate count comparison

## Screenshot

```
┌─────────────────────────────────────────────────────────────┐
│  🗓️ 作業スケジューラ最適化（目的を選べる）                    │
├─────────────────────────────────────────────────────────────┤
│  📐 最適化の目的関数を選択:                                   │
│  ○ 遅延時間  ○ 遅延タスク数  ○ 最大遅延  ○ 完了時刻          │
├─────────────────────────────────────────────────────────────┤
│  [Task List]              │  [Optimization Results]         │
│  - レポート作成 30分 60分  │  EDF: 遅延時間 = 25             │
│  - メール返信  15分 30分   │  SPT: 遅延時間 = 35             │
│  - 会議準備   20分 45分   │  EDF+改善: 遅延時間 = 20        │
│  ...                      │  最適: 遅延時間 = 20            │
├─────────────────────────────────────────────────────────────┤
│  📈 Gantt Chart                                             │
│  [Visual schedule comparison with bars and deadlines]       │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# No additional packages required (uses standard library only)
python task_scheduler.py
```

## Requirements

- Python 3.8+
- tkinter (included with Python)

## How It Works

### Objective Functions

| Objective | Formula | Optimal Algorithm |
|-----------|---------|-------------------|
| Total Tardiness | Σ max(0, Cᵢ - dᵢ) | Brute Force |
| Tardy Count | count(Cᵢ > dᵢ) | Brute Force |
| Max Tardiness | max(0, Cᵢ - dᵢ) | EDF (proven optimal) |
| Total Completion | Σ Cᵢ | SPT (proven optimal) |

Where Cᵢ = completion time, dᵢ = deadline

### Algorithms

1. **EDF (Earliest Deadline First)**
   - Sort tasks by deadline (ascending)
   - O(n log n) complexity
   - Optimal for minimizing maximum tardiness

2. **SPT (Shortest Processing Time)**
   - Sort tasks by duration (ascending)
   - O(n log n) complexity
   - Optimal for minimizing total completion time

3. **EDF + Swap Improvement**
   - Start with EDF solution
   - Apply pairwise swap local search
   - Good balance of speed and quality

4. **Brute Force**
   - Evaluate all n! permutations
   - Guarantees optimal solution
   - O(n! × n) complexity

## Project Structure

```
day80-multi-objective-scheduler/
├── task_scheduler.py   # Main application
├── README.md          # This file
├── guide.md           # User guide
└── flowchart.md       # Program flow diagrams
```

## Technical Details

- **Threading**: Optimization runs in a background thread to keep UI responsive
- **Data Classes**: Uses Python dataclasses for immutable Task objects
- **Enum Types**: Type-safe objective function selection
- **Local Search**: Implements first-improvement swap-based optimization

## License

MIT License - Part of 100 Days of Code challenge
