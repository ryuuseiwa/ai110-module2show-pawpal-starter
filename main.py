"""CLI demo for PawPal+: builds a household and prints today's schedule."""

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog", age=3)
    luna = Pet("Luna", "cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    mochi.add_task(Task("Morning walk", "08:00", 30, "high", "daily"))
    mochi.add_task(Task("Evening walk", "18:30", 30, "medium", "daily"))
    luna.add_task(Task("Breakfast", "07:30", 10, "high", "daily"))
    luna.add_task(Task("Flea medication", "12:00", 5, "high", "weekly"))

    scheduler = Scheduler(owner)
    print(f"Today's Schedule for {owner.name}")
    print("=" * 40)
    for task in scheduler.todays_schedule():
        print(f"{task.time}  {task.pet_name:<6} {task.description} ({task.duration_minutes} min)")


if __name__ == "__main__":
    main()
