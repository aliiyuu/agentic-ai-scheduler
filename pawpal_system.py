from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str
    category: str
    preferred_window: str
    notes: str


@dataclass
class Pet:
    name: str
    species: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task_title: str) -> None:
        pass


class Owner:
    def __init__(
        self,
        name: str,
        available_minutes_per_day: int,
        preferences: List[str] | None = None,
        concerns: List[str] | None = None,
        pets: List[Pet] | None = None,
    ) -> None:
        self.name = name
        self.available_minutes_per_day = available_minutes_per_day
        self.preferences = preferences if preferences is not None else []
        self.concerns = concerns if concerns is not None else []
        self.pets = pets if pets is not None else []

    def add_pet(self, pet: Pet) -> None:
        pass

    def add_preference(self, pref: str) -> None:
        pass


@dataclass
class ScheduledTask:
    task: Task
    pet_name: str
    start_time: str
    end_time: str
    reason: str


@dataclass
class DailyPlan:
    owner_name: str
    date: str
    items: List[ScheduledTask] = field(default_factory=list)
    minutes_used: int = 0
    minutes_available: int = 0
    summary: str = ""
    explanation: str = ""

    def add_item(self, item: ScheduledTask) -> None:
        pass


class Scheduler:
    def generate_daily_plan(self, owner: Owner) -> DailyPlan:
        pass

    def score_task(self, task: Task, owner: Owner) -> float:
        pass

    def fits_constraints(self, task: Task, minutes_left: int) -> bool:
        pass

    def explain_choice(self, task: Task, owner: Owner) -> str:
        pass
