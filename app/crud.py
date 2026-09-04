"""Database read/write operations used by the routes in main.py."""
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas, logic
from app.seed_data import PROGRAMS

DAYS_AR = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]


# ── SEEDING ──────────────────────────────────────────────
def seed_if_empty(db: Session):
    if db.query(models.Program).count() > 0:
        return
    exercise_cache = {}

    def get_or_create_exercise(data: dict) -> models.Exercise:
        if data["name"] in exercise_cache:
            return exercise_cache[data["name"]]
        exist = db.query(models.Exercise).filter_by(name=data["name"]).first()
        if exist:
            exercise_cache[data["name"]] = exist
            return exist
        obj = models.Exercise(**data, is_custom=False)
        db.add(obj)
        db.flush()
        exercise_cache[data["name"]] = obj
        return obj

    for prog_data in PROGRAMS:
        program = models.Program(name=prog_data["name"])
        db.add(program)
        db.flush()
        for day_idx, day_data in enumerate(prog_data["days"]):
            day = models.ProgramDay(
                program_id=program.id, order_index=day_idx,
                name=day_data["name"], muscles=day_data["muscles"],
                is_rest=day_data["is_rest"],
            )
            db.add(day)
            db.flush()
            for ex_idx, (ex_data, target_sets) in enumerate(day_data["exercises"]):
                exercise = get_or_create_exercise(ex_data)
                link = models.ProgramDayExercise(
                    day_id=day.id, exercise_id=exercise.id,
                    order_index=ex_idx, target_sets=target_sets,
                )
                db.add(link)

    db.commit()

    # default settings row pointing at the first program
    first_program = db.query(models.Program).first()
    settings = models.Settings(id=1, current_program_id=first_program.id, current_day_index=0)
    db.add(settings)
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


def get_session_exercise_list(db: Session, workout: models.Workout):
    """Ordered list of {exercise, target_sets} for a workout: the
    program day's exercises followed by any custom exercises the user
    has added (custom ones are appended to every session, as in the
    original client-only version)."""
    items = []
    day = get_day_for_workout(db, workout)
    if day:
        for link in day.exercises:
            items.append({"exercise": link.exercise, "target_sets": link.target_sets})
    for custom in get_custom_exercises(db):
        items.append({"exercise": custom, "target_sets": 3})
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


def get_progression_suggestion(db: Session, exercise: models.Exercise) -> dict:
    _, sets = get_last_finished_sets_for_exercise(db, exercise.id)
    payload = [{"weight": s.weight, "reps": s.reps, "rir": s.rir, "is_effective": s.is_effective} for s in sets]
    return logic.next_session_suggestion(
        exercise.min_reps, exercise.max_reps, exercise.increment_weight, payload
    )


# ── BODY WEIGHT ──────────────────────────────────────────
def log_body_weight(db: Session, weight: float) -> models.BodyWeight:
    obj = models.BodyWeight(weight=weight)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_body_weights(db: Session, limit: int = 30):
    return db.query(models.BodyWeight).order_by(models.BodyWeight.date.desc()).limit(limit).all()
