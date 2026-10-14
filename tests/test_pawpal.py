from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

DAY = date(2026, 10, 14)


@pytest.fixture
def household():
    """An owner with two pets and no tasks."""
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", 3))
    owner.add_pet(Pet("Luna", "cat", 5))
    return owner


def add(owner, pet_name, description, time, duration=15, priority="medium", frequency="once", on=DAY):
    """Helper: create a task and attach it to the named pet."""
    task = Task(description, time, duration, priority, frequency, due_date=on)
    owner.get_pet(pet_name).add_task(task)
    return task


# ----- Phase 2 basics -------------------------------------------------------

def test_mark_complete_changes_status():
    task = Task("Morning walk", "08:00")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    assert pet.task_count() == 0
    pet.add_task(Task("Breakfast", "07:30"))
    assert pet.task_count() == 1


def test_add_task_tags_task_with_pet_name():
    pet = Pet("Mochi", "dog")
    task = Task("Walk", "08:00")
    pet.add_task(task)
    assert task.pet_name == "Mochi"


def test_owner_get_all_tasks_spans_every_pet(household):
    add(household, "Mochi", "Walk", "08:00")
    add(household, "Luna", "Breakfast", "07:30")
    assert {t.pet_name for t in household.get_all_tasks()} == {"Mochi", "Luna"}


def test_duplicate_pet_name_rejected(household):
    with pytest.raises(ValueError):
        household.add_pet(Pet("mochi", "dog"))


@pytest.mark.parametrize("bad_time", ["8am", "24:00", "12:60", ""])
def test_invalid_time_rejected(bad_time):
    with pytest.raises(ValueError):
        Task("Walk", bad_time)


def test_single_digit_hour_is_zero_padded():
    assert Task("Walk", "8:05").time == "08:05"


# ----- Sorting --------------------------------------------------------------

def test_sort_by_time_returns_chronological_order(household):
    add(household, "Mochi", "Evening walk", "18:30")
    add(household, "Luna", "Breakfast", "07:30")
    add(household, "Mochi", "Lunch", "12:00")
    times = [t.time for t in Scheduler(household).sort_by_time()]
    assert times == ["07:30", "12:00", "18:30"]


def test_sort_by_time_handles_unpadded_input(household):
    # "9:00" would sort after "10:00" as raw text; normalization prevents that.
    add(household, "Mochi", "Late", "10:00")
    add(household, "Mochi", "Early", "9:00")
    assert [t.description for t in Scheduler(household).sort_by_time()] == ["Early", "Late"]


def test_sort_by_time_orders_by_date_before_time(household):
    add(household, "Mochi", "Tomorrow early", "06:00", on=DAY + timedelta(days=1))
    add(household, "Mochi", "Today late", "21:00")
    assert [t.description for t in Scheduler(household).sort_by_time()] == ["Today late", "Tomorrow early"]


def test_sort_by_priority_then_time(household):
    add(household, "Mochi", "Low early", "07:00", priority="low")
    add(household, "Mochi", "High late", "20:00", priority="high")
    add(household, "Luna", "High early", "09:00", priority="high")
    add(household, "Luna", "Medium", "08:00", priority="medium")
    names = [t.description for t in Scheduler(household).sort_by_priority()]
    assert names == ["High early", "High late", "Medium", "Low early"]


def test_sorting_empty_schedule_returns_empty_list(household):
    assert Scheduler(household).sort_by_time() == []


def test_priority_parse_accepts_names_and_ints():
    assert Priority.parse("High") is Priority.HIGH
    assert Priority.parse(1) is Priority.LOW


# ----- Filtering ------------------------------------------------------------

def test_filter_by_pet_name_is_case_insensitive(household):
    add(household, "Mochi", "Walk", "08:00")
    add(household, "Luna", "Breakfast", "07:30")
    result = Scheduler(household).filter_tasks(pet_name="luna")
    assert [t.description for t in result] == ["Breakfast"]


def test_filter_by_completion_status(household):
    done = add(household, "Mochi", "Walk", "08:00")
    add(household, "Luna", "Breakfast", "07:30")
    done.mark_complete()
    scheduler = Scheduler(household)
    assert scheduler.filter_tasks(completed=True) == [done]
    assert [t.description for t in scheduler.filter_tasks(completed=False)] == ["Breakfast"]


def test_filters_combine(household):
    add(household, "Mochi", "Walk", "08:00")
    add(household, "Mochi", "Tomorrow walk", "08:00", on=DAY + timedelta(days=1))
    result = Scheduler(household).filter_tasks(pet_name="Mochi", on=DAY)
    assert [t.description for t in result] == ["Walk"]


def test_pet_with_no_tasks_filters_to_empty(household):
    add(household, "Mochi", "Walk", "08:00")
    assert Scheduler(household).filter_tasks(pet_name="Luna") == []


# ----- Recurring tasks ------------------------------------------------------

def test_completing_daily_task_creates_task_for_next_day(household):
    walk = add(household, "Mochi", "Walk", "08:00", frequency="daily")
    nxt = Scheduler(household).mark_task_complete(walk)
    assert walk.completed is True
    assert nxt.due_date == DAY + timedelta(days=1)
    assert nxt.completed is False
    assert (nxt.time, nxt.description, nxt.pet_name) == ("08:00", "Walk", "Mochi")
    assert nxt in household.get_pet("Mochi").tasks


def test_completing_weekly_task_creates_task_seven_days_later(household):
    meds = add(household, "Luna", "Flea meds", "12:00", frequency="weekly")
    nxt = Scheduler(household).mark_task_complete(meds)
    assert nxt.due_date == DAY + timedelta(weeks=1)


