from pawpal_system import Task, Pet, Scheduler


def test_mark_complete_changes_status():
    task = Task(description="Feed breakfast", time_minutes=5, frequency="daily")
    scheduler = Scheduler()

    assert task.is_complete is False
    scheduler.mark_complete(task)
    assert task.is_complete is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Biscuit", species="Dog")
    task = Task(description="Morning walk", time_minutes=30, frequency="daily")

    assert len(pet.tasks) == 0
    pet.add_task(task)
    assert len(pet.tasks) == 1
