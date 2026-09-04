"""FastAPI app: routes for the dashboard, workout builder, live session
tracker (HTMX partial updates), tools, and history."""
from datetime import datetime

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import crud, schemas, logic, models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IronCore")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.utcnow


@app.on_event("startup")
def startup():
    db = next(get_db())
    crud.seed_if_empty(db)


def render(request: Request, template: str, **ctx):
    active = crud.get_active_workout(ctx.get("db")) if ctx.get("db") else None
    ctx["active_workout"] = active
    return templates.TemplateResponse(request, template, ctx)


# ══════════════════════════════ DASHBOARD ══════════════════════════════
@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = crud.get_dashboard_stats(db)
    today_day = crud.get_today_suggested_day(db)
    recent = crud.get_recent_workouts(db, limit=1)
    weekly_muscle = crud.get_weekly_effective_sets_by_muscle(db)
    weights = crud.get_body_weights(db, limit=2)
    max_muscle_count = max(weekly_muscle.values()) if weekly_muscle else 1
    return render(
        request, "index.html", db=db, active_page="home",
        stats=stats, today_day=today_day, last_session=recent[0] if recent else None,
        weekly_muscle=weekly_muscle, max_muscle_count=max_muscle_count,
        weights=weights, today_label=crud.DAYS_AR[(datetime.now().weekday() + 1) % 7],
    )


@app.post("/weight")
def add_weight(request: Request, weight: float = Form(...), db: Session = Depends(get_db)):
    crud.log_body_weight(db, weight)
    weights = crud.get_body_weights(db, limit=2)
    return templates.TemplateResponse(
        request, "components/weight_preview.html", {"weights": weights}
    )


# ══════════════════════════════ WORKOUT BUILDER ═════════════════════════
@app.get("/workout")
def workout_page(request: Request, error: str = "", db: Session = Depends(get_db)):
    programs = crud.get_all_programs(db)
    program = crud.get_current_program(db)
    day = crud.get_current_day(db)
    custom_ex = crud.get_custom_exercises(db)
    return render(
        request, "workout.html", db=db, active_page="workout",
        programs=programs, program=program, day=day, error=error,
        day_index=crud.get_settings(db).current_day_index, custom_ex=custom_ex,
    )


@app.post("/workout/select-program")
def select_program(request: Request, program_id: int = Form(...), db: Session = Depends(get_db)):
    crud.set_current_program(db, program_id)
    program = crud.get_current_program(db)
    day = crud.get_current_day(db)
    return templates.TemplateResponse(
        request, "components/day_panel.html",
        {"program": program, "day": day, "day_index": 0}
    )


@app.post("/workout/select-day")
def select_day(request: Request, day_index: int = Form(...), db: Session = Depends(get_db)):
    crud.set_current_day(db, day_index)
    program = crud.get_current_program(db)
    day = crud.get_current_day(db)
    return templates.TemplateResponse(
        request, "components/day_panel.html",
        {"program": program, "day": day, "day_index": day_index}
    )


@app.post("/workout/start")
def start_workout(day_id: int = Form(...), db: Session = Depends(get_db)):
    active = crud.get_active_workout(db)
    if active:
        return RedirectResponse(f"/session/{active.id}", status_code=303)
    day = db.query(models.ProgramDay).get(day_id)
    if not day or day.is_rest:
        return RedirectResponse("/workout?error=rest_day", status_code=303)
    workout = crud.start_workout(db, day_id)
    return RedirectResponse(f"/session/{workout.id}", status_code=303)


@app.post("/exercises")
def add_exercise(
    request: Request,
    name: str = Form(...), muscle_group: str = Form(""),
    sets: int = Form(3), min_reps: int = Form(8), max_reps: int = Form(12),
    tip: str = Form(""), db: Session = Depends(get_db),
):
    data = schemas.ExerciseIn(
        name=name, muscle_group=muscle_group, min_reps=min_reps,
        max_reps=max_reps, tip=tip,
    )
    crud.add_custom_exercise(db, data)
    custom_ex = crud.get_custom_exercises(db)
    return templates.TemplateResponse(
        request, "components/custom_ex_list.html", {"custom_ex": custom_ex}
    )


