# 🐾 PawPal+

PawPal+ is a pet care planner for busy owners. It tracks feedings, walks, medications, grooming, and appointments for several pets, and it organizes them into a daily schedule. The schedule is sorted by time or priority, flags tasks that collide, repeats daily and weekly tasks automatically, and explains which tasks fit into the time you actually have.

The logic layer (`pawpal_system.py`) was built "CLI-first": a terminal demo (`main.py`) and a pytest suite verified it before it was connected to the Streamlit UI (`app.py`).

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py                   # CLI demo
streamlit run app.py             # web app
python -m pytest                 # test suite
```

## ✨ Features

- **Multi-pet households.** One owner can have any number of pets, and every scheduling feature works across all of them.
- **Sorting by time.** Tasks come back in chronological order (date, then time), no matter what order you entered them in.
- **Priority scheduling.** High-priority tasks come first, and ties are broken by time.
- **Filtering.** Show one pet's tasks, only the to-do or done tasks, or only one date. The filters can be combined.
- **Daily and weekly recurrence.** When you complete a repeating task, the next one is created automatically for tomorrow or next week. Completing the same task twice never creates duplicates.
- **Conflict warnings.** Two tasks whose time windows overlap get a readable warning, whether they are for the same pet or different pets. Both an exact time match and an overlap based on duration count. The check never crashes the program.
- **Next available slot.** PawPal+ finds the earliest gap in the day that fits a task of a given length, and the UI fills it in as the default time.
- **Time-budget plan with explanations.** Tell PawPal+ how many minutes you have. It keeps the highest-priority tasks that fit and gives a reason for every task it keeps or skips.
- **Data persistence.** Pets and tasks are saved to `data.json` and reloaded the next time you open the app.
- **Readable output.** The CLI shows tables with emoji labels for each task type and colored indicators for priority and status. The UI uses tables, success messages, and warnings.

## 🏗️ Implementation summary

| Class | Responsibility |
|-------|----------------|
| `Task` (dataclass) | One care activity: description, `"HH:MM"` time, duration, `Priority`, frequency (`once`/`daily`/`weekly`), `due_date`, completion status, and the `pet_name` it belongs to. Validates its own input, computes its start and end minutes, and builds its `next_occurrence()` with `timedelta`. |
| `Pet` (dataclass) | Pet details and its list of tasks. `add_task()` tags each task with the pet's name. |
| `Owner` | Holds the pets. `get_all_tasks()` is the single place where every pet's tasks are gathered, and it handles JSON save and load. |
| `Scheduler` | The "brain". It holds an `Owner` and reads tasks only through `owner.get_all_tasks()`, so every algorithm works across all pets. |
| `Priority` (IntEnum) | `LOW=1`, `MEDIUM=2`, `HIGH=3`, so priority sorts numerically rather than alphabetically. |
| `DailyPlan` (dataclass) | The result of `plan_day()`: the scheduled and skipped tasks, minutes used, and a reason for each task. |

The UI keeps the `Owner` in `st.session_state`, so it survives Streamlit reruns. Every widget calls a method on `Owner`, `Pet`, or `Scheduler`, and the app saves to disk after each change.

UML: [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd) (final design, also in `diagrams/uml.mmd`) and [`diagrams/uml_draft.mmd`](diagrams/uml_draft.mmd) (the Phase 1 draft).

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler.sort_by_priority()` | `sorted()` with a lambda key `(due_date, time)`. Times are stored zero-padded, so `"HH:MM"` strings sort correctly as text. The priority key is `(-priority, due_date, time)`. |
| Filtering | `Scheduler.filter_tasks(pet_name=, completed=, on=)` | Filters by pet name (case-insensitive), completion status, and date, in any combination. `None` means "don't filter on this". |
| Conflict handling | `Scheduler.detect_conflicts(on=)` | Sorts pending tasks by start time and flags every pair whose `[start, end)` windows overlap on the same date. It labels each one "same time" or "overlap" and says whether it involves one pet or two. Back-to-back tasks don't conflict. Returns a list of warning strings and never raises. |
| Recurring tasks | `Task.next_occurrence()`, `Scheduler.mark_task_complete()` | Completing a daily or weekly task marks it done and adds a copy dated `due_date + timedelta(days=1)` or `timedelta(weeks=1)` to the same pet. One-off tasks return `None`, and completing a task twice does nothing. |
| Next available slot | `Scheduler.find_next_available_slot(duration, on=, day_start=, day_end=)` | Walks the day's pending tasks in time order and returns the first gap that is long enough, or `None`. |
| Time-budget plan | `Scheduler.plan_day(available_minutes, on=)` | Greedy: goes through tasks in priority order and keeps each one that still fits the remaining minutes. Returns a `DailyPlan` with a reason for every kept or skipped task. |
| Persistence | `Owner.save_to_json()`, `Owner.load_from_json()` | Converts each class to a dict and back (`to_dict` / `from_dict`). Dates use ISO format, and priorities are stored by name. |

