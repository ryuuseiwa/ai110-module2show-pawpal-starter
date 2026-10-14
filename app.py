"""PawPal+ Streamlit UI. All logic lives in pawpal_system.py; this file only wires it to widgets."""

from datetime import date

import streamlit as st

from pawpal_system import FREQUENCIES, Owner, Pet, Priority, Scheduler, Task

DATA_FILE = "data.json"
PRIORITY_BADGE = {Priority.HIGH: "🔴 high", Priority.MEDIUM: "🟡 medium", Priority.LOW: "🟢 low"}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")


# ----- application "memory" -------------------------------------------------
# Streamlit reruns this script on every click, so the Owner lives in
# st.session_state and is only created (or loaded from disk) the first time.
if "owner" not in st.session_state:
    st.session_state.owner = Owner.load_from_json(DATA_FILE) or Owner("Jordan")

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)


def save() -> None:
    """Persist the current owner to data.json after every change."""
    owner.save_to_json(DATA_FILE)


def task_rows(tasks: list[Task]) -> list[dict]:
    """Turn tasks into table rows for display."""
    return [
        {
            "Time": t.time,
            "Pet": t.pet_name,
            "Task": f"{t.emoji} {t.description}",
            "Minutes": t.duration_minutes,
            "Priority": PRIORITY_BADGE[t.priority],
            "Repeats": t.frequency,
            "Date": t.due_date.isoformat(),
            "Status": "✅ done" if t.completed else "⏳ todo",
        }
        for t in tasks
    ]


# ----- sidebar: owner + persistence -----------------------------------------
with st.sidebar:
    st.header("👤 Owner")
    new_name = st.text_input("Owner name", value=owner.name)
    if new_name and new_name != owner.name:
        owner.name = new_name
        save()
    view_date = st.date_input("Schedule date", value=date.today())
    st.caption(f"Data auto-saves to `{DATA_FILE}`.")
    if st.button("🗑️ Reset all data"):
        st.session_state.owner = Owner(owner.name)
        st.session_state.owner.save_to_json(DATA_FILE)
        st.rerun()

st.title("🐾 PawPal+")
st.caption(f"Smart pet care planning for {owner.name}'s household.")

col_pet, col_task = st.columns(2)

# ----- add a pet --------------------------------------------------------------
with col_pet:
    st.subheader("Add a pet")
    with st.form("add_pet", clear_on_submit=True):
        pet_name = st.text_input("Pet name", placeholder="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        age = st.number_input("Age (years)", min_value=0, max_value=40, value=1)
        if st.form_submit_button("Add pet"):
            if not pet_name.strip():
                st.error("Please enter a pet name.")
            else:
                try:
                    owner.add_pet(Pet(pet_name.strip(), species, int(age)))
                    save()
                    st.success(f"Added {pet_name} the {species}!")
                except ValueError as err:
                    st.error(str(err))
    if owner.pets:
        st.write("**Your pets:** " + ", ".join(f"{p.name} ({p.species}, {p.task_count()} tasks)" for p in owner.pets))
    else:
        st.info("No pets yet. Add one to start scheduling.")

# ----- schedule a task ------------------------------------------------------
with col_task:
    st.subheader("Schedule a task")
    if not owner.pets:
        st.info("Add a pet first.")
    else:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=20)
        slot = scheduler.find_next_available_slot(int(duration), on=view_date)
        st.caption(
            f"🕒 Next free {duration}-minute slot on {view_date}: **{slot}**"
            if slot else f"🕒 No free {duration}-minute slot left on {view_date} (07:00–22:00)."
        )
        with st.form("add_task", clear_on_submit=True):
            target = st.selectbox("Pet", [p.name for p in owner.pets])
            description = st.text_input("Task", placeholder="Morning walk")
            c1, c2 = st.columns(2)
            with c1:
                default_time = slot or "08:00"
                time_text = st.text_input("Time (HH:MM)", value=default_time)
                priority = st.selectbox("Priority", ["high", "medium", "low"], index=1)
            with c2:
                frequency = st.selectbox("Repeats", FREQUENCIES)
                due = st.date_input("Date", value=view_date)
            if st.form_submit_button("Add task"):
                try:
                    task = Task(description.strip() or "Care task", time_text, int(duration), priority, frequency, due)
                    owner.get_pet(target).add_task(task)
                    save()
                    st.success(f"Scheduled {task.emoji} {task.description} for {target} at {task.time}.")
                except ValueError as err:
                    st.error(str(err))

st.divider()

# ----- schedule view ----------------------------------------------------------
st.subheader(f"📅 Schedule for {view_date:%A, %b %d}")

f1, f2, f3 = st.columns(3)
with f1:
    pet_filter = st.selectbox("Pet", ["All pets"] + [p.name for p in owner.pets])
with f2:
    status_filter = st.selectbox("Status", ["All", "To do", "Done"])
with f3:
    sort_mode = st.radio("Sort by", ["Time", "Priority, then time"], horizontal=True)

tasks = scheduler.filter_tasks(
    on=view_date,
    pet_name=None if pet_filter == "All pets" else pet_filter,
    completed={"All": None, "To do": False, "Done": True}[status_filter],
)
tasks = scheduler.sort_by_time(tasks) if sort_mode == "Time" else scheduler.sort_by_priority(tasks)

conflicts = scheduler.detect_conflicts(on=view_date)
if conflicts:
    st.warning(
        f"**{len(conflicts)} scheduling conflict(s).** You can't be in two places at once. "
        "Move one task in each pair, or use the suggested free slot above.\n\n"
        + "\n".join(f"- {c}" for c in conflicts)
    )
elif tasks:
    st.success("No conflicts. Every task has its own time slot.")

if tasks:
    st.table(task_rows(tasks))
    pending = [t for t in tasks if not t.completed]
    if pending:
        st.markdown("**Mark a task done**")
        labels = {f"{t.time} · {t.pet_name} · {t.description}": t for t in pending}
        choice = st.selectbox("Task to complete", list(labels), label_visibility="collapsed")
        if st.button("✅ Mark complete"):
            done = labels[choice]
            nxt = scheduler.mark_task_complete(done)
            save()
            if nxt:
                st.toast(f"Done! Next {done.description} scheduled for {nxt.due_date} at {nxt.time}.")
            else:
                st.toast(f"Done: {done.description}")
            st.rerun()
else:
    st.info("No tasks match these filters for this date.")

st.divider()

# ----- smart daily plan -------------------------------------------------------
st.subheader("🧠 Build today's plan")
st.caption("Short on time? PawPal+ keeps the highest-priority tasks that fit and explains each choice.")
available = st.slider("Minutes you have for pet care", 10, 480, 90, step=5)
if st.button("Generate plan"):
    plan = scheduler.plan_day(available, on=view_date)
    if not plan.scheduled and not plan.skipped:
        st.info("Nothing left to do on this date. 🎉")
    else:
        st.success(f"Planned {len(plan.scheduled)} task(s) using {plan.minutes_used} of {available} minutes.")
        for t in plan.scheduled:
            st.markdown(f"- **{t.time}** {t.emoji} {t.pet_name}: {t.description}. *{plan.reason_for(t)}*")
        if plan.skipped:
            st.warning("Didn't fit today:\n\n" + "\n".join(
                f"- {t.emoji} {t.pet_name}: {t.description}. {plan.reason_for(t)}" for t in plan.skipped
            ))
