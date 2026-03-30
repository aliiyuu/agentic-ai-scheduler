from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Task:
    description: str
    time_minutes: int
    frequency: str
    is_complete: bool = False


@dataclass
class Pet:
    name: str
    species: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, description: str) -> None:
        """Remove all tasks matching the given description."""
        self.tasks = [t for t in self.tasks if t.description != description]


@dataclass
class Owner:
    name: str
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's pet list."""
        self.pets.append(pet)

    def get_all_tasks(self) -> List[Task]:
        """Return a flat list of all tasks across every pet."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:
    def get_pending_tasks(self, owner: Owner) -> List[Task]:
        """Return all incomplete tasks across the owner's pets."""
        return [t for t in owner.get_all_tasks() if not t.is_complete]

    def organize_by_time(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks in ascending order by duration."""
        return sorted(tasks, key=lambda t: t.time_minutes)

    def mark_complete(self, task: Task) -> None:
        """Mark a task as complete."""
        task.is_complete = True

    def generate_schedule(self, owner: Owner) -> List[Task]:
        """Return pending tasks sorted by duration."""
        return self.organize_by_time(self.get_pending_tasks(owner))
