"""FastAPI app: routes for the dashboard, workout builder, live session
tracker (HTMX partial updates), tools, and history."""
from datetime import datetime

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import crud, schemas, logic, models, nutrition
from app.knowledge import library, science, references, programs as kprograms

Base.metadata.create_all(bind=engine)
crud.ensure_schema(engine)  # يضيف أعمدة جديدة لقواعد SQLite القديمة

app = FastAPI(title="IronCore")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.utcnow
# دليل الأداء لأي تمرين من مكتبة البذور (None للتمارين المخصصة)
templates.env.globals["guide_for"] = library.guide_for_name
templates.env.globals["guide_key"] = library.key_for_name
templates.env.globals["refs"] = references.resolve


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
        tip=science.PRINCIPLES[datetime.now().timetuple().tm_yday % len(science.PRINCIPLES)],
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
def start_workout(day_id: int = Form(...), readiness: str = Form(""),
                  db: Session = Depends(get_db)):
    active = crud.get_active_workout(db)
    if active:
        return RedirectResponse(f"/session/{active.id}", status_code=303)
    day = db.query(models.ProgramDay).get(day_id)
    if not day or day.is_rest:
        return RedirectResponse("/workout?error=rest_day", status_code=303)
    if day.is_cardio:
        return RedirectResponse("/workout?error=cardio_day", status_code=303)
    workout = crud.start_workout(db, day_id)
    if readiness.strip().isdigit():
        crud.set_workout_readiness(db, workout.id, int(readiness))
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
    suggestion = crud.get_progression_suggestion(
        db, current["exercise"], readiness=workout.readiness_score,
        min_reps=current["min_reps"], max_reps=current["max_reps"], rir_target=current["rir_target"])
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
    suggestion = crud.get_progression_suggestion(
        db, current["exercise"], readiness=workout.readiness_score,
        min_reps=current["min_reps"], max_reps=current["max_reps"], rir_target=current["rir_target"])
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


@app.post("/session/{workout_id}/readiness")
def update_readiness(workout_id: int, score: int = Form(...), db: Session = Depends(get_db)):
    """Change today's readiness mid-session; the page reloads so every
    suggestion is recomputed with the new score."""
    crud.set_workout_readiness(db, workout_id, score)
    return RedirectResponse(f"/session/{workout_id}", status_code=303)


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


# ══════════════════════════════ GUIDE (المعرفة العلمية) ═════════════════
@app.get("/guide")
def guide_hub(request: Request, db: Session = Depends(get_db)):
    return render(
        request, "guide.html", db=db, active_page="guide",
        n_exercises=len(library.all_entries()), n_refs=len(references.REFS),
        n_principles=len(science.PRINCIPLES), n_programs=len(crud.get_all_programs(db)),
    )


@app.get("/guide/exercises")
def guide_exercises(request: Request, q: str = "", cat: str = "", db: Session = Depends(get_db)):
    return render(
        request, "guide_exercises.html", db=db, active_page="guide",
        entries=library.all_entries(), categories=library.CATEGORIES, q=q, cat=cat,
    )


@app.get("/guide/exercises/{key}")
def guide_exercise_detail(request: Request, key: str, db: Session = Depends(get_db)):
    entry = library.get(key)
    if not entry:
        return RedirectResponse("/guide/exercises", status_code=303)
    exercise = db.query(models.Exercise).filter_by(name=entry["name"]).first()
    used_in, history = [], []
    if exercise:
        seen = set()
        for link in exercise.day_links:
            label = (link.day.program.name, link.day.name)
            if label not in seen:
                seen.add(label)
                used_in.append({"program": label[0], "day": label[1], "sets": link.target_sets,
                                "reps": f"{link.reps_lo}–{link.reps_hi}", "rest": link.rest_text,
                                "rir": link.rir_target or ""})
        history = crud.get_1rm_history(db, exercise.id, limit=8)
    return render(
        request, "guide_exercise_detail.html", db=db, active_page="guide",
        e=entry, g=entry["guide"], used_in=used_in, history=history,
        best=max((h["value"] for h in history), default=0),
    )


