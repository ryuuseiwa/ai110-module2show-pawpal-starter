"""PawPal+ logic layer: Owner, Pet, Task, and Scheduler classes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    description: str
    time: str  # "HH:MM"
    duration_minutes: int = 15
    priority: str = "medium"
    frequency: str = "once"  # "once" | "daily" | "weekly"
    completed: bool = False

    def mark_complete(self) -> None:
        pass


@dataclass
class Pet:
    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task: Task) -> None:
        pass

    def get_tasks(self) -> list[Task]:
        pass


class Owner:
    def __init__(self, name: str):
        self.name = name
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        pass

    def get_pet(self, name: str) -> Pet | None:
        pass

    def get_all_tasks(self) -> list[Task]:
        pass


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner

    def sort_by_time(self) -> list[Task]:
        pass

    def filter_tasks(self, pet_name: str | None = None, completed: bool | None = None) -> list[Task]:
        pass

    def detect_conflicts(self) -> list[str]:
        pass

    def todays_schedule(self) -> list[Task]:
        pass
