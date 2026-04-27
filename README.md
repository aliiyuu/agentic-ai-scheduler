# PawPal++: Agentic AI Pet Care Planner

## Original Project

This project extends **PawPal+**, originally built in Module 2. The original app was a rule-based Streamlit scheduler that helped pet owners manage daily care tasks across multiple pets. It was built around four classes — `Task`, `Pet`, `Owner`, and `Scheduler` — and supported sorting by time or priority, recurring task scheduling (daily/weekly), conflict detection across overlapping time windows, and live checkbox-based task completion. The original system was entirely deterministic with no AI or agentic functionality.

---

## Title and Summary

**PawPal++* transforms the original rule-based scheduler into a conversational AI system. Instead of manually filling in forms to add pets and tasks, users can describe what they need in plain English — "Add a daily walk for Mochi at 7am" or "Mark breakfast complete and show me what's left" — and a Claude-powered agent handles the rest, calling the appropriate scheduler functions and reporting back in natural language.

This matters because scheduling pet care is a constraint-satisfaction problem involving priorities, time windows, recurrence, and conflicts. A conversational agent that reasons about these constraints and takes multi-step actions (add a task → generate a schedule → check for conflicts) is more useful than a form, and it makes the existing scheduling logic accessible without requiring the user to understand the system's structure.

---

## Architecture Overview

```text
┌─────────────────────────────────────────┐
│              app.py (Streamlit UI)      │
│  - Owner/pet/task forms (manual entry)  │
│  - Schedule view with checkboxes        │
│  - AI chat panel (st.chat_input)        │
└────────────────┬────────────────────────┘
                 │ calls
┌────────────────▼────────────────────────┐
│           agent.py (Agent Loop)         │
│  - TOOLS: 7 tool definitions (JSON)     │
│  - dispatch_tool: routes tool → system  │
│  - run_agent: while-loop until end_turn │
│  - _build_context: injects live state   │
└────────────────┬────────────────────────┘
                 │ mutates
┌────────────────▼────────────────────────┐
│       pawpal_system.py (Core Logic)     │
│  - Task, Pet, Owner dataclasses         │
│  - Scheduler: sort, conflict, recur     │
└─────────────────────────────────────────┘
```

The agent layer sits between the UI and the core logic. On every turn, Claude (Haiku) receives a plain-text snapshot of the current owner state — which pets exist, which tasks are pending or complete, their times and priorities. Claude reads the user's message, selects which tools to call from their JSON schema descriptions, and the `dispatch_tool` function executes those calls against the live `Owner` and `Scheduler` objects held in Streamlit session state.

Two separate histories are maintained: `chat_history` (the raw API message list Claude needs for context, including tool_use and tool_result blocks) and `display_history` (clean user/assistant text pairs for rendering in the UI). This keeps internal tool-call messages from appearing as blank bubbles in the chat. The UI re-renders automatically after any state-modifying tool call via `st.rerun()`, keeping the pet/task tables in sync with what the agent did.

---

## Setup Instructions

### 1. Create a virtual environment pinned to Python 3.13

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your Anthropic API key

Create a `.env` file in the project root (already in `.gitignore`):

```text
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run the app

```bash
streamlit run app.py
```

### 5. Run the test suites

```bash
# Core logic tests (no API key needed)
python -m pytest tests/test_pawpal.py -v

# Agent reliability evals (requires API key)
python -m pytest tests/test_agent_evals.py -v

# Confidence scoring with visible scores
python -m pytest tests/test_agent_evals.py -v -s -k confidence
```

```bash
# Sample output
==================================================== test session starts ====================================================
platform darwin -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0 -- /Users/aliciayu/ai110/ai110-module2show-pawpal-starter/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/aliciayu/ai110/ai110-module2show-pawpal-starter
configfile: pytest.ini
plugins: anyio-4.13.0
collected 26 items / 18 deselected / 8 selected                                                                             

