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


READINESS_LABELS = {
    1: "منهك جداً", 2: "متعب", 3: "عادي", 4: "جيد", 5: "ممتاز",
}

# حدّ الجاهزية الذي يُعتبر عنده التعافي ضعيفاً: لا زيادة أحمال، وتخفيف عند اللزوم
LOW_READINESS = 2
DELOAD_FACTOR = 0.925  # تخفيف ~7.5% من الحمل عند جاهزية منخفضة جداً


def _round_to_step(value: float, step: float) -> float:
    """Round a load to the nearest plate step (e.g. 2.5 kg)."""
    if step <= 0:
        return round(value, 1)
    return round(round(value / step) * step, 1)


def next_session_suggestion(
    min_reps: int,
    max_reps: int,
    increment_weight: float,
    last_sets: Iterable[dict],
    readiness: Optional[int] = None,
    rir_gate: int = 2,
) -> dict:
    """Double-progression decision, adjusted by today's readiness (1-5).

    last_sets: iterable of {"weight","reps","rir","is_effective"}.

    Base rule: if every effective set at the top weight met/exceeded
    max_reps AND RIR <= rir_gate (default 2, or unrecorded) -> bump the weight by
    increment_weight. Otherwise hold and chase reps first.

    Readiness modulation (None = no adjustment):
      * readiness <= 2 : never increase the load. If the progression
        criteria were met, postpone it; if readiness == 1, suggest a
        light deload (~7.5% lighter, one set fewer).
      * readiness >= 4 and the rep target was met, but RIR was 3:
        no change (RIR gate stays strict, readiness never loosens it).
    Returns {"action": increase|hold|deload, "message", "weight", "note"}.
    """
    effective = [s for s in last_sets if s.get("is_effective", True)]
    if not effective:
        return {"action": "hold", "message": "لا توجد بيانات كافية بعد.",
                "weight": None, "note": ""}

    top_weight = max(s["weight"] for s in effective)
    top_sets = [s for s in effective if s["weight"] == top_weight]

    hit_rep_target = all(s["reps"] >= max_reps for s in top_sets)
    # rir_gate: أعلى RIR مقبول للزيادة (الافتراضي 2؛ يُشتق من RIR المستهدف للتمرين)
    low_rir = all((s.get("rir") is None or s["rir"] <= rir_gate) for s in top_sets)
    ready_low = readiness is not None and readiness <= LOW_READINESS

    # 1) very low readiness -> light deload instead of pushing
    if readiness == 1 and top_weight > 0:
        light = _round_to_step(top_weight * DELOAD_FACTOR, increment_weight or 0.5)
        return {
            "action": "deload",
            "message": f"جاهزيتك منخفضة جداً اليوم: استخدم {light} كجم وأنقص مجموعة واحدة، ولا تقترب من الفشل.",
            "weight": light,
            "note": "التعافي أولاً — الجلسة الخفيفة أفضل من جلسة مُجهدة تُعطّل التقدم.",
        }

    # 2) criteria met, but tired -> postpone the increase
    if hit_rep_target and low_rir:
        if ready_low:
            return {
                "action": "hold",
                "message": f"حققت شروط الزيادة، لكن جاهزيتك منخفضة. ثبّت {top_weight} كجم اليوم وأجّل الرفع.",
                "weight": top_weight,
                "note": "ستُقترح الزيادة تلقائياً في أول جلسة بجاهزية جيدة.",
            }
        new_weight = round(top_weight + increment_weight, 1)
        return {
            "action": "increase",
            "message": f"عمل رائع! ارفع الوزن إلى {new_weight} كجم في هذه الجلسة.",
            "weight": new_weight,
            "note": "",
        }

    # 3) default: hold and add reps first
    note = "جاهزيتك منخفضة: اترك مجموعة أو اثنتين بـ RIR 3 بدل الفشل." if ready_low else ""
    return {
        "action": "hold",
        "message": f"ثبّت الوزن {top_weight} كجم وحاول الوصول لـ {max_reps} تكرار في كل مجموعة.",
        "weight": top_weight,
        "note": note,
    }
