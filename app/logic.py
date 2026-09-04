"""Core training-science calculations: 1RM estimation, effective-set
filtering, and the double-progression weight recommendation."""
from typing import Iterable, Optional


def estimate_1rm_brzycki(weight: float, reps: int) -> float:
    """Brzycki formula: 1RM = weight * 36 / (37 - reps).
    Accurate mainly for reps <= 10-12; reps is clamped to 1..36
    to keep the denominator positive."""
    if weight <= 0 or reps <= 0:
        return 0.0
    reps = min(reps, 36)
    return round(weight * 36 / (37 - reps), 1)


def is_effective_set(rir: Optional[int]) -> bool:
    """A set counts toward weekly hypertrophy volume when RIR <= 3.
    Sets with no RIR recorded are treated as effective by default
    (most users log RIR only on working sets, not warm-ups)."""
    if rir is None:
        return True
    return rir <= 3


def next_session_suggestion(
    min_reps: int,
    max_reps: int,
    increment_weight: float,
    last_sets: Iterable[dict],
) -> dict:
    """Double-progression decision for the next time this exercise
    is trained. last_sets: iterable of {"weight","reps","rir","is_effective"}.

    Rule: if every effective set met/exceeded max_reps AND RIR <= 2
    (or unrecorded), bump the top working weight by increment_weight.
    Otherwise, hold the weight and prompt the user to add reps first.
    """
    effective = [s for s in last_sets if s.get("is_effective", True)]
    if not effective:
        return {"action": "hold", "message": "لا توجد بيانات كافية بعد.", "weight": None}

    top_weight = max(s["weight"] for s in effective)
    top_sets = [s for s in effective if s["weight"] == top_weight]

    hit_rep_target = all(s["reps"] >= max_reps for s in top_sets)
    low_rir = all((s.get("rir") is None or s["rir"] <= 2) for s in top_sets)

    if hit_rep_target and low_rir:
        new_weight = round(top_weight + increment_weight, 1)
        return {
            "action": "increase",
            "message": f"عمل رائع! ارفع الوزن إلى {new_weight} كجم في الجلسة القادمة.",
            "weight": new_weight,
        }
    return {
        "action": "hold",
        "message": f"ثبّت الوزن {top_weight} كجم وحاول الوصول لـ {max_reps} تكرار في كل مجموعة.",
        "weight": top_weight,
    }
