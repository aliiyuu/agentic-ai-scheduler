"""
Agent reliability evals — these make real Anthropic API calls.
Run with: python -m pytest tests/test_agent_evals.py -v
Requires ANTHROPIC_API_KEY in environment or .env file.
"""
import os
import pytest
from pawpal_system import Task, Pet, Owner, Scheduler
from agent import run_agent

pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping agent evals",
)

CONSISTENCY_RUNS = 3  # number of times to repeat each consistency check
CONFIDENCE_RUNS = 5   # number of runs for confidence scoring
CONFIDENCE_THRESHOLD = 0.8  # minimum acceptable score (4/5 runs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fresh_state():
    """Clean owner with one pet and no tasks."""
    pet = Pet(name="Mochi", species="dog")
    owner = Owner(name="Jordan")
    owner.add_pet(pet)
    return owner, pet, Scheduler()


def fresh_state_with_task(description="Morning walk", start="07:00", end="07:30",
                           frequency="daily", priority=1):
    """Clean owner with one pet and one pending task."""
    owner, pet, scheduler = fresh_state()
    pet.add_task(Task(description=description, start_time=start, end_time=end,
                      frequency=frequency, priority=priority))
    return owner, pet, scheduler


def tool_names(tool_calls):
    return [c["name"] for c in tool_calls]


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------

def test_add_task_calls_correct_tool():
    owner, pet, scheduler = fresh_state()
    _, _, tool_calls = run_agent(
        "Add a task called Morning walk for Mochi, daily from 07:00 to 07:30, high priority.",
        owner, scheduler, [],
    )
    assert "add_task" in tool_names(tool_calls), f"Expected add_task, got: {tool_names(tool_calls)}"


def test_add_task_updates_state():
    owner, pet, scheduler = fresh_state()
    run_agent(
        "Add a task called Morning walk for Mochi, daily from 07:00 to 07:30, high priority.",
        owner, scheduler, [],
    )
    assert len(pet.tasks) == 1, f"Expected 1 task, got {len(pet.tasks)}"


def test_add_task_correct_pet():
    owner, pet, scheduler = fresh_state()
    run_agent(
        "Add a task called Morning walk for Mochi, daily from 07:00 to 07:30, high priority.",
        owner, scheduler, [],
    )
    add_calls = [c for c in run_agent(
        "Add a task called Evening walk for Mochi, daily from 18:00 to 18:30, medium priority.",
        owner, scheduler, [],
    )[2] if c["name"] == "add_task"]
    assert all(c["inputs"]["pet_name"].lower() == "mochi" for c in add_calls)


def test_add_task_correct_frequency():
    owner, pet, scheduler = fresh_state()
    _, _, tool_calls = run_agent(
        "Add a weekly bath task for Mochi from 12:00 to 13:00, low priority.",
        owner, scheduler, [],
    )
    add_call = next((c for c in tool_calls if c["name"] == "add_task"), None)
    assert add_call is not None
    assert add_call["inputs"]["frequency"] == "weekly", \
        f"Expected weekly, got: {add_call['inputs']['frequency']}"


def test_add_task_followed_by_generate_schedule():
    """After adding a task the agent should always call generate_schedule."""
    owner, pet, scheduler = fresh_state()
    _, _, tool_calls = run_agent(
        "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
        owner, scheduler, [],
    )
    assert "generate_schedule" in tool_names(tool_calls), \
        f"Expected generate_schedule after add_task. Got: {tool_names(tool_calls)}"


def test_add_task_followed_by_detect_conflicts():
    """After adding a task the agent should always call detect_conflicts."""
    owner, pet, scheduler = fresh_state()
    _, _, tool_calls = run_agent(
        "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
        owner, scheduler, [],
    )
    assert "detect_conflicts" in tool_names(tool_calls), \
        f"Expected detect_conflicts after add_task. Got: {tool_names(tool_calls)}"


# ---------------------------------------------------------------------------
# add_pet
# ---------------------------------------------------------------------------

def test_add_pet_calls_correct_tool():
    owner = Owner(name="Jordan")
    scheduler = Scheduler()
    _, _, tool_calls = run_agent("Add a cat named Luna.", owner, scheduler, [])
    assert "add_pet" in tool_names(tool_calls), f"Expected add_pet, got: {tool_names(tool_calls)}"