tests/test_agent_evals.py::test_confidence_add_task_tool 
  [add_task tool called] confidence: 100% (5/5 runs passed)
PASSED
tests/test_agent_evals.py::test_confidence_add_task_state 
  [add_task state updated] confidence: 100% (5/5 runs passed)
PASSED
tests/test_agent_evals.py::test_confidence_add_task_correct_frequency 
  [add_task correct frequency] confidence: 100% (5/5 runs passed)
PASSED
tests/test_agent_evals.py::test_confidence_add_task_correct_priority 
  [add_task correct priority] confidence: 100% (5/5 runs passed)
PASSED
tests/test_agent_evals.py::test_confidence_schedule_after_add 
  [generate_schedule follows add_task] confidence: 100% (5/5 runs passed)
PASSED
tests/test_agent_evals.py::test_confidence_conflicts_after_add 
  [detect_conflicts follows add_task] confidence: 100% (5/5 runs passed)
PASSED
tests/test_agent_evals.py::test_confidence_mark_complete_tool 
  [mark_complete tool called] confidence: 100% (5/5 runs passed)
PASSED
tests/test_agent_evals.py::test_confidence_mark_complete_state 
  [mark_complete state updated] confidence: 100% (5/5 runs passed)
PASSED

======================================= 8 passed, 18 deselected in 171.99s (0:02:51) ========================================
```

---

## Sample Interactions

### 1. Adding a pet and task in one message

> **User:** Add a dog named Mochi and give her a daily morning walk from 7:00 to 7:30, high priority.
>
> **PawPal+:** I've added Mochi the dog and scheduled her Morning walk daily from 07:00–07:30 (high priority). Here's her current schedule:
> - [Mochi] Morning walk 07:00–07:30 | priority 1 | daily
>
> No conflicts detected.

*Tools called: `add_pet` → `add_task` → `generate_schedule` → `detect_conflicts`*

---

### 2. Marking a task complete and seeing the updated plan

> **User:** Mochi finished her walk. Mark it complete and show me what's left today.

> **PawPal+:** Marked "Morning walk" complete for Mochi. Since it's a daily task, I've automatically scheduled the next one for tomorrow. Here's what's still pending today:
> - [Mochi] Breakfast 08:00–08:30 | priority 1 | daily
>
> No conflicts.

*Tools called: `mark_complete` → `generate_schedule` → `detect_conflicts`*

---

### 3. Detecting scheduling conflicts

> **User:** Do any of Mochi's tasks overlap?

> **PawPal+:** I checked all pending tasks. There is one conflict:
> CONFLICT: Mochi/"Bath" [12:00–13:00] overlaps with Mochi/"Vet appointment" [12:30–13:30].
> You may want to reschedule one of these.

*Tools called: `detect_conflicts`*

---

## Design Decisions

**Agentic workflow over RAG**
RAG requires a knowledge base and suits Q&A use cases. PawPal+'s core problem is scheduling under constraints, which is a reasoning and action problem. An agent that wraps the existing `pawpal_system.py` functions as tools is a more direct fit, and it means the AI layer extends the original system without replacing or duplicating it. I also decided to make this a very heavily UI-focused app as the original PawPal+ already was very UI-driven and dependent on individual user interaction.

**Four classes kept from original design**
The original Module 2 reflection documents a deliberate simplification from a six-class design (which included `SchedulingContext`, `ScoredTask`, `ScheduledTask`, `DailyPlan`, and two enums) down to four (`Task`, `Pet`, `Owner`, `Scheduler`). Those extra classes are useful for time-window scoring and printable daily plans, but added unnecessary complexity for a minimal working scheduler. The agentic layer builds on the four-class design without re-introducing that complexity.

**Tool descriptions drive routing**
Rather than writing routing logic, Claude infers which tools to call from their natural-language descriptions in the JSON schema. This required careful description writing (distinguishing `generate_schedule` (returns sorted pending tasks) from `get_all_tasks` (returns everything including completed tasks)) but avoids brittle if/else dispatch based on user phrasing.

**System prompt for chaining**
The default model behavior was to call one tool and stop. Explicit rules in the system prompt ("after adding a task, always call `generate_schedule` then `detect_conflicts`") force the multi-step chains the app needs. Prompt engineering here was more effective and less fragile than structural changes to the loop.

**Separate display and API history**
The raw Claude API `messages` list contains `tool_use` and `tool_result` blocks that are meaningless to display. Rendering from it produced blank bubbles and ghost messages. A separate `display_history` of only user/assistant text pairs fixed this cleanly without changing the agent logic.

**Quadratic conflict detection preserved**
The original `detect_conflicts` uses an O(n²) pairwise check by design — it catches non-adjacent overlaps (e.g., a task spanning two others) that a sweep-line approach would miss for small n. This was documented in the Module 2 reflection as a deliberate tradeoff. The agent calls this function unchanged, but the complexity may be improved in later iterations of the app.

---

## Testing Summary

**Core logic tests (`test_pawpal.py`) — 31 tests, all passing**

Covers task defaults, pet management, owner aggregation, sorting correctness, recurrence logic, and conflict detection. These test the pure Python layer with no API calls and remained fully stable throughout the AI integration because `pawpal_system.py` was never modified.

**Agent reliability evals (`test_agent_evals.py`) — 20+ tests**

Tests the AI layer by asserting on tool calls and final state rather than response text (which varies between runs). Structured in three tiers:

| Tier | Approach | Failure condition |
| --- | --- | --- |
| Single-run correctness | Assert tool called / state updated once | Any failure |
| Consistency checks | Run 3× — require 3/3 | Any single failure |
| Confidence scoring | Run 5× — report pass rate (0.0–1.0) | Score below 80% |

**What worked:** Asserting on `tool_calls` (which tool was called, with what inputs) and on Python object state after the run proved far more reliable than matching response text. State assertions caught cases where the right tool was called but with wrong parameters. Adding ReAct-style prompting (Thought → Action → Observation) also measurably improved chaining reliability — the explicit reasoning step before each tool call reduced cases where the agent would skip required follow-up tools. The `detect_conflicts` rule in the system prompt acts as a specific guardrail: by mandating that `detect_conflicts` always runs after any task modification, the system guarantees conflict checking happens regardless of how the user phrases their request, which is a safety property that pure model judgment alone would not reliably provide.

**What didn't:** The agent occasionally skips `detect_conflicts` after `add_task` on ambiguous short prompts. Tightening the system prompt rules improved consistency but didn't reach 100% — reflected in the confidence threshold being 80% rather than requiring a perfect score. The UI (`app.py`) still has no automated tests; end-to-end interactions remain manually verified only.

**What I learned:** Testing a probabilistic system requires a different mental model than testing deterministic code. Binary pass/fail tests misrepresent LLM reliability — a test that passes 4/5 times isn't "passing." Confidence scoring is more honest and more actionable.

---

## Reflection

Building the agentic layer reinforced the Module 2 takeaway that software development is iterative even with AI. In Module 2, the challenge was designing the right abstractions. Here, the challenge was designing the right *interface* between an LLM and those abstractions: tool schemas, system prompt rules, context injection, and state serialization all required iteration that had nothing to do with the model's raw capability.

The most surprising thing was how much behavior could be controlled through the system prompt rather than code. The multi-step chaining problem (agent stops after one tool call) was solved entirely in the prompt, not the loop. This suggests that prompt engineering is a form of system design. Decisions made in natural language that shape control flow as surely as code does.

I also came away with a clearer sense of what "agentic" actually means. PawPal+ now acts on multiple steps without the user driving each one, but it only acts when prompted. A genuinely autonomous version would monitor the schedule and surface overdue tasks unprompted. This would require persistent state across sessions, background execution, and a more sophisticated memory model.