@app.delete("/exercises/{exercise_id}")
def remove_exercise(request: Request, exercise_id: int, db: Session = Depends(get_db)):
    crud.delete_exercise(db, exercise_id)
    custom_ex = crud.get_custom_exercises(db)
    return templates.TemplateResponse(
        request, "components/custom_ex_list.html", {"custom_ex": custom_ex}
    )


# ══════════════════════════════ LIVE SESSION ═══════════════════════════
@app.get("/session/{workout_id}")
def session_page(request: Request, workout_id: int, ex: int = 0, db: Session = Depends(get_db)):
    workout = crud.get_workout(db, workout_id)
    if not workout or workout.finished:
        return RedirectResponse("/", status_code=303)
    items = crud.get_session_exercise_list(db, workout)
    if not items:
        return RedirectResponse("/workout", status_code=303)
    ex = max(0, min(ex, len(items) - 1))
    current = items[ex]
    sets = crud.get_sets_for_workout(db, workout_id, current["exercise"].id)
    prev_workout, prev_sets = crud.get_last_finished_sets_for_exercise(
        db, current["exercise"].id, exclude_workout_id=workout_id
    )
    suggestion = crud.get_progression_suggestion(db, current["exercise"])
    return render(
        request, "session.html", db=db, active_page="session",
        workout=workout, items=items, ex_index=ex, current=current,
        sets=sets, prev_workout=prev_workout, prev_sets=prev_sets, suggestion=suggestion,
    )


@app.get("/session/{workout_id}/exercise/{ex_index}")
def session_exercise_panel(request: Request, workout_id: int, ex_index: int, db: Session = Depends(get_db)):
    workout = crud.get_workout(db, workout_id)
    items = crud.get_session_exercise_list(db, workout)
    ex_index = max(0, min(ex_index, len(items) - 1))
    current = items[ex_index]
    sets = crud.get_sets_for_workout(db, workout_id, current["exercise"].id)
    prev_workout, prev_sets = crud.get_last_finished_sets_for_exercise(
        db, current["exercise"].id, exclude_workout_id=workout_id
    )
    suggestion = crud.get_progression_suggestion(db, current["exercise"])
    return templates.TemplateResponse(
        request, "components/exercise_panel.html",
        {"workout": workout, "items": items, "ex_index": ex_index, "current": current,
         "sets": sets, "prev_workout": prev_workout, "prev_sets": prev_sets, "suggestion": suggestion}
    )


@app.post("/session/{workout_id}/log-set")
def log_set(
    request: Request, workout_id: int,
    exercise_id: int = Form(...), set_index: int = Form(...),
    weight: float = Form(0), reps: int = Form(0), rir: str = Form(""),
    ex_index: int = Form(0),
    db: Session = Depends(get_db),
):
    rir_val = int(rir) if rir.strip() != "" else None
    data = schemas.SetLogIn(exercise_id=exercise_id, set_index=set_index, weight=weight, reps=reps, rir=rir_val)
    crud.log_set(db, workout_id, data)
    workout = crud.get_workout(db, workout_id)
    items = crud.get_session_exercise_list(db, workout)
    current = items[ex_index]
    sets = crud.get_sets_for_workout(db, workout_id, current["exercise"].id)
    prev_workout, prev_sets = crud.get_last_finished_sets_for_exercise(
        db, current["exercise"].id, exclude_workout_id=workout_id
    )
    return templates.TemplateResponse(
        request, "components/set_rows.html",
        {"workout": workout, "current": current, "sets": sets, "ex_index": ex_index,
         "prev_workout": prev_workout, "prev_sets": prev_sets}
    )