## 🖥️ Sample Output

Output of `python main.py`. The demo adds tasks out of order on purpose, and it includes one exact-time collision and one overlapping collision:

```
🐾 PawPal+ — Today's Schedule for Jordan (Wednesday Oct 14)

Raw task list (grouped by pet, unsorted):
╭────────┬───────┬────────────────────┬──────────┬────────────┬───────────┬──────────╮
│ Time   │ Pet   │ Task               │ Length   │ Priority   │ Repeats   │ Status   │
├────────┼───────┼────────────────────┼──────────┼────────────┼───────────┼──────────┤
│ 18:30  │ Mochi │ 🦮 Evening walk    │ 30 min   │ 🟡 medium  │ daily     │ ⏳ todo  │
│ 08:00  │ Mochi │ 🦮 Morning walk    │ 30 min   │ 🔴 high    │ daily     │ ⏳ todo  │
│ 12:00  │ Mochi │ 🎾 Puzzle toy play │ 20 min   │ 🟢 low     │ once      │ ⏳ todo  │
│ 12:00  │ Luna  │ 💊 Flea medication │ 5 min    │ 🔴 high    │ weekly    │ ⏳ todo  │
│ 07:30  │ Luna  │ 🍖 Breakfast       │ 10 min   │ 🔴 high    │ daily     │ ⏳ todo  │
│ 08:15  │ Luna  │ 🛁 Brush coat      │ 15 min   │ 🟢 low     │ weekly    │ ⏳ todo  │
╰────────┴───────┴────────────────────┴──────────┴────────────┴───────────┴──────────╯

📅 Sorted by time — Scheduler.sort_by_time():
╭────────┬───────┬────────────────────┬──────────┬────────────┬───────────┬──────────╮
│ Time   │ Pet   │ Task               │ Length   │ Priority   │ Repeats   │ Status   │
├────────┼───────┼────────────────────┼──────────┼────────────┼───────────┼──────────┤
│ 07:30  │ Luna  │ 🍖 Breakfast       │ 10 min   │ 🔴 high    │ daily     │ ⏳ todo  │
│ 08:00  │ Mochi │ 🦮 Morning walk    │ 30 min   │ 🔴 high    │ daily     │ ⏳ todo  │
│ 08:15  │ Luna  │ 🛁 Brush coat      │ 15 min   │ 🟢 low     │ weekly    │ ⏳ todo  │
│ 12:00  │ Mochi │ 🎾 Puzzle toy play │ 20 min   │ 🟢 low     │ once      │ ⏳ todo  │
│ 12:00  │ Luna  │ 💊 Flea medication │ 5 min    │ 🔴 high    │ weekly    │ ⏳ todo  │
│ 18:30  │ Mochi │ 🦮 Evening walk    │ 30 min   │ 🟡 medium  │ daily     │ ⏳ todo  │
╰────────┴───────┴────────────────────┴──────────┴────────────┴───────────┴──────────╯

⭐ Sorted by priority, then time — Scheduler.sort_by_priority():
╭────────┬───────┬────────────────────┬──────────┬────────────┬───────────┬──────────╮
│ Time   │ Pet   │ Task               │ Length   │ Priority   │ Repeats   │ Status   │
├────────┼───────┼────────────────────┼──────────┼────────────┼───────────┼──────────┤
│ 07:30  │ Luna  │ 🍖 Breakfast       │ 10 min   │ 🔴 high    │ daily     │ ⏳ todo  │
│ 08:00  │ Mochi │ 🦮 Morning walk    │ 30 min   │ 🔴 high    │ daily     │ ⏳ todo  │
│ 12:00  │ Luna  │ 💊 Flea medication │ 5 min    │ 🔴 high    │ weekly    │ ⏳ todo  │
│ 18:30  │ Mochi │ 🦮 Evening walk    │ 30 min   │ 🟡 medium  │ daily     │ ⏳ todo  │
│ 08:15  │ Luna  │ 🛁 Brush coat      │ 15 min   │ 🟢 low     │ weekly    │ ⏳ todo  │
│ 12:00  │ Mochi │ 🎾 Puzzle toy play │ 20 min   │ 🟢 low     │ once      │ ⏳ todo  │
╰────────┴───────┴────────────────────┴──────────┴────────────┴───────────┴──────────╯

🐶 Only Mochi's tasks — Scheduler.filter_tasks(pet_name='Mochi'):
╭────────┬───────┬────────────────────┬──────────┬────────────┬───────────┬──────────╮
│ Time   │ Pet   │ Task               │ Length   │ Priority   │ Repeats   │ Status   │
├────────┼───────┼────────────────────┼──────────┼────────────┼───────────┼──────────┤
│ 08:00  │ Mochi │ 🦮 Morning walk    │ 30 min   │ 🔴 high    │ daily     │ ⏳ todo  │
│ 12:00  │ Mochi │ 🎾 Puzzle toy play │ 20 min   │ 🟢 low     │ once      │ ⏳ todo  │
│ 18:30  │ Mochi │ 🦮 Evening walk    │ 30 min   │ 🟡 medium  │ daily     │ ⏳ todo  │
╰────────┴───────┴────────────────────┴──────────┴────────────┴───────────┴──────────╯

🚨 Conflict check — Scheduler.detect_conflicts():
  ⚠️  Conflict (overlap) on 2026-10-14: 08:00 Morning walk (30 min) vs 08:15 Brush coat (15 min), Mochi and Luna
  ⚠️  Conflict (same time) on 2026-10-14: 12:00 Puzzle toy play (20 min) vs 12:00 Flea medication (5 min), Mochi and Luna

🔁 Completing recurring tasks — Scheduler.mark_task_complete():
  ✅ Mochi's Morning walk done → next one created for 2026-10-15 at 08:00
  ✅ Luna's Flea medication done → next one created for 2026-10-21 at 12:00

✅ Completed — filter_tasks(completed=True):
╭────────┬───────┬────────────────────┬──────────┬────────────┬───────────┬──────────╮
│ Time   │ Pet   │ Task               │ Length   │ Priority   │ Repeats   │ Status   │
├────────┼───────┼────────────────────┼──────────┼────────────┼───────────┼──────────┤
│ 08:00  │ Mochi │ 🦮 Morning walk    │ 30 min   │ 🔴 high    │ daily     │ ✅ done  │
│ 12:00  │ Luna  │ 💊 Flea medication │ 5 min    │ 🔴 high    │ weekly    │ ✅ done  │
╰────────┴───────┴────────────────────┴──────────┴────────────┴───────────┴──────────╯

⏳ Still to do today — filter_tasks(completed=False, on=today):
╭────────┬───────┬────────────────────┬──────────┬────────────┬───────────┬──────────╮
│ Time   │ Pet   │ Task               │ Length   │ Priority   │ Repeats   │ Status   │
├────────┼───────┼────────────────────┼──────────┼────────────┼───────────┼──────────┤
│ 07:30  │ Luna  │ 🍖 Breakfast       │ 10 min   │ 🔴 high    │ daily     │ ⏳ todo  │
│ 08:15  │ Luna  │ 🛁 Brush coat      │ 15 min   │ 🟢 low     │ weekly    │ ⏳ todo  │
│ 12:00  │ Mochi │ 🎾 Puzzle toy play │ 20 min   │ 🟢 low     │ once      │ ⏳ todo  │
│ 18:30  │ Mochi │ 🦮 Evening walk    │ 30 min   │ 🟡 medium  │ daily     │ ⏳ todo  │
╰────────┴───────┴────────────────────┴──────────┴────────────┴───────────┴──────────╯

🕒 Next free 45-minute slot today — find_next_available_slot(45): 08:30

🧠 Plan for a busy day with 60 free minutes — plan_day(60): 55/60 min used
  07:30  🍖 Luna: Breakfast — high priority; fits (50 min left after)
  08:15  🛁 Luna: Brush coat — low priority; fits (5 min left after)
  18:30  🦮 Mochi: Evening walk — medium priority; fits (20 min left after)
  ✖  🎾 Mochi: Puzzle toy play — skipped: low priority, needs 20 min but only 5 min left

💾 Saved and reloaded via JSON: 2 pets, 8 tasks round-tripped.
```

