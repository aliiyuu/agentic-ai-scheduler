from pawpal_system import Task, Pet, Owner, Scheduler

# --- Setup ---
owner = Owner(name="Alex")

dog = Pet(name="Biscuit", species="Dog")
cat = Pet(name="Luna", species="Cat")

dog.add_task(Task(description="Morning walk", time_minutes=30, frequency="daily"))
dog.add_task(Task(description="Feed breakfast", time_minutes=5, frequency="daily"))
cat.add_task(Task(description="Clean litter box", time_minutes=10, frequency="daily"))

owner.add_pet(dog)
owner.add_pet(cat)

# --- Generate schedule ---
scheduler = Scheduler()
schedule = scheduler.generate_schedule(owner)

# --- Print ---
print("=== Today's Schedule ===")
for task in schedule:
    status = "done" if task.is_complete else "pending"
    print(f"  [{task.time_minutes} min] {task.description} ({task.frequency}) — {status}")
