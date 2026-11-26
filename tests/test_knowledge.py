"""Checks for the evidence-based knowledge base and nutrition planner.
Run: python -m pytest -q"""
import os
import tempfile

import pytest

from app import nutrition
from app.seed_data import _E, PROGRAMS
from app.knowledge.exercises import GUIDES
from app.knowledge.references import REFS, resolve
from app.knowledge import science, programs as kprog

REQUIRED = {"target", "secondary", "level", "equipment", "setup", "eccentric", "concentric",
            "breathing", "tempo", "mistakes", "safety", "evidence", "alternatives", "refs"}


def test_every_exercise_has_a_complete_guide():
    assert set(GUIDES) == set(_E)
    for key, g in GUIDES.items():
        assert set(g) == REQUIRED, key
        assert g["setup"] and g["mistakes"] and g["safety"], key


def test_every_cited_reference_exists():
    ids = [r for g in GUIDES.values() for r in g["refs"]]
    ids += [r for p in science.PRINCIPLES for r in p["refs"]]
    ids += [r for p in kprog.PROGRAM_INFO.values() for r in p["refs"]]
    ids += [r for p in nutrition.PRINCIPLES + nutrition.SUPPLEMENTS for r in p["refs"]]
    missing = sorted(set(ids) - set(REFS))
    assert not missing, missing
    assert all(r["url"].startswith("https://") for r in resolve(list(REFS)))


def test_program_info_names_match_seed_programs():
    names = {p["name"] for p in PROGRAMS}
    assert set(kprog.PROGRAM_INFO) <= names


@pytest.mark.parametrize("goal", ["cut", "maintain", "bulk"])
@pytest.mark.parametrize("meals", [3, 4, 5])
@pytest.mark.parametrize("diet", ["omni", "veg"])
def test_menu_matches_macro_targets(goal, meals, diet):
    plan = nutrition.compute(nutrition.Profile(weight=80, height=178, age=28, goal=goal, meals=meals, diet=diet))
    assert len(plan.meals) == meals
    t = plan.totals
    assert abs(t["p"] - plan.protein) <= plan.protein * 0.08
    assert abs(t["c"] - plan.carbs) <= plan.carbs * 0.08
    assert abs(t["kcal"] - plan.calories) <= plan.calories * 0.08


def test_cut_rate_and_protein_are_in_evidence_ranges():
    plan = nutrition.compute(nutrition.Profile(weight=80, height=178, age=28, goal="cut"))
    loss_pct = -plan.weekly_change_kg / 80 * 100
    assert 0.4 <= loss_pct <= 1.0
    assert 1.6 * 80 <= plan.protein <= 2.6 * 80
    assert plan.fat >= 0.6 * 80


def test_deficit_never_exceeds_cap_or_drops_below_bmr():
    plan = nutrition.compute(nutrition.Profile(weight=130, height=170, age=45, sex="f",
                                               goal="cut", pace="fast", activity=1.2))
    assert plan.calories >= plan.bmr - 1
    assert plan.tdee - plan.calories <= plan.tdee * 0.25 + 1


def test_bulk_rate_is_lean():
    plan = nutrition.compute(nutrition.Profile(weight=70, height=175, age=22, goal="bulk"))
    gain_pct = plan.weekly_change_kg / 70 * 100
    assert 0.1 <= gain_pct <= 0.5


def test_canonical_muscles():
    assert kprog.canonical_muscles("صدر / تراي") == ["الصدر", "الترايسبس"]
    assert kprog.canonical_muscles("كتف جانبي") == ["الكتف الجانبي"]
    assert kprog.canonical_muscles("الكتف الأمامي، الترايسبس") == ["الكتف الأمامي", "الترايسبس"]


@pytest.fixture(scope="module")
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
    os.remove(path)


def test_guide_pages_render(client):
    for url in ["/", "/guide", "/guide/exercises", "/guide/science", "/guide/programs", "/guide/nutrition", "/tools"]:
        assert client.get(url).status_code == 200, url
    for key in _E:
        assert client.get(f"/guide/exercises/{key}").status_code == 200, key


def test_nutrition_plan_endpoint(client):
    r = client.post("/guide/nutrition/plan", data={"weight": "80", "height": "178", "age": "28", "goal": "cut"})
    assert r.status_code == 200 and "سعرة" in r.text
    r = client.post("/guide/nutrition/plan", data={"weight": "x", "height": "", "age": ""})
    assert r.status_code == 200 and "أدخل" in r.text
