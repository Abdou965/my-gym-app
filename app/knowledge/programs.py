"""Program descriptions and the weekly-volume analysis shown in the guide.

analyze_program() counts, for every program in the database, the direct
working sets each muscle gets per week and rates them against the
evidence-based 10–20 sets range (schoenfeld2017vol, pelland2025).
"""
from collections import defaultdict

from app.seed_data import ADVANCED_PROGRAM_NAME, FULL_BODY_SCI_NAME, UPPER_LOWER_SCI_NAME

PROGRAM_INFO: dict[str, dict] = {
    FULL_BODY_SCI_NAME: {
        "level": "مبتدئ", "days": 3, "goal": "بناء أساس قوة وعضل وتعلّم الحركات",
        "who": "من يبدأ أو يعود بعد انقطاع، أو من لديه 3 أيام فقط.",
        "why": "كل عضلة تُدرَّب 3 مرات أسبوعياً بحجم ~9–12 مجموعة، مع تنويع الزوايا بين الأيام وراحة يوم بين الحصص.",
        "refs": ["schoenfeld2016freq", "schoenfeld2017vol", "refalo2023"],
    },
    UPPER_LOWER_SCI_NAME: {
        "level": "متوسط", "days": 4, "goal": "تضخم وقوة متوازنان",
        "who": "من تدرب 6–24 شهراً ويريد حجماً أعلى مع تعافٍ جيد.",
        "why": "تكرار مرتين أسبوعياً لكل عضلة، يوم قوة (5–10 تكرارات) ويوم تضخم (8–20)، وحجم 12–18 مجموعة لمعظم العضلات.",
        "refs": ["schoenfeld2016freq", "pelland2025", "maeo2021", "maeo2023"],
    },
    ADVANCED_PROGRAM_NAME: {
        "level": "متقدم", "days": 4, "goal": "أولوية الجزء العلوي والذراعين",
        "who": "متدرب متقدم يريد تركيزاً على الصدر العلوي والظهر والذراعين.",
        "why": "برنامج مخصص بأحجام محسوبة لكل عضلة، RIR مستهدف لكل فئة تمارين، وكارديو منفصل.",
        "refs": ["refalo2023", "singer2024"],
    },
    "PPL — Push/Pull/Legs": {
        "level": "متوسط–متقدم", "days": 6, "goal": "حجم تدريبي عالٍ",
        "who": "من يستطيع التدريب 6 أيام ويتعافى جيداً (نوم وتغذية ممتازان).",
        "why": "كل عضلة مرتين أسبوعياً بحجم عالٍ؛ يحتاج إدارة دقيقة للإرهاق.",
        "refs": ["schoenfeld2016freq", "pelland2025"],
    },
    "Upper/Lower (4 أيام)": {
        "level": "متوسط", "days": 4, "goal": "قوة وتضخم",
        "who": "متدرب متوسط بجدول 4 أيام.",
        "why": "تكرار مرتين أسبوعياً وبنية بسيطة.",
        "refs": ["schoenfeld2016freq"],
    },
    "Bro Split (5 أيام)": {
        "level": "متوسط", "days": 5, "goal": "تضخم بتركيز عضلة يومياً",
        "who": "من يفضّل التركيز على عضلة واحدة في الحصة.",
        "why": "كل عضلة مرة أسبوعياً فقط؛ الأدلة تفضّل مرتين أسبوعياً، لذا يُنصح بتوزيع الحجم أو التحول لبرنامج آخر.",
        "refs": ["schoenfeld2016freq"],
    },
    "Full Body (3 أيام)": {
        "level": "مبتدئ–متوسط", "days": 3, "goal": "لياقة عامة وقوة",
        "who": "من لديه وقت محدود.",
        "why": "تكرار عالٍ لكل عضلة بحجم معتدل.",
        "refs": ["schoenfeld2016freq"],
    },
}

