"""Database read/write operations used by the routes in main.py."""
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas, logic
from app.seed_data import PROGRAMS

DAYS_AR = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]


# ── SEEDING ──────────────────────────────────────────────
# أعمدة أُضيفت بعد الإصدار الأول: (جدول، عمود، نوع SQL). BOOLEAN DEFAULT FALSE
# يعمل على SQLite (3.23+) وPostgreSQL معاً.
_NEW_COLUMNS = [
    ("program_days", "is_cardio", "BOOLEAN DEFAULT FALSE"),
    ("program_days", "note", "TEXT DEFAULT ''"),
    ("program_day_exercises", "min_reps", "INTEGER"),
    ("program_day_exercises", "max_reps", "INTEGER"),
    ("program_day_exercises", "rest_min", "INTEGER"),
    ("program_day_exercises", "rest_max", "INTEGER"),
    ("program_day_exercises", "rir_target", "VARCHAR DEFAULT ''"),
    ("program_day_exercises", "note", "TEXT DEFAULT ''"),
]


def ensure_schema(engine):
    """Lightweight migration: create_all() never adds columns to existing
    tables, so add any column an older database is missing."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    for table, column, ddl in _NEW_COLUMNS:
        if table not in tables:
            continue
        if column not in {c["name"] for c in insp.get_columns(table)}:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def _get_or_create_exercise(db: Session, cache: dict, data: dict) -> models.Exercise:
    if data["name"] in cache:
        return cache[data["name"]]
    exist = db.query(models.Exercise).filter_by(name=data["name"]).first()
    if exist:
        cache[data["name"]] = exist
        return exist
    obj = models.Exercise(**data, is_custom=False)
    db.add(obj)
    db.flush()
    cache[data["name"]] = obj
    return obj


def _link_spec(item) -> tuple:
    """Normalise a seed entry: (exercise_dict, sets) or (exercise_dict, sets, overrides)."""
    ex_data, target_sets = item[0], item[1]
    o = item[2] if len(item) > 2 else {}
    return ex_data, target_sets, {
        "min_reps": o.get("min_reps"), "max_reps": o.get("max_reps"),
        "rest_min": o.get("rest_min"), "rest_max": o.get("rest_max"),
        "rir_target": o.get("rir_target", ""), "note": o.get("note", ""),
    }


def _fill_day_links(db: Session, cache: dict, day: models.ProgramDay, items: list):
    for ex_idx, item in enumerate(items):
        ex_data, target_sets, o = _link_spec(item)
        exercise = _get_or_create_exercise(db, cache, ex_data)
        db.add(models.ProgramDayExercise(
            day_id=day.id, exercise_id=exercise.id,
            order_index=ex_idx, target_sets=target_sets, **o,
        ))


def _create_program(db: Session, prog_data: dict, cache: dict) -> models.Program:
    program = models.Program(name=prog_data["name"])
    db.add(program)
    db.flush()
    for day_idx, day_data in enumerate(prog_data["days"]):
        day = models.ProgramDay(
            program_id=program.id, order_index=day_idx,
            name=day_data["name"], muscles=day_data["muscles"],
            is_rest=day_data["is_rest"], is_cardio=day_data.get("is_cardio", False),
            note=day_data.get("note", ""),
        )
        db.add(day)
        db.flush()
        _fill_day_links(db, cache, day, day_data["exercises"])
    return program


def _day_signature(day_name, muscles, is_rest, is_cardio, note, links) -> tuple:
    return (day_name, muscles or "", bool(is_rest), bool(is_cardio), note or "", tuple(links))


def sync_managed_programs(db: Session, cache: dict):
    """Bring programs flagged "managed" in seed_data in line with the file.

    Updates days IN PLACE (same ProgramDay ids, so workout history that
    points at them stays valid) and rewrites only the exercise links, and
    only when something actually differs. Other programs are never touched.
    """
    for prog_data in PROGRAMS:
        if not prog_data.get("managed"):
            continue
        program = db.query(models.Program).filter_by(name=prog_data["name"]).first()
        if not program:
            continue  # will be created by seed_if_empty
        days = list(program.days)
        if len(days) != len(prog_data["days"]):
            continue  # structure changed manually; leave it alone
        for day, d in zip(days, prog_data["days"]):
            want_links = []
            for item in d["exercises"]:
                ex_data, sets, o = _link_spec(item)
                want_links.append((ex_data["name"], sets, o["min_reps"], o["max_reps"],
                                   o["rest_min"], o["rest_max"], o["rir_target"], o["note"]))
            have_links = [(l.exercise.name, l.target_sets, l.min_reps, l.max_reps,
                           l.rest_min, l.rest_max, l.rir_target or "", l.note or "")
                          for l in day.exercises]
            want = _day_signature(d["name"], d["muscles"], d["is_rest"], d.get("is_cardio", False),
                                  d.get("note", ""), want_links)
            have = _day_signature(day.name, day.muscles, day.is_rest, day.is_cardio,
                                  day.note, have_links)
            if want == have:
                continue
            day.name, day.muscles = d["name"], d["muscles"]
            day.is_rest, day.is_cardio = d["is_rest"], d.get("is_cardio", False)
            day.note = d.get("note", "")
            for link in list(day.exercises):
                db.delete(link)
            db.flush()
            _fill_day_links(db, cache, day, d["exercises"])
    db.commit()


def seed_if_empty(db: Session):
    """Fresh DB: seed every program. Existing DB: add any program from
    seed_data that is missing by name (never deletes or edits old ones)."""
    cache: dict = {}
    existing = {name for (name,) in db.query(models.Program.name).all()}
    for prog_data in PROGRAMS:
        if prog_data["name"] not in existing:
            _create_program(db, prog_data, cache)
    db.commit()
    sync_managed_programs(db, cache)

    if not db.query(models.Settings).filter_by(id=1).first():
        first_program = db.query(models.Program).first()
        db.add(models.Settings(id=1, current_program_id=first_program.id, current_day_index=0))
        db.commit()


# ── SETTINGS / PROGRAM SELECTION ────────────────────────
def get_settings(db: Session) -> models.Settings:
    s = db.query(models.Settings).filter_by(id=1).first()
    if not s:
        first_program = db.query(models.Program).first()
        s = models.Settings(id=1, current_program_id=first_program.id if first_program else None,
                             current_day_index=0)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def get_all_programs(db: Session):
    return db.query(models.Program).all()


def set_current_program(db: Session, program_id: int):
    s = get_settings(db)
    s.current_program_id = program_id
    s.current_day_index = 0
    db.commit()


def set_current_day(db: Session, day_index: int):
    s = get_settings(db)
    s.current_day_index = day_index
    db.commit()


def get_current_program(db: Session) -> models.Program | None:
    s = get_settings(db)
    if s.current_program_id:
        return db.query(models.Program).get(s.current_program_id)
    return db.query(models.Program).first()


def get_current_day(db: Session) -> models.ProgramDay | None:
    program = get_current_program(db)
    if not program or not program.days:
        return None
    s = get_settings(db)
    idx = s.current_day_index % len(program.days)
    return program.days[idx]


def get_today_suggested_day(db: Session) -> models.ProgramDay | None:
    """Purely for the dashboard hero card: rotate by weekday, independent
    of whichever day the user has manually selected in the workout tab."""
    program = get_current_program(db)
    if not program or not program.days:
        return None
    weekday = datetime.now().weekday()  # Mon=0..Sun=6
    # convert to Sun=0..Sat=6 to match DAYS_AR ordering used elsewhere
    idx = (weekday + 1) % 7
    return program.days[idx % len(program.days)]


# ── EXERCISES ────────────────────────────────────────────
def get_all_exercises(db: Session):
    return db.query(models.Exercise).order_by(models.Exercise.name).all()


def get_custom_exercises(db: Session):
    return db.query(models.Exercise).filter_by(is_custom=True).all()


def add_custom_exercise(db: Session, data: schemas.ExerciseIn) -> models.Exercise:
    obj = models.Exercise(**data.model_dump(), is_custom=True)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_exercise(db: Session, exercise_id: int):
    obj = db.query(models.Exercise).get(exercise_id)
    if obj and obj.is_custom:
        db.delete(obj)
        db.commit()


# ── WORKOUTS / SESSIONS ──────────────────────────────────
def get_active_workout(db: Session) -> models.Workout | None:
    return db.query(models.Workout).filter_by(finished=False).order_by(
        models.Workout.id.desc()
    ).first()


def start_workout(db: Session, day_id: int) -> models.Workout:
    day = db.query(models.ProgramDay).get(day_id)
    if not day:
        raise ValueError("day not found")
    program = day.program
    workout = models.Workout(
        day_id=day.id, program_name=program.name, day_name=day.name, finished=False,
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


def get_workout(db: Session, workout_id: int) -> models.Workout | None:
    return db.query(models.Workout).get(workout_id)


def get_day_for_workout(db: Session, workout: models.Workout) -> models.ProgramDay | None:
    if workout.day_id:
        return db.query(models.ProgramDay).get(workout.day_id)
    return None


def _rir_gate(rir_target: str | None) -> int:
    """Highest RIR still accepted for a load increase: the upper bound of the
    exercise's target RIR (e.g. "1–3" -> 3). Falls back to 2."""
    import re
    nums = [int(n) for n in re.findall(r"\d+", rir_target or "")]
    return max(nums) if nums else 2


