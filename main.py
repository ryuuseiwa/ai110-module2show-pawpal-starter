"""CLI demo for PawPal+: exercises every Scheduler feature and prints the results."""

import sys
from datetime import date
from pathlib import Path

from tabulate import tabulate

from pawpal_system import Owner, Pet, Scheduler, Task

STATUS = {True: "✅ done", False: "⏳ todo"}
PRIORITY_BADGE = {3: "🔴 high", 2: "🟡 medium", 1: "🟢 low"}


def show(title: str, tasks: list[Task]) -> None:
    """Print a titled table of tasks."""
    print(f"\n{title}")
    if not tasks:
        print("  (no tasks)")
        return
    rows = [
        [
            t.time,
            t.pet_name,
            f"{t.emoji} {t.description}",
            f"{t.duration_minutes} min",
            PRIORITY_BADGE[t.priority],
            t.frequency,
            STATUS[t.completed],
        ]
        for t in tasks
    ]
    print(tabulate(rows, headers=["Time", "Pet", "Task", "Length", "Priority", "Repeats", "Status"],
                   tablefmt="rounded_outline"))


def build_household() -> Owner:
    """Create a demo owner with two pets and tasks added deliberately out of order."""
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog", age=3)
    luna = Pet("Luna", "cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    mochi.add_task(Task("Evening walk", "18:30", 30, "medium", "daily"))
    mochi.add_task(Task("Morning walk", "08:00", 30, "high", "daily"))
    luna.add_task(Task("Flea medication", "12:00", 5, "high", "weekly"))
    luna.add_task(Task("Breakfast", "07:30", 10, "high", "daily"))
    mochi.add_task(Task("Puzzle toy play", "12:00", 20, "low"))      # same time as Luna's meds
    luna.add_task(Task("Brush coat", "08:15", 15, "low", "weekly"))   # overlaps Mochi's walk
    return owner


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    owner = build_household()
    scheduler = Scheduler(owner)
    today = date.today()

    print(f"🐾 PawPal+ — Today's Schedule for {owner.name} ({today:%A %b %d})")

    show("Raw task list (grouped by pet, unsorted):", owner.get_all_tasks())
    show("📅 Sorted by time — Scheduler.sort_by_time():", scheduler.sort_by_time())
    show("⭐ Sorted by priority, then time — Scheduler.sort_by_priority():", scheduler.sort_by_priority())
    show("🐶 Only Mochi's tasks — Scheduler.filter_tasks(pet_name='Mochi'):",
         scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi")))

    print("\n🚨 Conflict check — Scheduler.detect_conflicts():")
    for warning in scheduler.detect_conflicts(on=today) or ["No conflicts."]:
        print(f"  ⚠️  {warning}")

    print("\n🔁 Completing recurring tasks — Scheduler.mark_task_complete():")
    for task in scheduler.filter_tasks(on=today):
        if task.description in ("Morning walk", "Flea medication"):
            nxt = scheduler.mark_task_complete(task)
            print(f"  ✅ {task.pet_name}'s {task.description} done → next one created for {nxt.due_date} at {nxt.time}")

    show("✅ Completed — filter_tasks(completed=True):", scheduler.filter_tasks(completed=True))
    show("⏳ Still to do today — filter_tasks(completed=False, on=today):",
         scheduler.sort_by_time(scheduler.filter_tasks(completed=False, on=today)))

    slot = scheduler.find_next_available_slot(45, on=today)
    print(f"\n🕒 Next free 45-minute slot today — find_next_available_slot(45): {slot}")

    plan = scheduler.plan_day(available_minutes=60, on=today)
    print(f"\n🧠 Plan for a busy day with 60 free minutes — plan_day(60): "
          f"{plan.minutes_used}/{plan.minutes_available} min used")
    for t in plan.scheduled:
        print(f"  {t.time}  {t.emoji} {t.pet_name}: {t.description} — {plan.reason_for(t)}")
    for t in plan.skipped:
        print(f"  ✖  {t.emoji} {t.pet_name}: {t.description} — {plan.reason_for(t)}")

    path = Path("demo_data.json")
    owner.save_to_json(path)
    reloaded = Owner.load_from_json(path)
    path.unlink()
    print(f"\n💾 Saved and reloaded via JSON: {len(reloaded.pets)} pets, "
          f"{len(reloaded.get_all_tasks())} tasks round-tripped.")


if __name__ == "__main__":
    main()
