import anthropic
from dotenv import load_dotenv
from pawpal_system import Task, Pet, Owner, Scheduler

load_dotenv()

TOOLS = [
    {
        "name": "add_pet",
        "description": "Add a new pet to the owner's profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "species": {"type": "string", "enum": ["dog", "cat", "bird", "other"]},
            },
            "required": ["name", "species"],
        },
    },
    {
        "name": "add_task",
        "description": "Add a care task to a specific pet's schedule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {"type": "string"},
                "description": {"type": "string"},
                "start_time": {"type": "string", "description": "HH:MM format"},
                "end_time": {"type": "string", "description": "HH:MM format"},
                "priority": {
                    "type": "integer",
                    "enum": [1, 2, 3],
                    "description": "1=high, 2=medium, 3=low",
                },
                "frequency": {
                    "type": "string",
                    "enum": ["daily", "weekly", "as needed"],
                },
            },
            "required": ["pet_name", "description", "start_time", "end_time", "priority", "frequency"],
        },
    },
    {
        "name": "remove_task",
        "description": "Remove all tasks with a given description from a specific pet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["pet_name", "description"],
        },
    },
    {
        "name": "generate_schedule",
        "description": "Generate and return the owner's pending task schedule, sorted by their preference.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "detect_conflicts",
        "description": "Check for time window overlaps across all pending tasks and return any conflict warnings.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "mark_complete",
        "description": "Mark a specific task as complete. Recurring tasks will automatically reschedule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {"type": "string"},
                "task_description": {"type": "string"},
            },
            "required": ["pet_name", "task_description"],
        },
    },
    {
        "name": "get_all_tasks",
        "description": "Return a summary of all tasks (pending and completed) across all pets.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

SYSTEM_PROMPT = """You are PawPal+, an AI assistant that helps pet owners plan and manage daily care tasks.
You have tools to add pets, add/remove tasks, generate schedules, detect conflicts, and mark tasks complete.

Use a Thought → Action → Observation reasoning cycle:
- Thought: before every tool call, write one sentence starting with "Thought:" that explains what you are about to do and why.
- Action: call the tool.
- Observation: after receiving the result, write one sentence starting with "Observation:" summarising what you learned.
- Repeat until you have enough information to respond to the user.

Always follow these rules:
- After adding or removing any task, always call generate_schedule and then detect_conflicts before responding to the user.
- After marking a task complete, always call generate_schedule to show the updated schedule.
- When asked to plan the day or generate a schedule, call detect_conflicts immediately after generate_schedule.
- Never ask the user for information you can already see in the current owner state.
- Always complete your reasoning cycle before writing your final response to the user."""


def _find_pet(owner: Owner, name: str) -> Pet | None:
    return next((p for p in owner.pets if p.name.lower() == name.lower()), None)


def _find_pending_task(pet: Pet, description: str) -> Task | None:
    return next(
        (t for t in pet.tasks if t.description.lower() == description.lower() and not t.is_complete),
        None,
    )


def _serialize_schedule(schedule: list) -> str:
    if not schedule:
        return "No pending tasks."
    lines = [f"- [{pet.name}] {task.description} ({task.start_time}–{task.end_time}) | priority {task.priority} | {task.frequency}" for pet, task in schedule]
    return "\n".join(lines)


def _serialize_tasks(owner: Owner) -> str:
    tasks = owner.get_all_tasks()
    if not tasks:
        return "No tasks found."
    lines = [
        f"- {task.description} | {'done' if task.is_complete else 'pending'} | priority {task.priority} | {task.frequency}"
        for task in tasks
    ]
    return "\n".join(lines)


def dispatch_tool(name: str, inputs: dict, owner: Owner, scheduler: Scheduler) -> str:
    if name == "add_pet":
        owner.add_pet(Pet(name=inputs["name"], species=inputs["species"]))
        return f"Added {inputs['name']} the {inputs['species']}."

    if name == "add_task":
        pet = _find_pet(owner, inputs["pet_name"])
        if pet is None:
            return f"No pet named '{inputs['pet_name']}' found."
        pet.add_task(Task(
            description=inputs["description"],
            start_time=inputs["start_time"],
            end_time=inputs["end_time"],
            priority=inputs["priority"],
            frequency=inputs["frequency"],
        ))
        return f"Added task '{inputs['description']}' to {pet.name}."

    if name == "remove_task":
        pet = _find_pet(owner, inputs["pet_name"])
        if pet is None:
            return f"No pet named '{inputs['pet_name']}' found."
        pet.remove_task(inputs["description"])
        return f"Removed task '{inputs['description']}' from {pet.name}."

    if name == "generate_schedule":
        schedule = scheduler.generate_schedule(owner)
        return _serialize_schedule(schedule)

    if name == "detect_conflicts":
        warnings = scheduler.detect_conflicts(owner)
        return "\n".join(warnings) if warnings else "No conflicts detected."

    if name == "mark_complete":
        pet = _find_pet(owner, inputs["pet_name"])
        if pet is None:
            return f"No pet named '{inputs['pet_name']}' found."
        task = _find_pending_task(pet, inputs["task_description"])
        if task is None:
            return f"No pending task '{inputs['task_description']}' found for {pet.name}."
        scheduler.mark_complete(task, pet)
        return f"Marked '{task.description}' complete for {pet.name}."

    if name == "get_all_tasks":
        return _serialize_tasks(owner)

    return f"Unknown tool: {name}"


def _build_context(owner: Owner) -> str:
    if not owner.pets:
        return f"Owner: {owner.name} | No pets added yet."
    lines = [f"Owner: {owner.name} | Sort preference: {owner.preferences.get('sort_by', 'time')}"]
    for pet in owner.pets:
        lines.append(f"- {pet.name} ({pet.species})")
        for task in pet.tasks:
            status = "done" if task.is_complete else "pending"
            lines.append(f"  • [{status}] {task.description} {task.start_time}–{task.end_time} | priority {task.priority} | {task.frequency} | due {task.due_date}")
    return "\n".join(lines)


def run_agent(user_message: str, owner: Owner, scheduler: Scheduler, history: list) -> tuple[str, list, list[dict]]:
    """Run one turn of the agent loop. Returns (response_text, updated_history, tool_calls)."""
    client = anthropic.Anthropic()
    context = _build_context(owner)
    system = f"{SYSTEM_PROMPT}\n\nCurrent owner state:\n{context}"
    messages = history + [{"role": "user", "content": user_message}]
    tool_calls = []

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if hasattr(b, "text")), "")
            return text, messages, tool_calls

        # capture reasoning text (Thought/Observation) then execute tool calls
        tool_results = []
        for block in response.content:
            if hasattr(block, "text") and block.text.strip():
                tool_calls.append({"type": "thought", "text": block.text.strip()})
            elif block.type == "tool_use":
                result = dispatch_tool(block.name, block.input, owner, scheduler)
                tool_calls.append({"type": "tool", "name": block.name, "inputs": block.input, "result": result})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "user", "content": tool_results})
