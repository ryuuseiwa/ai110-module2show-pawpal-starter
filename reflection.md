# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I wanted PawPal+ to be a simple pet care system that helps owners organize their pets' daily routines without keeping track of everything in their heads.

The three main actions I wanted users to be able to do were:

1. **Add a pet** with basic information like its name, species, and age.
2. **Schedule care tasks** such as feeding, walking, grooming, or giving medication.
3. **View a daily schedule** that organizes all tasks and points out any scheduling conflicts.

My initial UML (`diagrams/uml_draft.mmd`) used four classes:

- **Owner:** manages the pets and gives access to all of their tasks through `get_all_tasks()`.
- **Pet:** stores information about each pet and the tasks assigned to it.
- **Task:** one care activity, with its description, time, duration, frequency, and completion status.
- **Scheduler:** organizes tasks. It sorts, filters, and finds conflicts.

The relationships are: an Owner *has* many Pets, a Pet *owns* many Tasks, and the Scheduler *reads from* the Owner. I wanted each class to have one clear job instead of putting everything into one class. I also wanted the Scheduler to hold most of the scheduling logic, so I could add features later without changing the whole system.

**b. Design changes**

Yes. I made several changes after reviewing my skeleton with Claude Code:

1. **Tasks didn't know which pet they belonged to.** The Scheduler collects tasks from several pets into one list, so I added a `pet_name` attribute that `Pet.add_task()` fills in automatically.
2. **Recurring tasks had no date.** I had a frequency like "daily" or "weekly", but no specific date to calculate the next one from. I added `due_date` and `next_occurrence()`.
3. **Priority was a plain string,** which would sort alphabetically ("high" < "low" < "medium"). I changed it to a `Priority` `IntEnum` (LOW=1, MEDIUM=2, HIGH=3), so sorting compares numbers instead.
4. **Completing a recurring task belongs in the Scheduler.** Creating the next occurrence means adding a new task to the *pet*, which a lone Task can't do. I put this in `Scheduler.mark_task_complete()` instead of spreading completion methods across several classes.

These changes showed me why planning the structure before coding matters. Things that seem minor at the start can turn into problems once different features have to work together.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers **time** (start time and duration), **priority**, **frequency and due date**, **completion status**, and **how much time the owner has available**.

I treated **time as the most important constraint**, followed by priority. For example, if someone has two pets and walks one at 8:00 for 30 minutes, then gives the other medication at 8:15, those tasks overlap even though they start at different times. I wanted the system to catch situations like that, not just sort tasks and assume everything works out.

Priority matters because pet care tasks aren't all equally urgent. Medication or feeding should come before playing with a toy. That's why I added priority-based sorting and a daily plan (`plan_day()`) that picks tasks based on the time the owner actually has. I also added recurring tasks, because feeding and walking happen every day. Instead of making the user re-enter them, the system creates the next occurrence automatically when one is completed.

**b. Tradeoffs**

The biggest tradeoff was how complicated the scheduler should be.

**The daily plan uses a greedy algorithm.** It picks higher-priority tasks first and checks whether each one fits in the remaining time. With 40 minutes available, it might take a 30-minute high-priority task instead of two 20-minute medium-priority tasks, so it doesn't always use every minute. I think that's right for pet care, because getting the important tasks done matters more than fitting in as many tasks as possible. A more advanced algorithm could find a better combination, but that complexity wasn't needed for this project, and a greedy rule is easy to explain to the user ("kept because it's high priority and fits").

**Conflicts are warnings, not automatic fixes.** The system checks for overlapping durations, not only exact time matches, but it lets the owner decide what to do. The system doesn't know everyone's situation. Two tasks might overlap, but another family member could handle one of them. To make conflicts easier to fix, the app suggests the next available time slot.

Overall, I tried to balance being useful with keeping things simple.

---

## 3. AI Collaboration

**a. How you used AI**

I mainly used Claude Code in VS Code. I started by giving it the project requirements and asking it to help plan the architecture. It generated the first UML diagram and the class skeletons. After that, I used agent mode to implement the classes, the scheduling methods, the CLI demo, the tests, and the Streamlit connection.

The most useful thing about agent mode was that it could work across several files at once. For example, recurring tasks needed changes to `Task`, `Scheduler`, the demo, and the tests together.

I also used AI to brainstorm edge cases. Instead of just asking it to "write tests", I asked what kinds of situations could cause problems for a pet scheduler. That surfaced overlapping tasks, invalid times, dates changing at the end of a month, and a recurring task accidentally being completed twice. Specific questions worked much better than vague ones. Asking *how the Scheduler should get tasks from multiple pets* gave a much more useful answer than asking it to "improve the code."

**b. Judgment and verification**

I didn't accept every AI suggestion.

