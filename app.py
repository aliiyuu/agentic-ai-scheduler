import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler
from agent import run_agent

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("A daily pet care planner — add your pets, build tasks, and generate a prioritized schedule.")

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # raw API messages passed to run_agent
if "display_history" not in st.session_state:
    st.session_state.display_history = []  # clean user/assistant pairs for rendering

PRIORITY_LABEL = {1: "⬆ High", 2: "➡ Medium", 3: "⬇ Low"}

# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------
st.subheader("Owner")
col_name, col_sort = st.columns(2)
with col_name:
    owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
    st.session_state.owner.name = owner_name
with col_sort:
    sort_by = st.selectbox(
        "Sort schedule by",
        ["time", "priority"],
        index=["time", "priority"].index(st.session_state.owner.preferences.get("sort_by", "time")),
        help="'time' sorts chronologically; 'priority' puts high-priority tasks first, ties broken by start time.",
    )
    st.session_state.owner.preferences["sort_by"] = sort_by

st.divider()

# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------
st.subheader("Pets")
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "bird", "other"])
with col3:
    st.write("")
    st.write("")
    if st.button("Add pet", use_container_width=True):
        st.session_state.owner.add_pet(Pet(name=pet_name, species=species))
        st.success(f"Added {pet_name} the {species}!")

if st.session_state.owner.pets:
    st.table([
        {"Name": p.name, "Species": p.species.title(), "Tasks": len(p.tasks)}
        for p in st.session_state.owner.pets
    ])
else:
    st.info("No pets yet — add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
st.subheader("Tasks")

if not st.session_state.owner.pets:
    st.info("Add a pet first before adding tasks.")
else:
    pet_names = [p.name for p in st.session_state.owner.pets]
    selected_pet_name = st.selectbox("Add task to", pet_names)

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        start_time = st.text_input("Start time (HH:MM)", value="07:00")
    with col3:
        end_time = st.text_input("End time (HH:MM)", value="07:30")

    col4, col5, col6 = st.columns([2, 2, 1])
    with col4:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "as needed"])
    with col5:
        priority = st.selectbox(
            "Priority", [1, 2, 3], index=1,
            format_func=lambda p: PRIORITY_LABEL[p],
        )
    with col6:
        st.write("")
        st.write("")
        add_clicked = st.button("Add task", use_container_width=True)

    if add_clicked:
        selected_pet = next(p for p in st.session_state.owner.pets if p.name == selected_pet_name)
        selected_pet.add_task(Task(
            description=task_title,
            start_time=start_time,
            end_time=end_time,
            frequency=frequency,
            priority=priority,
        ))
        st.success(f"Added \"{task_title}\" to {selected_pet_name}.")

    all_tasks = st.session_state.owner.get_all_tasks()
    if all_tasks:
        st.markdown("**All tasks**")
        st.table([
            {
                "Pet": pet.name,
                "Task": t.description,
                "Priority": PRIORITY_LABEL[t.priority],
                "Start": t.start_time,
                "End": t.end_time,
                "Frequency": t.frequency,
                "Due": t.due_date,
                "Status": "✅ Done" if t.is_complete else "🕐 Pending",
            }
            for pet in st.session_state.owner.pets
            for t in pet.tasks
        ])

st.divider()

# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------
st.subheader("Schedule")
st.caption(f"Pending tasks sorted by **{st.session_state.owner.preferences['sort_by']}**. Check a task to mark it complete — recurring tasks reschedule automatically.")

if st.button("Generate schedule", type="primary"):
    st.session_state.schedule = st.session_state.scheduler.generate_schedule(st.session_state.owner)

if "schedule" in st.session_state:
    # Conflict warnings / success banner
    conflicts = st.session_state.scheduler.detect_conflicts(st.session_state.owner)
    if conflicts:
        for warning in conflicts:
            st.warning(warning)
    else:
        st.success("No scheduling conflicts detected.")

    schedule = st.session_state.schedule

    if not schedule:
        st.info("No pending tasks — all done!")
    else:
        # Summary metrics
        total = len(st.session_state.owner.get_all_tasks())
        pending = len(schedule)
        done = total - pending
        m1, m2, m3 = st.columns(3)
        m1.metric("Total tasks", total)
        m2.metric("Pending", pending)
        m3.metric("Completed", done)

        st.markdown("---")

        # Column headers
        hcols = st.columns([1, 3, 2, 2, 2, 2])
        for col, label in zip(hcols, ["Done", "Task", "Priority", "Pet", "Time", "Frequency"]):
            col.markdown(f"**{label}**")
        st.divider()

        for i, (pet, task) in enumerate(schedule):
            col1, col2, col3, col4, col5, col6 = st.columns([1, 3, 2, 2, 2, 2])
            with col1:
                checked = st.checkbox(
                    label="complete",
                    value=task.is_complete,
                    key=f"chk_{i}_{pet.name}_{task.description}_{task.due_date}",
                    label_visibility="collapsed",
                )
                if checked and not task.is_complete:
                    st.session_state.scheduler.mark_complete(task, pet)
                    st.session_state.schedule = st.session_state.scheduler.generate_schedule(st.session_state.owner)
                    st.rerun()
            col2.write(task.description)
            col3.write(PRIORITY_LABEL[task.priority])
            col4.write(pet.name)
            col5.write(f"{task.start_time}–{task.end_time}")
            col6.write(task.frequency)

st.divider()

# ---------------------------------------------------------------------------
# AI Assistant
# ---------------------------------------------------------------------------
st.subheader("AI Assistant")
st.caption("Ask PawPal+ to add pets, manage tasks, generate a schedule, or plan your day.")

for msg in st.session_state.display_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("tool_calls"):
            with st.expander(f"🔧 Tools called ({len(msg['tool_calls'])})"):
                for call in msg["tool_calls"]:
                    st.markdown(f"**`{call['name']}`**")
                    if call["inputs"]:
                        st.json(call["inputs"])
                    st.caption(f"Result: {call['result']}")
                    st.divider()

MODIFYING_TOOLS = {"add_pet", "add_task", "remove_task", "mark_complete"}

if prompt := st.chat_input("Ask PawPal+ anything..."):
    st.session_state.display_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response, st.session_state.chat_history, tool_calls = run_agent(
                prompt,
                st.session_state.owner,
                st.session_state.scheduler,
                st.session_state.chat_history,
            )
        st.session_state.display_history.append({
            "role": "assistant",
            "content": response,
            "tool_calls": tool_calls,
        })
        if tool_calls:
            with st.expander(f"🔧 Tools called ({len(tool_calls)})"):
                for call in tool_calls:
                    st.markdown(f"**`{call['name']}`**")
                    if call["inputs"]:
                        st.json(call["inputs"])
                    st.caption(f"Result: {call['result']}")
                    st.divider()
        st.write(response)

    if any(call["name"] in MODIFYING_TOOLS for call in tool_calls):
        st.rerun()