## 🧪 Testing PawPal+

Run the suite:

```bash
python -m pytest
```

The 39 tests in `tests/test_pawpal.py` cover:

- **Basics:** `mark_complete()` changes the status, adding a task increases the pet's task count and tags it with the pet's name, `get_all_tasks()` covers every pet, and invalid times and duplicate pet names are rejected.
- **Sorting:** chronological order, unpadded times like `"9:00"`, date before time, priority then time, and an empty schedule.
- **Filtering:** by pet (case-insensitive), by status, combined filters, and a pet with no tasks.
- **Recurrence:** a daily task produces one for the next day, a weekly task produces one 7 days later, Oct 31 rolls over to Nov 1, one-off tasks don't repeat, the copy is independent of the original, and completing twice creates no duplicates.
- **Conflicts:** duplicate times, overlapping durations for the same pet, back-to-back tasks (no conflict), the same time on different days (no conflict), completed tasks are ignored, and a three-way conflict reports all 3 pairs.
- **Next slot, time-budget plan, and JSON round-trip.**

```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Dan\download\codepath\ai110-module2show-pawpal-starter
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 39 items

tests\test_pawpal.py .......................................             [100%]

============================= 39 passed in 0.06s ==============================
```

**Confidence level: ⭐⭐⭐⭐☆ (4/5).** Every scheduling behavior has tests for the normal case and the edge cases, and the Streamlit flow was also driven end-to-end with Streamlit's `AppTest`. I'm not giving it 5 stars because a few things are untested or unsupported: tasks that cross midnight, time zones, and persistence when several browser sessions edit the same `data.json` at once.

