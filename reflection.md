# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

Three core actions a user should be able to perform:

1. **Add a pet** (name, species, age) to their household.
2. **Schedule a care task** for a pet — e.g. a walk at 08:00 for 30 minutes, daily, high priority.
3. **See today's schedule** — every task for every pet, in time order, with warnings when two tasks collide.

My initial UML (`diagrams/uml_draft.mmd`) had four classes:

- **Task** (dataclass) — one care activity: description, time (`"HH:MM"`), duration, priority, frequency, and completion status. Its only behavior was `mark_complete()`.
- **Pet** (dataclass) — pet details plus the list of tasks that belong to that pet; responsible for adding/removing its own tasks.
- **Owner** — holds multiple pets and exposes `get_all_tasks()`, the single place where every pet's tasks are gathered together.
- **Scheduler** — the "brain". It holds a reference to an `Owner` and reads tasks through `get_all_tasks()`, so it always works across all pets. It is responsible for sorting, filtering, conflict detection, and producing today's schedule.

Relationships: Owner *has* many Pets (aggregation), a Pet *owns* many Tasks (composition), and the Scheduler *reads from* the Owner.

**b. Design changes**

Yes. When I asked the AI to review the skeleton for missing relationships and bottlenecks, it flagged three problems, and I made these changes:

1. **Tasks didn't know which pet they belonged to.** `Owner.get_all_tasks()` returns a flat list, so once tasks were merged the Scheduler couldn't filter by pet or print "Mochi: walk". I added a `pet_name` field on `Task` that `Pet.add_task()` fills in automatically, instead of returning `(pet, task)` tuples everywhere.
2. **Recurring tasks had no date.** "Daily" is meaningless without knowing *which* day a task is for, so I added `due_date: date` and a `next_occurrence()` method that uses `timedelta` to build the next instance.
3. **Priority as a free string would sort alphabetically** ("high" < "low" < "medium"). I replaced it with a `Priority` `IntEnum` (LOW=1, MEDIUM=2, HIGH=3) so priority sorting is numeric and typos are rejected.

I also moved "mark complete and spawn the next occurrence" into `Scheduler.mark_task_complete()` rather than `Task.mark_complete()`, because creating a new task requires adding it to the *pet*, which a lone Task has no access to.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:

- **Time of day.** Every task has a `"HH:MM"` start time and a duration. This drives sorting, conflict detection, and finding the next free slot.
- **Date and recurrence.** Each task has a `due_date` and repeats once, daily, or weekly. Only tasks due on the selected day show up in that day's schedule.
- **Priority** (low/medium/high). It is used by `sort_by_priority()`, and it decides what survives in `plan_day()` when time is short.
- **The owner's available minutes.** `plan_day(available_minutes)` treats this as a hard budget.
- **Completion status.** Finished tasks no longer cause conflicts or use up time.

I decided that **time** was the most important constraint, followed by **priority**. A pet owner's day is organized by the clock, so the default view is chronological. Priority matters most when there isn't enough time. Skipping a play session is fine, but skipping medication or a meal isn't, so the time-budget planner chooses tasks by priority first and then shows the chosen ones in time order. I left out softer "preferences" (such as "Mochi prefers walks in the morning") because they would make the model more complicated without changing the core behaviors this project is graded on.

**b. Tradeoffs**

**`plan_day()` is greedy, not optimal.** It goes through tasks in priority order and keeps each one that still fits the remaining minutes. It does not search for the combination that fills the time budget best (that would be the knapsack problem). As a result, it can leave minutes unused. With 40 minutes, a high-priority 30-minute walk is kept first, so two medium-priority 20-minute tasks that would together fill all 40 minutes won't both fit. This is reasonable here because the owner's real goal is to make sure the important tasks happen, not to fill every minute. A greedy rule is also easy to explain ("kept because it is high priority and fits"), and an optimal solver couldn't explain its choices that simply.

