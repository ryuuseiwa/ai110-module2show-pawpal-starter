"""PawPal+ logic layer: Owner, Pet, Task, and Scheduler classes."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from enum import IntEnum

FREQUENCIES = ("once", "daily", "weekly")


class Priority(IntEnum):
    """Task importance; higher value means more important."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def parse(cls, value: Priority | str | int) -> Priority:
        """Convert a Priority, name ("high"), or int (3) into a Priority."""
        if isinstance(value, Priority):
            return value
        if isinstance(value, str):
            return cls[value.strip().upper()]
        return cls(value)


@dataclass
class Task:
    """A single pet care activity scheduled at a time on a date."""

    description: str
    time: str  # "HH:MM", 24-hour
    duration_minutes: int = 15
    priority: Priority = Priority.MEDIUM
    frequency: str = "once"  # "once" | "daily" | "weekly"
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    pet_name: str = ""

    def __post_init__(self) -> None:
        """Normalize priority and validate time, duration, and frequency."""
        self.priority = Priority.parse(self.priority)
        self.frequency = self.frequency.lower()
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {FREQUENCIES}, got {self.frequency!r}")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        self.time = _normalize_time(self.time)

    @property
    def start_minutes(self) -> int:
        """Minutes since midnight when this task starts."""
        hours, minutes = self.time.split(":")
        return int(hours) * 60 + int(minutes)

    @property
    def end_minutes(self) -> int:
        """Minutes since midnight when this task ends."""
        return self.start_minutes + self.duration_minutes

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return a fresh copy of this task for its next due date, or None if it doesn't recur."""
        if self.frequency == "daily":
            step = timedelta(days=1)
        elif self.frequency == "weekly":
            step = timedelta(weeks=1)
        else:
            return None
        return replace(self, due_date=self.due_date + step, completed=False)


def _normalize_time(value: str) -> str:
    """Validate an "H:MM"/"HH:MM" string and return it zero-padded as "HH:MM"."""
    try:
        hours_str, minutes_str = value.strip().split(":")
        hours, minutes = int(hours_str), int(minutes_str)
    except (ValueError, AttributeError):
        raise ValueError(f"time must look like 'HH:MM', got {value!r}") from None
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError(f"time out of range: {value!r}")
    return f"{hours:02d}:{minutes:02d}"


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet and tag it with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet (no-op if it isn't there)."""
        if task in self.tasks:
            self.tasks.remove(task)

    def get_tasks(self) -> list[Task]:
        """Return a copy of this pet's task list."""
        return list(self.tasks)

    def task_count(self) -> int:
        """Return how many tasks this pet has."""
        return len(self.tasks)


class Owner:
    """A pet owner who manages one or more pets."""

    def __init__(self, name: str):
        """Create an owner with no pets."""
        self.name = name
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet; pet names must be unique per owner."""
        if self.get_pet(pet.name) is not None:
            raise ValueError(f"{self.name} already has a pet named {pet.name!r}")
        self.pets.append(pet)

    def get_pet(self, name: str) -> Pet | None:
        """Find a pet by name (case-insensitive)."""
        for pet in self.pets:
            if pet.name.lower() == name.lower():
                return pet
        return None

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:
    """The 'brain' that organizes tasks across all of an owner's pets."""

    def __init__(self, owner: Owner):
        """Create a scheduler that reads tasks from the given owner."""
        self.owner = owner

    def todays_schedule(self, on: date | None = None) -> list[Task]:
        """Return tasks due on the given date (default today), ordered by time."""
        on = on or date.today()
        due = [t for t in self.owner.get_all_tasks() if t.due_date == on]
        return sorted(due, key=lambda t: t.time)