def _session_item(exercise: models.Exercise, target_sets: int, link=None) -> dict:
    g = (lambda attr: getattr(link, attr, None)) if link else (lambda attr: None)
    rest_min, rest_max = g("rest_min"), g("rest_max")
    return {
        "exercise": exercise,
        "target_sets": target_sets,
        "min_reps": g("min_reps") or exercise.min_reps,
        "max_reps": g("max_reps") or exercise.max_reps,
        "rest_min": rest_min, "rest_max": rest_max or rest_min,
        "rir_target": g("rir_target") or "",
        "note": g("note") or "",
    }


def get_session_exercise_list(db: Session, workout: models.Workout):
    """Ordered list of session items (exercise, target sets, rep range, rest,
    target RIR, note): the program day's exercises followed by any custom
    exercises the user has added (appended to every session, as in the
    original client-only version). Rep range / rest / RIR come from the
    program-day link when it overrides the exercise library defaults."""
    items = []
    day = get_day_for_workout(db, workout)
    if day:
        for link in day.exercises:
            items.append(_session_item(link.exercise, link.target_sets, link))
    for custom in get_custom_exercises(db):
        items.append(_session_item(custom, 3))
    return items


def log_set(db: Session, workout_id: int, data: schemas.SetLogIn) -> models.SetLog:
    existing = (
        db.query(models.SetLog)
        .filter_by(workout_id=workout_id, exercise_id=data.exercise_id, set_index=data.set_index)
        .first()
    )
    is_eff = logic.is_effective_set(data.rir)
    if existing:
        existing.weight = data.weight
        existing.reps = data.reps
        existing.rir = data.rir
        existing.is_effective = is_eff
        db.commit()
        db.refresh(existing)
        return existing
    obj = models.SetLog(
        workout_id=workout_id, exercise_id=data.exercise_id, set_index=data.set_index,
        weight=data.weight, reps=data.reps, rir=data.rir, is_effective=is_eff,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_set(db: Session, set_id: int):
    obj = db.query(models.SetLog).get(set_id)
    if obj:
        db.delete(obj)
        db.commit()


def get_sets_for_workout(db: Session, workout_id: int, exercise_id: int | None = None):
    q = db.query(models.SetLog).filter_by(workout_id=workout_id)
    if exercise_id:
        q = q.filter_by(exercise_id=exercise_id)
    return q.order_by(models.SetLog.set_index).all()


def finish_workout(db: Session, workout_id: int, data: schemas.FinishWorkoutIn) -> models.Workout:
    workout = db.query(models.Workout).get(workout_id)
    if not workout:
        raise ValueError("workout not found")
    sets = get_sets_for_workout(db, workout_id)
    workout.volume = sum((s.weight or 0) * (s.reps or 0) for s in sets)
    workout.duration_seconds = int((datetime.utcnow() - workout.date).total_seconds())
    # لا نمسح الجاهزية المسجّلة في بداية الجلسة إذا ترك المستخدم الحقل فارغاً
    if data.readiness_score is not None:
        workout.readiness_score = data.readiness_score
    workout.notes = data.notes
    workout.finished = True
    db.commit()
    db.refresh(workout)
    return workout


def get_recent_workouts(db: Session, limit: int = 30):
    return (
        db.query(models.Workout)
        .filter_by(finished=True)
        .order_by(models.Workout.date.desc())
        .limit(limit)
        .all()
    )


def get_last_finished_sets_for_exercise(db: Session, exercise_id: int, exclude_workout_id: int | None = None):
    """Sets from the most recent *finished* workout that touched this
    exercise — used both for the 'best previous' UI card and as the
    input to the double-progression suggestion."""
    q = (
        db.query(models.Workout)
        .join(models.SetLog)
        .filter(models.SetLog.exercise_id == exercise_id, models.Workout.finished == True)  # noqa: E712
    )
    if exclude_workout_id:
        q = q.filter(models.Workout.id != exclude_workout_id)
    workout = q.order_by(models.Workout.date.desc()).first()
    if not workout:
        return None, []
    sets = get_sets_for_workout(db, workout.id, exercise_id)
    return workout, sets


def get_streak(db: Session) -> int:
    workouts = get_recent_workouts(db, limit=200)
    days = {w.date.date() for w in workouts}
    streak = 0
    d = datetime.now().date()
    while d in days:
        streak += 1
        d -= timedelta(days=1)
    return streak


def get_dashboard_stats(db: Session) -> dict:
    workouts = db.query(models.Workout).filter_by(finished=True).all()
    total_sessions = len(workouts)
    total_volume = sum(w.volume or 0 for w in workouts)
    week_ago = datetime.utcnow() - timedelta(days=7)
    this_week = len([w for w in workouts if w.date >= week_ago])
    return {
        "sessions": total_sessions,
        "volume": total_volume,
        "week": this_week,
        "streak": get_streak(db),
    }


def get_weekly_effective_sets_by_muscle(db: Session) -> dict:
    """Effective (RIR<=3) sets per muscle group in the last 7 days —
    powers the small weekly-volume chart on the dashboard."""
    week_ago = datetime.utcnow() - timedelta(days=7)
    rows = (
        db.query(models.Exercise.muscle_group, models.SetLog.is_effective)
        .join(models.SetLog, models.SetLog.exercise_id == models.Exercise.id)
        .join(models.Workout, models.Workout.id == models.SetLog.workout_id)
        .filter(models.Workout.date >= week_ago, models.Workout.finished == True)  # noqa: E712
        .all()
    )
    counts = defaultdict(int)
    for muscle, is_eff in rows:
        if is_eff:
            counts[muscle or "أخرى"] += 1
    return dict(counts)


def get_1rm_history(db: Session, exercise_id: int, limit: int = 10):
    """Best estimated-1RM per finished workout for one exercise,
    oldest -> newest, for the progress chart."""
    workouts = (
        db.query(models.Workout)
        .join(models.SetLog)
        .filter(models.SetLog.exercise_id == exercise_id, models.Workout.finished == True)  # noqa: E712
        .order_by(models.Workout.date.desc())
        .limit(limit)
        .all()
    )
    points = []
    for w in reversed(workouts):
        sets = get_sets_for_workout(db, w.id, exercise_id)
        best = max(
            (logic.estimate_1rm_brzycki(s.weight, s.reps) for s in sets if s.weight and s.reps),
            default=0,
        )
        if best:
            points.append({"date": w.date.strftime("%Y-%m-%d"), "value": best})
    return points


def get_progression_suggestion(db: Session, exercise: models.Exercise,
                               readiness: int | None = None,
                               min_reps: int | None = None, max_reps: int | None = None,
                               rir_target: str | None = None) -> dict:
    """Double-progression suggestion, modulated by the session's readiness
    score (1-5). min/max reps and target RIR come from the program-day link
    when it overrides the exercise defaults."""
    _, sets = get_last_finished_sets_for_exercise(db, exercise.id)
    payload = [{"weight": s.weight, "reps": s.reps, "rir": s.rir, "is_effective": s.is_effective} for s in sets]
    return logic.next_session_suggestion(
        min_reps or exercise.min_reps, max_reps or exercise.max_reps,
        exercise.increment_weight, payload,
        readiness=readiness, rir_gate=_rir_gate(rir_target),
    )


def set_workout_readiness(db: Session, workout_id: int, score: int | None) -> models.Workout | None:
    """Store the pre-session readiness (1-5) on the active workout."""
    workout = db.query(models.Workout).get(workout_id)
    if not workout or workout.finished:
        return workout
    workout.readiness_score = score if score and 1 <= score <= 5 else None
    db.commit()
    db.refresh(workout)
    return workout


# ── BODY WEIGHT ──────────────────────────────────────────
def log_body_weight(db: Session, weight: float) -> models.BodyWeight:
    obj = models.BodyWeight(weight=weight)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_body_weights(db: Session, limit: int = 30):
    return db.query(models.BodyWeight).order_by(models.BodyWeight.date.desc()).limit(limit).all()
