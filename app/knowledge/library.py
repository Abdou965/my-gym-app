"""Joins the seed exercise table (seed_data._E) with the technique guides
so routes can look an exercise up by key or by its database name."""
from app.seed_data import _E
from app.knowledge.exercises import GUIDES
from app.knowledge.programs import canonical_muscles
from app.knowledge.references import resolve

# فئات الفلترة في واجهة المكتبة
CATEGORIES = [
    ("chest", "الصدر", ["الصدر"]),
    ("back", "الظهر", ["الظهر", "الترابيس"]),
    ("shoulders", "الكتف", ["الكتف الأمامي", "الكتف الجانبي", "الكتف الخلفي"]),
    ("arms", "الذراعان", ["البايسبس", "الترايسبس", "الساعد"]),
    ("legs", "الأرجل", ["الأرباعية", "الخلفية (همسترينج)", "الأرداف", "السمانة", "المقرّبات"]),
    ("core", "البطن", ["البطن"]),
]


def _category(muscles: list[str]) -> str:
    for key, _, names in CATEGORIES:
        if any(m in names for m in muscles):
            return key
    return "other"


def _entry(key: str) -> dict:
    name, muscle, mn, mx, inc, tip = _E[key]
    muscles = canonical_muscles(muscle)
    return {
        "key": key, "name": name, "muscle_group": muscle, "muscles": muscles,
        "category": _category(muscles), "min_reps": mn, "max_reps": mx,
        "increment": inc, "tip": tip, "guide": GUIDES.get(key),
    }


NAME_TO_KEY = {v[0]: k for k, v in _E.items()}


def all_entries() -> list[dict]:
    return [_entry(k) for k in _E]


def get(key: str) -> dict | None:
    if key not in _E:
        return None
    e = _entry(key)
    if e["guide"]:
        e["refs"] = resolve(e["guide"].get("refs"))
    return e


def key_for_name(name: str) -> str | None:
    return NAME_TO_KEY.get(name)


def guide_for_name(name: str) -> dict | None:
    k = key_for_name(name)
    return GUIDES.get(k) if k else None