@app.get("/guide/science")
def guide_science(request: Request, db: Session = Depends(get_db)):
    return render(request, "guide_science.html", db=db, active_page="guide",
                  principles=science.PRINCIPLES)


@app.get("/guide/programs")
def guide_programs(request: Request, db: Session = Depends(get_db)):
    current = crud.get_current_program(db)
    cards = []
    for p in crud.get_all_programs(db):
        info = kprograms.PROGRAM_INFO.get(p.name, {})
        low = kprograms.BEGINNER_LOW if info.get("level", "").startswith("مبتدئ") else kprograms.LOW
        cards.append({"program": p, "info": info,
                      "analysis": kprograms.analyze_program(p, low),
                      "current": bool(current and current.id == p.id)})
    # البرامج العلمية أولاً
    order = list(kprograms.PROGRAM_INFO)
    cards.sort(key=lambda c: order.index(c["program"].name) if c["program"].name in order else 99)
    return render(request, "guide_programs.html", db=db, active_page="guide",
                  cards=cards, low=kprograms.LOW, high=kprograms.HIGH)


@app.post("/guide/programs/{program_id}/use")
def guide_use_program(program_id: int, db: Session = Depends(get_db)):
    if db.query(models.Program).get(program_id):
        crud.set_current_program(db, program_id)
    return RedirectResponse("/workout", status_code=303)


@app.get("/guide/nutrition")
def guide_nutrition(request: Request, db: Session = Depends(get_db)):
    weights = crud.get_body_weights(db, limit=1)
    return render(
        request, "guide_nutrition.html", db=db, active_page="guide",
        last_weight=weights[0].weight if weights else None,
        activity=nutrition.ACTIVITY, goals=nutrition.GOALS, paces=nutrition.PACE_LABELS,
        principles=nutrition.PRINCIPLES, supplements=nutrition.SUPPLEMENTS, swaps=nutrition.ALL_SWAPS,
    )


def _num(v: str, cast=float, default=None):
    try:
        return cast(v) if str(v).strip() != "" else default
    except ValueError:
        return default


@app.post("/guide/nutrition/plan")
def guide_nutrition_plan(
    request: Request,
    weight: str = Form(""), height: str = Form(""), age: str = Form(""), sex: str = Form("m"),
    activity: str = Form("1.55"), goal: str = Form("maintain"), pace: str = Form("moderate"),
    body_fat: str = Form(""), meals: str = Form("4"), diet: str = Form("omni"),
    training_hour: str = Form("evening"),
):
    w, h, a = _num(weight), _num(height), _num(age, int)
    error = ""
    if not w or not (30 <= w <= 250):
        error = "أدخل وزناً بين 30 و 250 كجم."
    elif not h or not (120 <= h <= 230):
        error = "أدخل طولاً بين 120 و 230 سم."
    elif not a or not (14 <= a <= 90):
        error = "أدخل عمراً بين 14 و 90 سنة."
    if error:
        return templates.TemplateResponse(request, "components/nutrition_plan.html", {"error": error})
    prof = nutrition.Profile(
        weight=w, height=h, age=a, sex="f" if sex == "f" else "m",
        activity=_num(activity, float, 1.55) or 1.55,
        goal=goal if goal in nutrition.GOALS else "maintain",
        pace=pace if pace in nutrition.PACE_LABELS else "moderate",
        body_fat=_num(body_fat), meals=_num(meals, int, 4) or 4,
        diet="veg" if diet == "veg" else "omni",
        training_hour="morning" if training_hour == "morning" else "evening",
    )
    plan = nutrition.compute(prof)
    return templates.TemplateResponse(
        request, "components/nutrition_plan.html",
        {"error": "", "plan": plan, "profile": prof, "goal_label": nutrition.GOALS[prof.goal]},
    )
