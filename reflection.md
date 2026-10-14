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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