def test_recurrence_crosses_month_boundary(household):
    task = add(household, "Mochi", "Walk", "08:00", frequency="daily", on=date(2026, 10, 31))
    assert Scheduler(household).mark_task_complete(task).due_date == date(2026, 11, 1)


def test_completing_one_off_task_creates_nothing(household):
    bath = add(household, "Mochi", "Bath", "15:00")
    assert Scheduler(household).mark_task_complete(bath) is None
    assert household.get_pet("Mochi").task_count() == 1


def test_next_occurrence_is_independent_copy(household):
    walk = add(household, "Mochi", "Walk", "08:00", frequency="daily")
    nxt = Scheduler(household).mark_task_complete(walk)
    nxt.mark_complete()
    assert nxt is not walk and walk.due_date == DAY


# ----- Conflict detection ---------------------------------------------------

def test_conflict_flags_duplicate_times(household):
    add(household, "Mochi", "Walk", "08:00")
    add(household, "Luna", "Breakfast", "08:00")
    warnings = Scheduler(household).detect_conflicts()
    assert len(warnings) == 1
    assert "same time" in warnings[0] and "Walk" in warnings[0] and "Breakfast" in warnings[0]


def test_conflict_flags_overlapping_durations_same_pet(household):
    add(household, "Mochi", "Walk", "08:00", duration=30)
    add(household, "Mochi", "Bath", "08:20", duration=15)
    warnings = Scheduler(household).detect_conflicts()
    assert len(warnings) == 1 and "overlap" in warnings[0] and "both for Mochi" in warnings[0]


def test_back_to_back_tasks_do_not_conflict(household):
    add(household, "Mochi", "Walk", "08:00", duration=30)
    add(household, "Mochi", "Breakfast", "08:30", duration=10)
    assert Scheduler(household).detect_conflicts() == []


def test_same_time_on_different_days_is_not_a_conflict(household):
    add(household, "Mochi", "Walk", "08:00")
    add(household, "Mochi", "Walk", "08:00", on=DAY + timedelta(days=1))
    assert Scheduler(household).detect_conflicts() == []


def test_completed_tasks_are_ignored_by_conflict_check(household):
    add(household, "Mochi", "Walk", "08:00").mark_complete()
    add(household, "Luna", "Breakfast", "08:00")
    assert Scheduler(household).detect_conflicts() == []


def test_three_way_conflict_reports_every_pair(household):
    for name in ("A", "B", "C"):
        add(household, "Mochi", name, "09:00")
    assert len(Scheduler(household).detect_conflicts()) == 3


# ----- Next available slot --------------------------------------------------

def test_next_slot_skips_gaps_that_are_too_small(household):
    add(household, "Mochi", "Walk", "07:00", duration=30)       # busy 07:00-07:30
    add(household, "Luna", "Breakfast", "07:45", duration=15)   # 15-min gap before this
    assert Scheduler(household).find_next_available_slot(30, on=DAY) == "08:00"


def test_next_slot_on_empty_day_is_day_start(household):
    assert Scheduler(household).find_next_available_slot(60, on=DAY, day_start="06:30") == "06:30"


def test_next_slot_returns_none_when_day_is_full(household):
    add(household, "Mochi", "All day", "07:00", duration=15 * 60)
    assert Scheduler(household).find_next_available_slot(10, on=DAY) is None


# ----- Time-budget plan -----------------------------------------------------

def test_plan_day_keeps_high_priority_and_skips_what_does_not_fit(household):
    add(household, "Mochi", "Walk", "08:00", duration=30, priority="high")
    add(household, "Luna", "Play", "07:00", duration=40, priority="low")
    add(household, "Luna", "Meds", "12:00", duration=5, priority="high")
    plan = Scheduler(household).plan_day(available_minutes=40, on=DAY)
    assert [t.description for t in plan.scheduled] == ["Walk", "Meds"]  # time order
    assert [t.description for t in plan.skipped] == ["Play"]
    assert plan.minutes_used == 35
    assert "skipped" in plan.reason_for(plan.skipped[0])


# ----- Persistence ----------------------------------------------------------

def test_save_and_load_json_round_trip(household, tmp_path):
    walk = add(household, "Mochi", "Walk", "08:00", 30, "high", "daily")
    walk.mark_complete()
    path = tmp_path / "data.json"
    household.save_to_json(path)

    loaded = Owner.load_from_json(path)
    task = loaded.get_pet("Mochi").tasks[0]
    assert loaded.name == "Jordan" and [p.name for p in loaded.pets] == ["Mochi", "Luna"]
    assert (task.time, task.priority, task.frequency, task.due_date, task.completed, task.pet_name) == (
        "08:00", Priority.HIGH, "daily", DAY, True, "Mochi"
    )


def test_load_missing_json_returns_none(tmp_path):
    assert Owner.load_from_json(tmp_path / "nope.json") is None


def test_completing_twice_does_not_duplicate_next_occurrence(household):
    walk = add(household, "Mochi", "Walk", "08:00", frequency="daily")
    scheduler = Scheduler(household)
    scheduler.mark_task_complete(walk)
    assert scheduler.mark_task_complete(walk) is None
    assert household.get_pet("Mochi").task_count() == 2


def test_remove_task_removes_only_that_object():
    pet = Pet("Mochi", "dog")
    first, twin = Task("Walk", "08:00"), Task("Walk", "08:00")
    pet.add_task(first)
    pet.add_task(twin)
    pet.remove_task(twin)
    assert pet.tasks == [first] and pet.tasks[0] is first