- **Rejected:** adding completion methods to both `Pet` and `Owner`. That could work, but the Scheduler was already responsible for managing tasks, and spreading one operation across several classes would make the system harder to follow. I kept it in `Scheduler.mark_task_complete()`.
- **Rejected:** requiring a task's `pet_name` to already match the pet before it could be added. My design has `Pet.add_task()` *assign* the pet's name, so that check would block every newly created task.
- **Accepted:** the model comparison found two real issues. Completing the same recurring task twice could create duplicate future tasks. And removing a task could remove the wrong one if two tasks had identical information, because Python dataclasses compare by value. I added a double-completion guard, changed task removal to use object identity, and made sure both cases have tests.

This was an important lesson: AI can suggest solutions that look correct but don't fit the structure of the existing project. I still need to understand what the code does and decide whether a suggestion actually makes the system better.

---

## 4. Testing and Verification

**a. What you tested**

PawPal+ has 39 automated tests that cover:

- **Core functionality:** adding pets, assigning tasks, completing tasks, getting tasks from multiple pets, and rejecting invalid times and duplicate pet names.
- **Sorting:** chronological order, and higher-priority tasks first when sorting by priority.
- **Filtering:** by pet, date, and completion status.
- **Recurring tasks:** creating the next daily or weekly occurrence, crossing into a new month, and not creating duplicates.
- **Conflict detection:** overlapping tasks, including tasks with different start times whose durations overlap.
- **Extra features:** finding available time slots, building daily plans, and saving and loading with JSON.

Testing recurring tasks was especially important, because a small mistake could create duplicate tasks or put them on the wrong dates. I also wanted to make sure that two back-to-back tasks are *not* flagged as a conflict.

The recorded test run showed **all 39 tests passing**. The Streamlit app was also tested with Streamlit's `AppTest` to check that adding pets, creating tasks, and marking tasks complete actually go through the backend.

**b. Confidence**

**4/5 stars.** The main features are tested, including several edge cases, so I'm fairly confident. I wouldn't give it 5 because some situations still need testing:

- tasks that continue past midnight
- recurring tasks completed several days late
- a saved JSON file that gets corrupted
- a much larger number of pets and tasks, to check performance

It's reliable for its current scope, but there's still room to improve before it could be a fully developed app.

---

## 5. Reflection

**a. What went well**

The most successful part was how the components worked together. Keeping Owner, Pet, Task, and Scheduler separate made it easy to add features without rewriting everything. I'm also happy with the scheduling features, especially conflict detection, recurring tasks, and finding open time slots. PawPal+ ended up being more than a basic to-do list. It helps owners make decisions based on priorities and the time they have.

Building the backend before connecting Streamlit also went well. Because the core logic was already tested, it was easy to tell whether a problem came from the scheduling logic or from the UI.

**b. What you would improve**

- **Edit and delete tasks in the UI.** Right now users can add and complete tasks, but can't change them afterwards.
- **Better handling of overdue tasks.** If someone forgets a recurring task for several days, the system should handle that more intelligently.
- **A unique ID for each task,** so tasks can be tracked and updated more reliably.
- **A smarter daily plan** that considers fixed appointment times as well as priority. Medication can't just be moved because it doesn't fit.

**c. Key takeaway**

My biggest takeaway is that **AI can help write code, but understanding how everything works together is still my responsibility.** Before this project, I mostly thought about whether individual pieces of code worked. Now I understand that designing a system also means deciding how the parts communicate, what each class is responsible for, and how to handle unexpected situations. Using AI well isn't just about writing prompts. It's about asking the right questions, reviewing the results, testing the code, and deciding what should or shouldn't go in.

---

## 6. AI Strategy

**Which AI coding assistant features were most effective?**
Agent mode was the most effective because it could change several files while keeping the project structure consistent. That helped most with recurring tasks and data persistence, which touched several parts of the system. Running the tests and the demo during development, instead of waiting until the end, helped too. The most valuable thing overall was asking the AI to review my design and find problems before they became harder to fix.

**One AI suggestion I rejected or modified:**
I rejected adding separate task-completion methods to `Pet` and `Owner`, and kept completion in the Scheduler, which already manages tasks. It's simpler and makes it clear which part of the system handles scheduling. I also rejected requiring a matching `pet_name` before adding a task, because my design assigns it automatically.

**How did separate chat sessions help?**
For the model comparison, I gave the same prompt to two models in separate, fresh contexts without my project files. That made the comparison fair: I could see which suggestions both models agreed on (the double-completion guard) and where they differed. It also kept me from relying too much on one response. Working in separate phases, each with its own commit, helped in a similar way, because each phase had a single goal that I could check the AI's work against.

**What did being the lead architect mean to me?**
It meant taking responsibility for the overall design instead of letting AI make every decision. AI generated much of the code, but I still had to decide which features were necessary, how the classes should interact, and whether the suggested solutions made sense. I also had to weigh simplicity against functionality. For example, I chose a greedy planner and warning-based conflict detection because they're easy to understand and fit the scope of the project. Being the lead architect doesn't mean writing every line myself. It means understanding the system, making the design decisions, and making sure the result actually meets the requirements.
