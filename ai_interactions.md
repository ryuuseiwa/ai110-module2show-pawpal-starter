# AI Interactions Log

---

## Agent Workflow (SF7)

**What task did you give the agent?**

I gave Claude Code (agent mode, in VS Code) the full PawPal+ project spec and asked it to work through every phase in order. The phases were: UML draft → class skeleton → core implementation and CLI demo → algorithms (sorting, filtering, recurrence, conflicts) → test suite → Streamlit integration → final UML, README, and reflection. I also asked it to complete every optional challenge, including a third algorithm (next available slot plus a time-budget plan), JSON persistence, priority scheduling, formatted CLI output, and a comparison between models. I asked for a commit at the end of each phase so the history shows the progression.

**What did the agent do?**

| Step | Files modified | What it did |
|------|----------------|-------------|
| 1 | `diagrams/uml_draft.mmd`, `pawpal_system.py`, `reflection.md` | Drafted the four-class Mermaid UML and the dataclass skeleton with empty stubs. Wrote 1a/1b. Committed `chore: add class skeletons from UML`. |
| 2 | `pawpal_system.py`, `main.py`, `tests/test_pawpal.py`, `pytest.ini` | Implemented `Task`/`Pet`/`Owner`/`Scheduler` and added `Priority`, `due_date`, and `pet_name` (from the skeleton review). Wrote the demo and the first 2 tests, and ran both. |
| 3 | `pawpal_system.py`, `main.py`, `requirements.txt` | Added `sort_by_time`, `sort_by_priority`, `filter_tasks`, `mark_task_complete` (recurrence with `timedelta`), `detect_conflicts` (overlap-aware), `find_next_available_slot`, `plan_day`, and JSON save/load. Rewrote `main.py` with `tabulate` and emoji. Ran the demo and checked each result by hand (for example, that the next free 45-minute slot is 08:30). |
| 4 | `tests/test_pawpal.py`, `pawpal_system.py` | Wrote 37 more tests (39 in total). Added the double-completion guard and identity-based `remove_task` after the model comparison exposed those gaps. |
| 5 | `app.py`, `.gitignore` | Rewired the UI: `Owner` in `st.session_state`, forms that call `add_pet`/`add_task`, filters and sorting, an `st.warning` for conflicts, mark complete, the plan view, and auto-save to `data.json`. Verified headlessly with `streamlit.testing.v1.AppTest` in a scratch directory (adding pets and tasks, creating a conflict, completing a task, reloading). |
| 6 | `diagrams/uml_final.mmd`, `diagrams/uml.mmd`, `README.md`, `reflection.md`, `ai_interactions.md` | Updated the UML to match the code. Wrote the README with the real captured output of `main.py` and `pytest`, plus the reflection and this log. |

Commands it ran repeatedly: `python main.py`, `python -m pytest -v`, the `AppTest` script, and `git commit`.

**What did you have to verify or fix manually?**

- **Mermaid syntax.** The first final diagram used `LOW = 1` inside the enum block, which Mermaid may not parse as an enum value. I changed it to plain `LOW`/`MEDIUM`/`HIGH`.
- **A misleading label.** The demo's first table was titled "Tasks in the order they were added", but `get_all_tasks()` groups tasks by pet, so that wasn't true. I renamed it to "Raw task list (grouped by pet, unsorted)".
- **The reflection had to match reality.** The first draft said tests were written "failing-first" and that the AI had suggested an `itertools.combinations` refactor. Neither was accurate, so I rewrote those sentences to describe what actually happened.
- **Recurrence design.** I kept completion logic in `Scheduler.mark_task_complete()` rather than adopting the `Pet.complete_task`/`Owner.complete_task` wrappers that both comparison models proposed (see below).

---

## Prompt Comparison (SF11)

**Task:** the logic for rescheduling recurring (weekly/daily) tasks when they're marked complete. Each model got exactly the same prompt in a fresh context with no project files attached.

> *"I have a Python dataclass `Task(description, time 'HH:MM', duration_minutes, frequency 'once'|'daily'|'weekly', due_date: date, completed, pet_name)`. Pets hold a list of tasks; an Owner holds pets and has `get_pet(name)`. Write the logic so that when a weekly (or daily) task is marked complete, a new instance is automatically created for the next occurrence and added to the same pet. Show the code and briefly explain design decisions and edge cases."*

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | Claude Sonnet (Claude Code subagent) | Claude Haiku (Claude Code subagent) |
| **Prompt** | Same prompt as above | Same prompt as above |
| **Response summary** | A `FREQUENCY_DELTAS` dict of `timedelta`s. `Task.next_occurrence()` uses `dataclasses.replace`. `Pet.complete_task()` marks the task done and appends the next copy. `Owner.complete_task(pet_name, task)` is a thin wrapper. It is idempotent: an already-completed task returns `None`. | The same `timedelta` table and `replace()` approach. `Pet.complete_task()` checks membership by identity (`is`), skips completed tasks, and also scans for an "equivalent pending instance" before appending. `add_task()` raises an error if `task.pet_name` doesn't match the pet. Unknown frequencies raise `ValueError`. |
| **What was useful** | It flagged the **double-completion bug** (a second click would create a duplicate future task). It also warned that dataclass `==` makes `in` and `list.remove()` match equal-but-different tasks, and it explained anchoring to `due_date` versus completion date clearly (to avoid drifting). | It also caught double completion and **used an identity check** instead of only describing it. It gave a concrete suggestion for overdue tasks (loop until the date is on or after today) and was honest that its demo output was unverified. |
| **Problems noticed** | It spreads one operation across three classes (`Task`, `Pet`, `Owner`). Its `Pet.complete_task` still uses `task not in self.tasks`, even though its own explanation warns about that pitfall. | `add_task()` raising when `pet_name` doesn't match would break normal use, because a new `Task` starts with no pet name. It also adds more defensive code than needed: the duplicate scan is redundant once double completion is guarded, and frequency validation happens late, at completion instead of at creation. |
| **Decision** | Adopted its idempotency guard and its explanation of the identity pitfall. | Adopted the identity-based matching (applied to `Pet.remove_task`). Rejected the `add_task` check and the extra duplicate scan. |

**Which approach did you use in your final implementation and why?**

Neither answer was used as written. Both models agreed with my existing core (`timedelta` plus `dataclasses.replace` in `Task.next_occurrence()`), which confirmed that it was right. I kept the side effects in **`Scheduler.mark_task_complete()`**, because the assignment makes the Scheduler the single "brain" for task management, and a single entry point is clearer for the UI. From the comparison, I took the **double-completion guard** (`if task.completed: return None`), which both models raised, and **identity-based removal** in `Pet.remove_task`, where Haiku's approach was applied correctly and Sonnet's wasn't. Each change has a test (`test_completing_twice_does_not_duplicate_next_occurrence` and `test_remove_task_removes_only_that_object`). Overall, Sonnet's answer was cleaner and easier to read, Haiku's was more defensive than necessary, and both found the same real bug, which was the most valuable result of the comparison.
