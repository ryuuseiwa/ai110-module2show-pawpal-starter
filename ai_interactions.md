# AI Interactions Log

---

## Agent Workflow (SF7)

**What task did you give the agent?**

I used Claude Code in agent mode in VS Code to build PawPal+ from the project requirements. I wanted it to work in phases instead of doing everything at once:

1. UML diagram and class skeletons
2. The main classes
3. A CLI demo
4. The scheduling algorithms
5. Automated tests
6. Connecting the backend to Streamlit

I also wanted to complete every optional challenge: an extra scheduling algorithm, JSON persistence, priority-based scheduling, better output formatting, and a comparison between AI models. I asked it to commit after each phase so I could track how the project developed.

**What did the agent do?**

| Step | Files modified | What it did |
|------|----------------|-------------|
| 1. System design | `diagrams/uml_draft.mmd`, `pawpal_system.py` | Generated the first Mermaid UML and the class skeletons, then reviewed them for missing pieces. This led to adding `pet_name`, `due_date`, and the `Priority` enum. |
| 2. Core implementation | `pawpal_system.py`, `main.py`, `tests/test_pawpal.py` | Implemented the classes and wrote `main.py`, which demonstrates two pets (Mochi and Luna) with different care tasks. Added the first tests (completing a task, adding a task to a pet). |
| 3. Scheduling algorithms | `pawpal_system.py`, `main.py`, `requirements.txt` | Added sorting by time and by priority, filtering by pet and status, automatic recurring tasks, conflict detection, next available time slot, a daily plan based on available time, and JSON save/load. Improved the CLI output with tables, emoji, and priority indicators. |
| 4. Testing | `tests/test_pawpal.py`, `pawpal_system.py` | Expanded the suite to 39 tests (overlapping tasks, invalid times, completing a task twice, month changes). Fixed the duplicate-recurrence and identical-task removal issues found in the model comparison. The recorded run showed all 39 passing. |
| 5. Streamlit integration | `app.py`, `.gitignore` | Connected the UI to the backend: add pets, schedule tasks, view and filter the schedule, see conflict warnings, mark tasks complete, and build a daily plan. Data auto-saves to `data.json`. Checked the UI with Streamlit's `AppTest`. |
| 6. Documentation | `diagrams/uml_final.mmd`, `README.md`, `reflection.md`, `ai_interactions.md` | Updated the UML to match the code, and wrote the README with run instructions, features, real CLI output, and test results. |

**What did you have to verify or fix manually?**

Even though the agent did most of the implementation, several things were caught and corrected during review:

- **UML diagram.** I checked that the class relationships made sense and matched the code. The `Priority` enum was originally written as `LOW = 1`, which Mermaid may not render, so it was changed to plain `LOW`/`MEDIUM`/`HIGH`.
- **CLI output.** One table was labeled as showing tasks "in the order they were added", but the tasks were actually grouped by pet. The label was corrected so it isn't misleading.
- **Recurring tasks.** Both comparison models suggested putting completion methods on `Pet` and `Owner`. I decided to keep that logic in the Scheduler so scheduling stays in one place.
- **Documentation accuracy.** I checked the test results and feature descriptions against the code. An early draft of the reflection described things that didn't happen (for example, it said the tests were written test-first, and they weren't), so those parts were rewritten to match reality.

Even when an AI agent completes many tasks successfully, its output still needs to be reviewed for accuracy and consistency.

---

## Prompt Comparison (SF11)

**Task:** the logic for automatically rescheduling recurring tasks. I picked it because it involves several classes and has to mark a task complete *and* correctly create the next occurrence.

Both models ran as Claude Code subagents in separate, fresh contexts, with no project files attached. Each got exactly this prompt:

> *"I have a Python dataclass `Task(description, time 'HH:MM', duration_minutes, frequency 'once'|'daily'|'weekly', due_date: date, completed, pet_name)`. Pets hold a list of tasks; an Owner holds pets and has `get_pet(name)`. Write the logic so that when a weekly (or daily) task is marked complete, a new instance is automatically created for the next occurrence and added to the same pet. Show the code and briefly explain design decisions and edge cases."*

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | Claude Sonnet (Claude Code subagent) | Claude Haiku (Claude Code subagent) |
| **Prompt** | Same prompt as above | Same prompt as above |
| **Response summary** | Used `timedelta` and `dataclasses.replace()`. Split the logic across classes: `Task.next_occurrence()` calculates the next date, `Pet.complete_task()` marks the task done and adds the next one, and `Owner.complete_task()` is a wrapper that finds the right pet. Prevented a task from being completed twice. | Used the same `timedelta` and `replace()` approach, with more checks: object identity to find the right task, a check for an equivalent future task before adding one, an error on invalid frequencies, and an error if `pet_name` didn't match the pet. Suggested how to handle tasks completed late. |
| **What was useful** | A clear, easy-to-follow explanation. It pointed out that completing a task twice would create duplicate future tasks. It also warned that dataclasses treat separate objects with identical values as equal, which I hadn't thought about for removing tasks. | It considered more edge cases and actually used identity checks so the correct task gets modified. |
| **Problems noticed** | Spreads completion across too many classes (`Task`, `Pet`, `Owner`). It also still uses a value-based check (`task not in self.tasks`) despite explaining the problem with dataclass equality. | More complicated than needed. Requiring `pet_name` to match would break my design, where `Pet.add_task()` *assigns* the name. The duplicate-task scan is unnecessary once double completion is blocked, and I'd rather validate frequency when a task is created than when it's completed. |
| **Decision** | Kept its double-completion guard. | Kept identity-based task removal. Rejected the `pet_name` check and the extra validation. |

**Which approach did you use in your final implementation and why?**

I didn't use either solution exactly as written. Both models used `timedelta` and `dataclasses.replace()`, which my implementation already did, so that made me more confident my recurrence logic was reasonable. I kept the completion process in `Scheduler.mark_task_complete()` instead of moving it into `Pet` and `Owner`.

I did take two suggestions from the comparison, and both are covered by automated tests:

1. **Protection against double completion.** The Scheduler checks whether a task is already completed before creating another occurrence, so duplicate recurring tasks can't happen.
2. **Identity-based removal.** Removing a task now uses object identity instead of value comparison, so the intended task is removed even if another task has identical information.

Overall, I preferred **Sonnet's approach** because it was easier to follow and didn't add unnecessary complexity, while **Haiku did a better job of considering edge cases**. I combined the useful parts of both and kept PawPal+'s original structure.

**What I learned:** different models can solve the same problem in different ways, and a more detailed solution isn't always a better one. One model might write cleaner code while another finds more edge cases. Instead of picking the answer that looks more advanced, I need to ask whether it fits the existing system, whether it adds unnecessary complexity, and whether it actually solves the problem. **AI is most useful when I treat its responses as suggestions to evaluate, not instructions to follow automatically.**