A second tradeoff concerns conflicts. **`detect_conflicts()` checks for overlapping durations, not only exact time matches, but it only warns and never moves tasks automatically.** An 08:00 30-minute walk and an 08:15 grooming session are flagged even though their times differ. However, the scheduler doesn't decide which task should move, because the owner knows things it doesn't (for example, that a partner can handle one of them). The UI shows the next free slot instead, so the fix takes one step.

When I evaluated how to simplify the conflict check, the more "Pythonic" alternative was `itertools.combinations(tasks, 2)` with a single overlap test. That version is shorter, but it compares every pair. I kept my version, which sorts the tasks and stops early once a later task starts after the current one ends. It is still easy to read with the comment above the loop, it skips pairs that can't overlap, and the early stop makes the "sorted by start time" idea explicit.

---

## 3. AI Collaboration

**a. How you used AI**

I used Claude Code in agent mode inside VS Code throughout the project:

- **Design.** It turned my three core actions into the four-class UML draft, and then reviewed the skeleton for missing relationships. That review is where the `pet_name`, `due_date`, and `Priority` enum changes in section 1b came from.
- **Implementation.** It edited several files at once (`pawpal_system.py`, `main.py`, `app.py`, and the tests), which mattered for recurrence, because that change touches `Task`, `Scheduler`, and the UI.
- **Testing.** It drafted the edge-case test plan (empty pet, duplicate times, back-to-back tasks, month rollover, completing a task twice) and ran `pytest` after every change.
- **Verification of the UI.** It drove the Streamlit app headlessly with `streamlit.testing.v1.AppTest`: adding pets, creating a conflict, marking a task complete, and reloading from `data.json`. This confirmed that the UI really calls the backend instead of only rendering.
- **Comparing models.** I gave the same recurrence prompt to two other models (see `ai_interactions.md`).

The most helpful prompts were specific and pointed at a file, for example: *"Based on my skeletons in `pawpal_system.py`, how should the Scheduler retrieve all tasks from the Owner's pets?"* and *"What are the most important edge cases to test for a pet scheduler with sorting and recurring tasks?"* Asking for edge cases was more useful than asking it to "write tests", because it produced cases I hadn't thought of.

**b. Judgment and verification**

- **Rejected:** One model's recurrence answer had `Pet.add_task()` *raise an error* if `task.pet_name` didn't already match the pet. I rejected this because in my design `add_task()` is what *sets* `pet_name`, so that check would make it impossible to add a new task at all. The same answer also raised an error for an unknown frequency inside `next_occurrence()`. I validate frequency once, in `Task.__post_init__`, so a bad value fails when the task is created instead of later when someone completes it.
- **Modified:** Both models suggested putting `complete_task()` on `Pet` and adding an `Owner.complete_task(pet_name, task)` wrapper. I kept the logic in `Scheduler.mark_task_complete()` instead, because the assignment treats the Scheduler as the one "brain" for managing tasks, and having the same operation in three places makes it unclear which one the UI should call.
- **Accepted, after checking:** Both models pointed out that completing the same task twice would create two future copies, and that `list.remove()` on a dataclass compares by value, so it could remove an identical twin instead of the intended task. I didn't take this on trust. I checked my own code, confirmed that both problems were real (nothing stopped a second completion, and `remove_task` used `in`/`remove`), then added a guard (`if task.completed: return None`) and identity-based removal, together with two tests (`test_completing_twice_does_not_duplicate_next_occurrence` and `test_remove_task_removes_only_that_object`). The whole suite passed (39/39).

In general, I checked AI output by running it rather than reading it: `python main.py` for visible behavior, `pytest` for regressions, and `AppTest` for the UI.

---

## 4. Testing and Verification

**a. What you tested**

There are 39 tests in `tests/test_pawpal.py`:

