"""PawPal+ logic layer: Owner, Pet, Task, and Scheduler classes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from enum import IntEnum
from pathlib import Path

FREQUENCIES = ("once", "daily", "weekly")

# Keyword -> emoji used to label tasks in the CLI and UI (first match wins).
TASK_EMOJIS = (
    (("walk", "run", "hike"), "🦮"),
    (("feed", "breakfast", "dinner", "lunch", "meal", "food"), "🍖"),
    (("med", "pill", "flea", "vaccine", "vet"), "💊"),
    (("groom", "bath", "brush", "nail"), "🛁"),
    (("play", "toy", "enrich", "train"), "🎾"),
    (("litter", "clean"), "🧹"),
)


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


def _to_minutes(hhmm: str) -> int:
    """Convert "HH:MM" to minutes since midnight."""
    hours, minutes = _normalize_time(hhmm).split(":")
    return int(hours) * 60 + int(minutes)


def _to_hhmm(minutes: int) -> str:
    """Convert minutes since midnight to "HH:MM"."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


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
        return _to_minutes(self.time)

    @property
    def end_minutes(self) -> int:
        """Minutes since midnight when this task ends."""
        return self.start_minutes + self.duration_minutes

    @property
    def emoji(self) -> str:
        """Emoji for this task type, guessed from its description."""
        text = self.description.lower()
        for keywords, symbol in TASK_EMOJIS:
            if any(word in text for word in keywords):
                return symbol
        return "🐾"

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

    def to_dict(self) -> dict:
        """Serialize this task to JSON-safe primitives."""
        return {
            "description": self.description,
            "time": self.time,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.name.lower(),
            "frequency": self.frequency,
            "due_date": self.due_date.isoformat(),
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Rebuild a task from to_dict() output."""
        return cls(
            description=data["description"],
            time=data["time"],
            duration_minutes=data.get("duration_minutes", 15),
            priority=data.get("priority", "medium"),
            frequency=data.get("frequency", "once"),
            due_date=date.fromisoformat(data["due_date"]) if "due_date" in data else date.today(),
            completed=data.get("completed", False),
        )


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
        """Remove this exact task object (no-op if it isn't there).

        Matches by identity, because dataclass == would also match a
        different task with identical fields.
        """
        self.tasks = [t for t in self.tasks if t is not task]

    def get_tasks(self) -> list[Task]:
        """Return a copy of this pet's task list."""
        return list(self.tasks)

    def task_count(self) -> int:
        """Return how many tasks this pet has."""
        return len(self.tasks)

    def to_dict(self) -> dict:
        """Serialize this pet and its tasks to JSON-safe primitives."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "tasks": [task.to_dict() for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Rebuild a pet (and its tasks) from to_dict() output."""
        pet = cls(data["name"], data["species"], data.get("age", 0))
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet


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

    def to_dict(self) -> dict:
        """Serialize the owner and all pets/tasks to JSON-safe primitives."""
        return {"name": self.name, "pets": [pet.to_dict() for pet in self.pets]}

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Rebuild an owner from to_dict() output."""
        owner = cls(data["name"])
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def save_to_json(self, path: str | Path = "data.json") -> None:
        """Write this owner, their pets, and all tasks to a JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_from_json(cls, path: str | Path = "data.json") -> Owner | None:
        """Load an owner from a JSON file, or return None if the file doesn't exist."""
        path = Path(path)
        if not path.exists():
            return None
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


@dataclass
class DailyPlan:
    """Result of Scheduler.plan_day(): what fits in the time budget and why."""

    scheduled: list[Task]
    skipped: list[Task]
    reasons: dict[int, str]  # id(task) -> human-readable explanation
    minutes_used: int
    minutes_available: int

    def reason_for(self, task: Task) -> str:
        """Return the explanation recorded for a task."""
        return self.reasons.get(id(task), "")


class Scheduler:
    """The 'brain' that organizes tasks across all of an owner's pets."""

    def __init__(self, owner: Owner):
        """Create a scheduler that reads tasks from the given owner."""
        self.owner = owner

    def _tasks(self, tasks: list[Task] | None) -> list[Task]:
        """Use the given task list, or every task the owner has."""
        return self.owner.get_all_tasks() if tasks is None else tasks

    def todays_schedule(self, on: date | None = None) -> list[Task]:
        """Return tasks due on the given date (default today), ordered by time."""
        return self.sort_by_time(self.filter_tasks(on=on or date.today()))

    # ----- sorting ---------------------------------------------------------

    def sort_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks in chronological order (date, then "HH:MM" time).

        Times are stored zero-padded, so "HH:MM" strings sort correctly as
        plain text and the lambda key can use them directly.
        """
        return sorted(self._tasks(tasks), key=lambda t: (t.due_date, t.time))

    def sort_by_priority(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks ordered by priority (high first), then chronologically."""
        return sorted(self._tasks(tasks), key=lambda t: (-t.priority, t.due_date, t.time))

    # ----- filtering -------------------------------------------------------

    def filter_tasks(
        self,
        tasks: list[Task] | None = None,
        *,
        pet_name: str | None = None,
        completed: bool | None = None,
        on: date | None = None,
    ) -> list[Task]:
        """Return tasks matching every filter given; a None filter is ignored."""
        result = self._tasks(tasks)
        if pet_name is not None:
            result = [t for t in result if t.pet_name.lower() == pet_name.lower()]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        if on is not None:
            result = [t for t in result if t.due_date == on]
        return result

    # ----- recurring tasks -------------------------------------------------

    def mark_task_complete(self, task: Task) -> Task | None:
        """Complete a task; if it recurs, add its next occurrence to the pet and return it.

        Completing an already-completed task does nothing, so a double click
        can't spawn duplicate future tasks.
        """
        if task.completed:
            return None
        task.mark_complete()
        next_task = task.next_occurrence()
        if next_task is None:
            return None
        pet = self.owner.get_pet(task.pet_name)
        if pet is None:
            raise ValueError(f"task {task.description!r} is not attached to any of {self.owner.name}'s pets")
        pet.add_task(next_task)
        return next_task

    # ----- conflict detection ----------------------------------------------

    def detect_conflicts(self, on: date | None = None) -> list[str]:
        """Return a warning for every pair of pending tasks whose time windows overlap.

        Tasks are sorted by start, so each task is only compared with the
        ones after it, stopping at the first that starts after it ends.
        Never raises: an empty list means no conflicts.
        """
        pending = self.filter_tasks(completed=False, on=on)
        ordered = sorted(pending, key=lambda t: (t.due_date, t.start_minutes))
        warnings = []
        for i, first in enumerate(ordered):
            for second in ordered[i + 1:]:
                if second.due_date != first.due_date or second.start_minutes >= first.end_minutes:
                    break
                who = (
                    f"both for {first.pet_name}"
                    if first.pet_name == second.pet_name
                    else f"{first.pet_name} and {second.pet_name}"
                )
                kind = "same time" if first.time == second.time else "overlap"
                warnings.append(
                    f"Conflict ({kind}) on {first.due_date}: "
                    f"{first.time} {first.description} ({first.duration_minutes} min) vs "
                    f"{second.time} {second.description} ({second.duration_minutes} min), {who}"
                )
        return warnings

    # ----- next available slot ---------------------------------------------

    def find_next_available_slot(
        self,
        duration_minutes: int,
        on: date | None = None,
        day_start: str = "07:00",
        day_end: str = "22:00",
    ) -> str | None:
        """Return the earliest "HH:MM" on a date where a task of this length fits.

        Walks the day's pending tasks in time order and returns the first gap
        of at least duration_minutes, or None if nothing fits before day_end.
        """
        on = on or date.today()
        cursor, limit = _to_minutes(day_start), _to_minutes(day_end)
        busy = sorted(self.filter_tasks(completed=False, on=on), key=lambda t: t.start_minutes)
        for task in busy:
            if task.start_minutes - cursor >= duration_minutes:
                break
            cursor = max(cursor, task.end_minutes)
        if cursor + duration_minutes > limit:
            return None
        return _to_hhmm(cursor)

    # ----- time-budget planning --------------------------------------------

    def plan_day(self, available_minutes: int, on: date | None = None) -> DailyPlan:
        """Choose which pending tasks fit in the owner's available time, with reasons.

        Greedy: take tasks in priority order (high first, earlier time breaks
        ties) and keep each one that still fits in the remaining budget. The
        chosen tasks come back in time order.
        """
        on = on or date.today()
        remaining = available_minutes
        scheduled, skipped, reasons = [], [], {}
        for task in self.sort_by_priority(self.filter_tasks(completed=False, on=on)):
            label = task.priority.name.lower()
            if task.duration_minutes <= remaining:
                remaining -= task.duration_minutes
                scheduled.append(task)
                reasons[id(task)] = f"{label} priority; fits ({remaining} min left after)"
            else:
                skipped.append(task)
                reasons[id(task)] = (
                    f"skipped: {label} priority, needs {task.duration_minutes} min "
                    f"but only {remaining} min left"
                )
        return DailyPlan(
            scheduled=self.sort_by_time(scheduled),
            skipped=skipped,
            reasons=reasons,
            minutes_used=available_minutes - remaining,
            minutes_available=available_minutes,
        )