# تحويل نص "العضلة" في مكتبة التمارين (أو العضلات المساعدة في الدليل) إلى مجموعات موحدة.
# الترتيب مهم: الأكثر تحديداً أولاً.
_MUSCLE_KEYS = [
    ("صدر", "الصدر"), ("ظهر", "الظهر"), ("لاتس", "الظهر"), ("معينية", "الظهر"),
    ("دالية خلفية", "الكتف الخلفي"), ("كتف الخلفي", "الكتف الخلفي"),
    ("كتف جانبي", "الكتف الجانبي"), ("كتف الجانبي", "الكتف الجانبي"),
    ("كتف أمامي", "الكتف الأمامي"), ("كتف الأمامي", "الكتف الأمامي"), ("كتف", "الكتف الأمامي"),
    ("تراي", "الترايسبس"), ("بايسبس", "البايسبس"), ("عضدية", "البايسبس"), ("أرباعية", "الأرباعية"),
    ("همسترينج", "الخلفية (همسترينج)"), ("ردف", "الأرداف"), ("أرداف", "الأرداف"), ("ألوية", "الأرداف"),
    ("ربلة", "السمانة"), ("سمانة", "السمانة"), ("سولياس", "السمانة"),
    ("كور", "البطن"), ("بطن", "البطن"), ("سواعد", "الساعد"), ("ساعد", "الساعد"),
    ("شراوي", "الترابيس"), ("ترابيس", "الترابيس"), ("مقرّبات", "المقرّبات"),
]

LOW, HIGH = 10, 20
BEGINNER_LOW = 6   # حتى الحجم المنخفض يعطي نمواً واضحاً لدى المبتدئين (pelland2025)
# عضلات لا تحتاج حجماً مباشراً مستقلاً عادةً (تُحفَّز من التمارين المركبة)
INFO_ONLY = ("أخرى", "البطن", "الساعد", "الترابيس", "المقرّبات")


def canonical_muscles(muscle_group: str) -> list[str]:
    out = []
    text = muscle_group or ""
    for key, name in _MUSCLE_KEYS:
        if key in text and name not in out:
            # "كتف" العامة لا تُضاف إن طابقت "كتف جانبي/أمامي/خلفي" مسبقاً
            if key == "كتف" and any(n.startswith("الكتف") for n in out):
                continue
            out.append(name)
    return out or ["أخرى"]


def _secondary_muscles(exercise_name: str, primary: list[str]) -> list[str]:
    """Secondary muscles from the technique guide (counted as half sets)."""
    from app.seed_data import _E
    from app.knowledge.exercises import GUIDES
    key = next((k for k, v in _E.items() if v[0] == exercise_name), None)
    g = GUIDES.get(key) if key else None
    if not g or not g.get("secondary"):
        return []
    return [m for m in canonical_muscles(g["secondary"]) if m not in primary and m != "أخرى"]


def analyze_program(program, low: int = LOW) -> dict:
    """Weekly sets per muscle for a models.Program: 1 per set for the
    exercise's primary muscles, 0.5 for its secondary muscles (fractional
    counting, as in the volume meta-regression of pelland2025)."""
    sets = defaultdict(float)
    training_days = 0
    for day in program.days:
        if day.is_rest or day.is_cardio:
            continue
        training_days += 1
        for link in day.exercises:
            primary = canonical_muscles(link.exercise.muscle_group)
            for m in primary:
                sets[m] += link.target_sets
            for m in _secondary_muscles(link.exercise.name, primary):
                sets[m] += link.target_sets * 0.5
    rows = []
    for m, n in sorted(sets.items(), key=lambda kv: -kv[1]):
        n = round(n * 2) / 2  # أقرب نصف مجموعة
        if m in INFO_ONLY:
            status = "info"
        elif n < low * 0.8:
            status = "low"
        elif n < low:
            status = "near"   # ضمن 20% من الحد الأدنى
        elif n <= HIGH:
            status = "ok"
        else:
            status = "high"
        rows.append({"muscle": m, "sets": n, "status": status})
    return {"rows": rows, "training_days": training_days, "low": low,
            "max": max([r["sets"] for r in rows], default=1)}