- **Core objects:** completing a task, adding a task (count and pet tag), gathering tasks from every pet, and rejecting invalid times and duplicate pet names.
- **Sorting:** chronological order, unpadded times like `"9:00"`, date before time, priority then time, and an empty list.
- **Filtering:** by pet, by status, combined filters, and a pet with no tasks.
- **Recurrence:** daily (+1 day), weekly (+7 days), rolling over from Oct 31 to Nov 1, one-off tasks not repeating, the copy being independent, and no duplicates when a task is completed twice.
- **Conflicts:** exact duplicates, overlaps for the same pet, back-to-back tasks (no conflict), the same time on different days (no conflict), completed tasks ignored, and a three-way conflict producing three pairs.
- **Next free slot, time-budget plan, and JSON save/load round-trip.**

These tests matter because the scheduler's value depends on edge cases that are easy to get wrong silently. Plain string sorting puts `"9:00"` after `"10:00"`, a naive conflict check flags back-to-back tasks, and a recurrence bug can quietly fill the schedule with duplicates. Each of these would look fine in a quick demo and still be wrong.

**b. Confidence**

**4/5.** Every behavior I implemented has tests for the normal case and the edge cases, and the UI flow was tested end-to-end. Next, I would test:

- tasks that cross midnight (23:30 for 60 minutes), which currently aren't compared with tasks early the next day
- completing a recurring task long after its due date (the next copy is anchored to `due_date`, so it could already be overdue)
- `data.json` being corrupted or edited by hand
- two browser tabs writing to `data.json` at the same time
- very large schedules, for performance

---

## 5. Reflection

**a. What went well**

I'm most satisfied with how the classes are separated. Because `Scheduler` reads everything through `Owner.get_all_tasks()`, every feature (sorting, filtering, conflicts, free slots, planning) worked across several pets automatically, and the Streamlit UI needed almost no logic of its own. It only calls methods and displays the results. Building CLI-first paid off: by the time I connected the UI, the backend already had 39 passing tests, and the UI worked on the first headless run.

**b. What you would improve**

- Give each task a unique `id` instead of relying on object identity, so that persistence, editing, and removal from the UI are more robust.
- Support editing and deleting tasks in the UI (right now you can only add and complete them).
- Handle tasks that cross midnight, and let late recurring tasks catch up to today's date.
- Replace the greedy `plan_day()` with something that also respects fixed times (for example, medication must happen at 12:00), instead of only respecting a total number of minutes.

**c. Key takeaway**

AI is very good at producing plausible code, but being the "lead architect" means deciding where responsibilities belong. When two models suggested putting task completion on `Pet` and `Owner`, both versions worked, but they would have spread one operation across three classes. The useful part of their answers was the *edge cases* (double completion and equality versus identity), not the structure. I learned to take the AI's ideas but keep the design decisions myself, and to trust a suggestion only after a test I wrote proves it.

---

## 6. AI Strategy

**Which AI coding assistant features were most effective?** Agent mode with editing across several files was the most effective, especially for recurrence and persistence, which each changed `pawpal_system.py`, `main.py`, `app.py`, and the tests together. Being able to run `pytest` and `main.py` from inside the agent loop mattered just as much, because every change was checked immediately instead of me assuming it worked.

**One AI suggestion I rejected or modified to keep the design clean:** the `Pet.complete_task()` and `Owner.complete_task()` wrappers, plus the `add_task()` check that `pet_name` already matched (details in 3b). I kept a single `Scheduler.mark_task_complete()` entry point.

**How did separate chat sessions help?** I kept the model-comparison prompts in their own fresh contexts with no project files attached. That made their answers a fair, independent comparison instead of an echo of my existing code, and it showed which ideas (the double-completion guard) appeared without being prompted. Keeping planning, implementation, and testing as separate phases with their own commits had the same benefit: each phase had one goal, so I could review the AI's work against that goal alone.

**Being the "lead architect":** AI tools can write any of the pieces quickly, so the human's job becomes defining the boundaries. That means deciding which class owns which responsibility, which tradeoffs are acceptable (greedy planning, warn-only conflicts), and what counts as "verified". I made the structural decisions and used AI to implement them, to find edge cases, and to challenge my design, but I didn't let it decide the structure.