## 📸 Demo Walkthrough

Start the app with `streamlit run app.py`.

**Main UI features**

- **Sidebar.** Rename the owner, pick which date to view, and reset all data. Changes auto-save to `data.json`.
- **Add a pet.** Enter a name, species, and age. Duplicate names are rejected with an error message.
- **Schedule a task.** Choose the pet, task name, time, duration, priority, repeat setting (`once`/`daily`/`weekly`), and date. A caption above the form shows the **next free slot** for the chosen duration, and that slot is pre-filled as the default time.
- **Schedule view.** A table of the day's tasks with an emoji for each task type, priority badges, and status. You can filter by pet and status, and sort by *Time* or *Priority, then time*.
- **Conflict banner.** A yellow `st.warning` lists each pair of clashing tasks and suggests moving one of them. When there are no clashes, a green `st.success` appears instead.
- **Mark complete.** Pick a pending task and click ✅. Repeating tasks immediately create their next occurrence, and a notification shows the new date.
- **Build today's plan.** Choose how many minutes you have and click *Generate plan*. You get the tasks that fit, in time order, each with a reason, and a list of the tasks that didn't fit.

**Example workflow**

1. Add **Mochi** (dog, 3) and **Luna** (cat, 5) using *Add a pet*.
2. Schedule *Morning walk* for Mochi at 08:00, 30 min, high priority, daily.
3. Schedule *Breakfast* for Luna at 08:00, high priority, daily. The schedule now shows a **"Conflict (same time)"** warning for Morning walk vs Breakfast, Mochi and Luna.
4. Schedule *Brush coat* for Luna. The time field is pre-filled with the next free slot after the existing tasks.
5. Switch *Sort by* to **Priority, then time**. Both high-priority tasks move above the low-priority *Brush coat*.
6. Filter **Pet → Luna** to see only Luna's tasks, or **Status → Done** to see completed ones.
7. Mark *Morning walk* complete. Its status changes to ✅ done, a notification says the next walk is scheduled for tomorrow at 08:00, and the conflict warning disappears because completed tasks no longer block time.
8. Set the slider to 30 minutes and click **Generate plan**. High-priority tasks are kept, and anything that no longer fits is listed under "Didn't fit today" with the reason.
9. Close the browser and restart the app. Your pets and tasks reload from `data.json`.

**Key Scheduler behaviors shown:** sorting by time and by priority (`sort_by_time`, `sort_by_priority`), filtering (`filter_tasks`), overlap and duplicate-time warnings (`detect_conflicts`), daily and weekly recurrence (`mark_task_complete`), next free slot (`find_next_available_slot`), and the explained time-budget plan (`plan_day`).

The CLI output of the same behaviors is shown in [Sample Output](#️-sample-output) above.

## 💾 Data persistence workflow

- **Files modified:** `pawpal_system.py` (added `to_dict`/`from_dict` on `Task`, `Pet`, and `Owner`, plus `Owner.save_to_json` and `Owner.load_from_json`), `app.py` (load on first run, save after every change), and `.gitignore` (ignores `data.json`).
- **On startup,** `app.py` calls `Owner.load_from_json("data.json")` and stores the result in `st.session_state`. If there is no file, it starts with a new `Owner`.
- **After every change** (add a pet or task, complete a task, rename the owner), the app calls `owner.save_to_json("data.json")`.
- **Serialization** uses a custom dictionary conversion instead of a library such as marshmallow, because there are only three simple classes. Dates are stored as ISO strings and priorities as names (`"high"`). Each task's `pet_name` is rebuilt from its parent pet on load instead of being stored twice.

## 🎨 Output formatting

- **CLI:** [`tabulate`](https://pypi.org/project/tabulate/) with `tablefmt="rounded_outline"`, plus `wcwidth` so tables containing emoji stay aligned. `main.py`'s `show()` function adds 🔴/🟡/🟢 priority badges and ✅/⏳ status indicators. `sys.stdout.reconfigure(encoding="utf-8")` keeps the emoji from breaking on Windows terminals.
- **Task-type emoji:** the `Task.emoji` property picks 🦮 🍖 💊 🛁 🎾 🧹 (or 🐾 by default) from keywords in the description. Both the CLI and the UI use it.
- **UI:** `st.table` for the schedule, `st.warning` for conflicts, `st.success` and `st.error` for form results, and `st.toast` for completions.