@app.post("/session/{workout_id}/add-set")
def add_set(
    request: Request, workout_id: int,
    exercise_id: int = Form(...), ex_index: int = Form(0),
    db: Session = Depends(get_db),
):
    sets = crud.get_sets_for_workout(db, workout_id, exercise_id)
    next_index = len(sets)
    last = sets[-1] if sets else None
    data = schemas.SetLogIn(
        exercise_id=exercise_id, set_index=next_index,
        weight=last.weight if last else 0, reps=last.reps if last else 0, rir=None,
    )
    crud.log_set(db, workout_id, data)
    workout = crud.get_workout(db, workout_id)
    items = crud.get_session_exercise_list(db, workout)
    current = items[ex_index]
    sets = crud.get_sets_for_workout(db, workout_id, exercise_id)
    prev_workout, prev_sets = crud.get_last_finished_sets_for_exercise(
        db, exercise_id, exclude_workout_id=workout_id
    )
    return templates.TemplateResponse(
        request, "components/set_rows.html",
        {"workout": workout, "current": current, "sets": sets, "ex_index": ex_index,
         "prev_workout": prev_workout, "prev_sets": prev_sets}
    )


@app.delete("/session/{workout_id}/set/{set_id}")
def delete_set(
    request: Request, workout_id: int, set_id: int,
    exercise_id: int = 0, ex_index: int = 0,
    db: Session = Depends(get_db),
):
    crud.delete_set(db, set_id)
    workout = crud.get_workout(db, workout_id)
    items = crud.get_session_exercise_list(db, workout)
    current = items[ex_index]
    sets = crud.get_sets_for_workout(db, workout_id, current["exercise"].id)
    prev_workout, prev_sets = crud.get_last_finished_sets_for_exercise(
        db, current["exercise"].id, exclude_workout_id=workout_id
    )
    return templates.TemplateResponse(
        request, "components/set_rows.html",
        {"workout": workout, "current": current, "sets": sets, "ex_index": ex_index,
         "prev_workout": prev_workout, "prev_sets": prev_sets}
    )


@app.post("/session/{workout_id}/finish")
def finish_workout(
    request: Request, workout_id: int,
    readiness_score: str = Form(""), notes: str = Form(""),
    db: Session = Depends(get_db),
):
    score = int(readiness_score) if readiness_score.strip() != "" else None
    data = schemas.FinishWorkoutIn(readiness_score=score, notes=notes)
    crud.finish_workout(db, workout_id, data)
    return RedirectResponse(f"/history/{workout_id}", status_code=303)


# ══════════════════════════════ TOOLS ═══════════════════════════════════
@app.get("/tools")
def tools_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "tools.html", db=db, active_page="tools")


@app.post("/tools/1rm")
def tool_1rm(request: Request, weight: float = Form(...), reps: int = Form(...)):
    orm = logic.estimate_1rm_brzycki(weight, reps)
    pcts = [(100, "1RM"), (95, "1–2"), (90, "3–4"), (85, "4–6"), (80, "6–8"), (75, "8–10"), (70, "10–12")]
    rows = [{"pct": p, "range": r, "value": round(orm * p / 100)} for p, r in pcts]
    return templates.TemplateResponse(request, "components/orm_result.html", {"orm": orm, "rows": rows})


# ══════════════════════════════ HISTORY ═════════════════════════════════
@app.get("/history")
def history_page(request: Request, db: Session = Depends(get_db)):
    workouts = crud.get_recent_workouts(db, limit=50)
    return render(request, "history.html", db=db, active_page="history", workouts=workouts)


@app.get("/history/{workout_id}")
def history_detail(request: Request, workout_id: int, db: Session = Depends(get_db)):
    workout = crud.get_workout(db, workout_id)
    items = crud.get_session_exercise_list(db, workout) if workout else []
    detail = []
    for item in items:
        sets = crud.get_sets_for_workout(db, workout_id, item["exercise"].id)
        if sets:
            detail.append({"exercise": item["exercise"], "sets": sets})
    return render(request, "history_detail.html", db=db, active_page="history", workout=workout, detail=detail)