def test_add_pet_updates_state():
    owner = Owner(name="Jordan")
    scheduler = Scheduler()
    run_agent("Add a cat named Luna.", owner, scheduler, [])
    assert len(owner.pets) == 1, f"Expected 1 pet, got {len(owner.pets)}"


def test_add_pet_correct_species():
    owner = Owner(name="Jordan")
    scheduler = Scheduler()
    _, _, tool_calls = run_agent("Add a bird named Kiwi.", owner, scheduler, [])
    add_call = next((c for c in tool_calls if c["name"] == "add_pet"), None)
    assert add_call is not None
    assert add_call["inputs"]["species"] == "bird", \
        f"Expected bird, got: {add_call['inputs']['species']}"


# ---------------------------------------------------------------------------
# mark_complete
# ---------------------------------------------------------------------------

def test_mark_complete_calls_correct_tool():
    owner, pet, scheduler = fresh_state_with_task("Morning walk")
    _, _, tool_calls = run_agent(
        "Mark the Morning walk complete for Mochi.", owner, scheduler, [],
    )
    assert "mark_complete" in tool_names(tool_calls), \
        f"Expected mark_complete, got: {tool_names(tool_calls)}"


def test_mark_complete_updates_state():
    owner, pet, scheduler = fresh_state_with_task("Morning walk")
    run_agent("Mark the Morning walk complete for Mochi.", owner, scheduler, [])
    assert pet.tasks[0].is_complete is True, "Expected task to be marked complete"


def test_mark_complete_daily_creates_next_task():
    owner, pet, scheduler = fresh_state_with_task("Morning walk", frequency="daily")
    run_agent("Mark the Morning walk complete for Mochi.", owner, scheduler, [])
    pending = [t for t in pet.tasks if not t.is_complete]
    assert len(pending) == 1, f"Expected 1 new pending task, got {len(pending)}"


# ---------------------------------------------------------------------------
# generate_schedule / detect_conflicts (read-only)
# ---------------------------------------------------------------------------

def test_generate_schedule_on_request():
    owner, pet, scheduler = fresh_state_with_task()
    _, _, tool_calls = run_agent("Show me today's schedule.", owner, scheduler, [])
    assert "generate_schedule" in tool_names(tool_calls), \
        f"Expected generate_schedule, got: {tool_names(tool_calls)}"


def test_detect_conflicts_on_request():
    owner, pet, scheduler = fresh_state_with_task()
    _, _, tool_calls = run_agent("Are there any scheduling conflicts?", owner, scheduler, [])
    assert "detect_conflicts" in tool_names(tool_calls), \
        f"Expected detect_conflicts, got: {tool_names(tool_calls)}"


# ---------------------------------------------------------------------------
# Consistency checks — each prompt is run CONSISTENCY_RUNS times
# ---------------------------------------------------------------------------

def _run_n(prompt, owner_factory, n=CONSISTENCY_RUNS):
    """Run a prompt n times with a fresh state each time. Returns list of tool_calls lists."""
    results = []
    for _ in range(n):
        owner, pet, scheduler = owner_factory()
        _, _, tool_calls = run_agent(prompt, owner, scheduler, [])
        results.append(tool_calls)
    return results


def test_consistency_add_task_tool_called():
    """add_task should be called every time for a clear add-task prompt."""
    all_runs = _run_n(
        "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
        fresh_state,
    )
    passes = sum(1 for tc in all_runs if "add_task" in tool_names(tc))
    assert passes == CONSISTENCY_RUNS, \
        f"add_task called in only {passes}/{CONSISTENCY_RUNS} runs"


def test_consistency_mark_complete_tool_called():
    """mark_complete should be called every time for a clear complete prompt."""
    all_runs = _run_n(
        "Mark the Morning walk complete for Mochi.",
        lambda: fresh_state_with_task("Morning walk"),
    )
    passes = sum(1 for tc in all_runs if "mark_complete" in tool_names(tc))
    assert passes == CONSISTENCY_RUNS, \
        f"mark_complete called in only {passes}/{CONSISTENCY_RUNS} runs"


def test_consistency_schedule_after_add():
    """generate_schedule should follow add_task every time."""
    all_runs = _run_n(
        "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
        fresh_state,
    )
    passes = sum(1 for tc in all_runs if "generate_schedule" in tool_names(tc))
    assert passes == CONSISTENCY_RUNS, \
        f"generate_schedule followed add_task in only {passes}/{CONSISTENCY_RUNS} runs"


def test_consistency_state_updated_after_add():
    """Pet should always have exactly 1 task after a single add-task prompt."""
    for _ in range(CONSISTENCY_RUNS):
        owner, pet, scheduler = fresh_state()
        run_agent(
            "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
            owner, scheduler, [],
        )
        assert len(pet.tasks) == 1, \
            f"Expected 1 task after add, got {len(pet.tasks)}"


# ---------------------------------------------------------------------------
# Confidence scoring
# Runs each eval CONFIDENCE_RUNS times and reports a 0.0–1.0 score.
# Fails if score drops below CONFIDENCE_THRESHOLD.
# Use -s flag to see printed scores: python -m pytest tests/test_agent_evals.py -v -s
# ---------------------------------------------------------------------------

def score_eval(prompt, owner_factory, check_fn, n=CONFIDENCE_RUNS):
    """
    Run an eval n times and return a confidence score (0.0–1.0).
    check_fn(tool_calls, owner) -> bool
    """
    passes = 0
    for _ in range(n):
        owner, pet, scheduler = owner_factory()
        _, _, tool_calls = run_agent(prompt, owner, scheduler, [])
        if check_fn(tool_calls, owner):
            passes += 1
    return passes / n


def assert_confidence(label, score, threshold=CONFIDENCE_THRESHOLD):
    print(f"\n  [{label}] confidence: {score:.0%} ({int(score * CONFIDENCE_RUNS)}/{CONFIDENCE_RUNS} runs passed)")
    assert score >= threshold, \
        f"[{label}] confidence {score:.0%} is below threshold {threshold:.0%}"


def test_confidence_add_task_tool():
    score = score_eval(
        "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
        fresh_state,
        lambda tc, _: "add_task" in tool_names(tc),
    )
    assert_confidence("add_task tool called", score)


def test_confidence_add_task_state():
    score = score_eval(
        "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
        fresh_state,
        lambda _, owner: len(owner.pets[0].tasks) == 1,
    )
    assert_confidence("add_task state updated", score)


def test_confidence_add_task_correct_frequency():
    score = score_eval(
        "Add a weekly bath for Mochi from 12:00 to 13:00, low priority.",
        fresh_state,
        lambda tc, _: any(
            c["name"] == "add_task" and c["inputs"].get("frequency") == "weekly"
            for c in tc
        ),
    )
    assert_confidence("add_task correct frequency", score)


def test_confidence_add_task_correct_priority():
    score = score_eval(
        "Add a high priority daily morning walk for Mochi from 07:00 to 07:30.",
        fresh_state,
        lambda tc, _: any(
            c["name"] == "add_task" and c["inputs"].get("priority") == 1
            for c in tc
        ),
    )
    assert_confidence("add_task correct priority", score)


def test_confidence_schedule_after_add():
    score = score_eval(
        "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
        fresh_state,
        lambda tc, _: "generate_schedule" in tool_names(tc),
    )
    assert_confidence("generate_schedule follows add_task", score)


def test_confidence_conflicts_after_add():
    score = score_eval(
        "Add a daily morning walk for Mochi from 07:00 to 07:30, high priority.",
        fresh_state,
        lambda tc, _: "detect_conflicts" in tool_names(tc),
    )
    assert_confidence("detect_conflicts follows add_task", score)


def test_confidence_mark_complete_tool():
    score = score_eval(
        "Mark the Morning walk complete for Mochi.",
        lambda: fresh_state_with_task("Morning walk"),
        lambda tc, _: "mark_complete" in tool_names(tc),
    )
    assert_confidence("mark_complete tool called", score)


def test_confidence_mark_complete_state():
    score = score_eval(
        "Mark the Morning walk complete for Mochi.",
        lambda: fresh_state_with_task("Morning walk"),
        lambda _, owner: owner.pets[0].tasks[0].is_complete,
    )
    assert_confidence("mark_complete state updated", score)
