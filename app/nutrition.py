"""Evidence-based nutrition planner.

Pipeline:  profile -> BMR -> TDEE -> goal calories -> macros -> meal split
-> a concrete one-day menu solved from the food table.

Rules and their sources (ids from app/knowledge/references.py):
  * BMR: Mifflin-St Jeor (mifflin1990); Katch-McArdle when body fat is
    known, since it uses lean mass directly.
  * Fat loss: 0.5–1.0 % of body weight per week; slower losses preserve
    lean mass and strength better (garthe2011, helms2014). The deficit is
    capped at 25 % of TDEE because large deficits blunt lean-mass gains
    (murphy2022).
  * Lean gain: 0.25–0.5 % of body weight per week (iraki2019).
  * Protein: ~1.6 g/kg is the meta-analytic plateau, 2.2 g/kg the upper
    CI (morton2018, jager2017); 2.2–2.6 g/kg in a deficit (helms2014).
  * Fat: 20–35 % of calories, never below 0.6 g/kg (thomas2016, helms2014).
  * Carbohydrate: the remaining energy (kerksick2018).
  * Protein per meal ~0.4 g/kg over 3–5 meals (schoenfeld2018meal); larger
    single doses are still used, just more slowly (trommelen2023).
  * Fibre 14 g per 1000 kcal; free sugars < 10 % of energy (who_sugar2015).
"""
from dataclasses import dataclass, field

from app.knowledge.foods import FOODS, macros as food_macros, SWAPS

KCAL_PER_KG = 7700  # تقريب الطاقة المخزنة في 1 كجم من نسيج الجسم

ACTIVITY = {
    "1.2": "مستقر: عمل مكتبي بلا رياضة",
    "1.375": "خفيف: تمرين 1–3 أيام أسبوعياً",
    "1.55": "معتدل: تمرين 3–5 أيام أسبوعياً",
    "1.725": "نشيط: تمرين 6–7 أيام أو عمل بدني",
    "1.9": "مكثف جداً: تدريب مرتين يومياً أو عمل شاق",
}

GOALS = {
    "cut": "خسارة دهون مع الحفاظ على العضل",
    "maintain": "ثبات الوزن / إعادة تشكيل الجسم",
    "bulk": "بناء عضل بأقل دهون (Lean bulk)",
}

# نسبة التغير الأسبوعي من وزن الجسم (%)
PACE = {
    "cut": {"slow": 0.5, "moderate": 0.7, "fast": 1.0},
    "bulk": {"slow": 0.15, "moderate": 0.25, "fast": 0.5},
    "maintain": {"slow": 0.0, "moderate": 0.0, "fast": 0.0},
}
PACE_LABELS = {"slow": "بطيء", "moderate": "متوسط (موصى به)", "fast": "سريع"}

PROTEIN_G_PER_KG = {"cut": 2.2, "maintain": 2.0, "bulk": 1.8}
FAT_SHARE = {"cut": 0.25, "maintain": 0.27, "bulk": 0.25}
MIN_FAT_G_PER_KG = 0.6


@dataclass
class Profile:
    weight: float
    height: float
    age: int
    sex: str = "m"            # m | f
    activity: float = 1.55
    goal: str = "maintain"    # cut | maintain | bulk
    pace: str = "moderate"    # slow | moderate | fast
    body_fat: float | None = None
    meals: int = 4            # 3..5
    diet: str = "omni"        # omni | veg (بيض وألبان)
    training_hour: str = "evening"  # morning | evening


@dataclass
class Plan:
    bmr: int
    bmr_method: str
    tdee: int
    calories: int
    protein: int
    fat: int
    carbs: int
    fiber: int
    water_l: float
    weekly_change_kg: float
    protein_per_meal: int
    notes: list = field(default_factory=list)
    meals: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    lean_mass: float | None = None


def bmr_mifflin(weight: float, height: float, age: int, sex: str) -> float:
    base = 10 * weight + 6.25 * height - 5 * age
    return base + 5 if sex == "m" else base - 161


def bmr_katch(lean_mass: float) -> float:
    return 370 + 21.6 * lean_mass


def _protein_reference_weight(p: Profile) -> float:
    """Protein is set per kg of body weight, but for people with high body
    fat that overshoots: use lean mass (÷0.85 to express it per 'lean-ish'
    weight) when body fat is known, else the weight at BMI 27."""
    if p.body_fat:
        return (p.weight * (1 - p.body_fat / 100)) / 0.85
    bmi = p.weight / (p.height / 100) ** 2
    if bmi > 30:
        return 27 * (p.height / 100) ** 2
    return p.weight


def compute(p: Profile) -> Plan:
    notes = []
    lean = None
    if p.body_fat and 3 <= p.body_fat <= 60:
        lean = p.weight * (1 - p.body_fat / 100)
        bmr = bmr_katch(lean)
        method = "Katch-McArdle (حسب الكتلة الخالية من الدهون)"
    else:
        bmr = bmr_mifflin(p.weight, p.height, p.age, p.sex)
        method = "Mifflin-St Jeor"
    tdee = bmr * p.activity

    rate = PACE.get(p.goal, PACE["maintain"]).get(p.pace, 0.0)
    delta = p.weight * rate / 100 * KCAL_PER_KG / 7  # سعرات يومية
    if p.goal == "cut":
        cap = tdee * 0.25
        if delta > cap:
            delta = cap
            notes.append("قُيّد العجز عند 25% من TDEE: العجز الأكبر يرتبط بفقدان أكبر للكتلة العضلية.")
        calories = tdee - delta
        floor = max(bmr, 1500 if p.sex == "m" else 1200)
        if calories < floor:
            calories = floor
            notes.append("رُفعت السعرات إلى الحد الأدنى الآمن؛ إن أردت عجزاً أكبر فزِد النشاط اليومي (المشي) بدل خفض الأكل.")
    elif p.goal == "bulk":
        calories = tdee + delta
    else:
        calories = tdee
    weekly_change = (calories - tdee) * 7 / KCAL_PER_KG

    ref_w = _protein_reference_weight(p)
    protein = PROTEIN_G_PER_KG.get(p.goal, 2.0) * ref_w
    fat = max(calories * FAT_SHARE.get(p.goal, 0.25) / 9, MIN_FAT_G_PER_KG * p.weight)
    carbs = (calories - protein * 4 - fat * 9) / 4
    if carbs < 50:
        carbs = 50
        notes.append("الكربوهيدرات عند حدها الأدنى (50 غ)؛ راقب أداءك في التمرين.")
    calories = protein * 4 + fat * 9 + carbs * 4  # إعادة ضبط بعد التقريب والحدود

    if carbs / p.weight < 3 and p.activity >= 1.55:
        notes.append("كربوهيدرات أقل من 3 غ/كجم: قد ينخفض أداء الحصص ذات الحجم العالي؛ ضع معظمها حول التمرين.")
    if p.goal == "bulk" and p.pace == "fast":
        notes.append("الزيادة السريعة تناسب المبتدئين أو النحفاء؛ المتقدمون يكسبون دهوناً أكثر بها.")

    fiber = calories / 1000 * 14
    # تقدير عام: ~35 مل/كجم + ~0.75 لتر لتعويض حصة تدريب مدتها ساعة، بسقف 4.5 لتر
    water = min(p.weight * 0.035 + 0.75, 4.5)
    meals = max(3, min(5, int(p.meals)))
    plan = Plan(
        bmr=round(bmr), bmr_method=method, tdee=round(tdee), calories=round(calories),
        protein=round(protein), fat=round(fat), carbs=round(carbs), fiber=round(fiber),
        water_l=round(water, 1), weekly_change_kg=round(weekly_change, 2),
        protein_per_meal=round(protein / meals), notes=notes,
        lean_mass=round(lean, 1) if lean else None,
    )
    plan.meals = build_menu(plan, meals, p.diet, p.training_hour)
    plan.totals = _sum_totals(plan.meals)
    return plan


# ── قائمة الطعام ─────────────────────────────────────────────
# كل وجبة: (اسم، أيقونة، حصة الكربوهيدرات النسبية، مصدر بروتين، كربوهيدرات، دهون، [إضافات ثابتة])
_OMNI = {
    "breakfast": ("الفطور", "🍳", 1.0, "egg_white", "oats", "almonds", [("egg", 100), ("fruit", 100)]),
    "lunch": ("الغداء", "🍗", 1.1, "chicken", "rice", "olive_oil", [("veg", 200)]),
    "snack": ("وجبة خفيفة", "🥣", 0.7, "greek_yogurt", "dates", "almonds", []),
    "pre": ("قبل التمرين (1–3 ساعات)", "⚡", 1.3, "tuna", "bread", "olive_oil", [("veg", 100)]),
    "post": ("بعد التمرين", "🔁", 1.3, "greek_yogurt", "banana", "peanut_butter", [("milk", 200)]),
    "dinner": ("العشاء", "🍽️", 0.8, "lean_beef", "potato", "olive_oil", [("veg", 200)]),
}
_VEG_SWAP = {"chicken": "tofu", "lean_beef": "cottage", "tuna": "egg_white", "salmon": "tofu"}
_VEG_EXTRA = {"lunch": [("lentils", 150)], "dinner": [("chickpeas", 100)]}

_ORDER = {
    3: ["breakfast", "lunch", "dinner"],
    4: {"morning": ["breakfast", "post", "lunch", "dinner"],
        "evening": ["breakfast", "lunch", "pre", "dinner"]},
    5: {"morning": ["pre", "post", "lunch", "snack", "dinner"],
        "evening": ["breakfast", "snack", "lunch", "pre", "post"]},
}


def _solve_meal(target: dict, prot: str, carb: str, fat: str, extras: list) -> list:
    """Find grams of the 3 variable foods so the meal (with its fixed
    extras) hits target p/c/f. Gauss-Seidel on a diagonally dominant
    3×3 system, clamped to >= 0 and rounded to 5 g."""
    base = {"p": 0.0, "c": 0.0, "f": 0.0}
    for k, g in extras:
        m = food_macros(k, g)
        for n in base:
            base[n] += m[n]
    need = {n: max(0.0, target[n] - base[n]) for n in base}
    per = {k: food_macros(k, 100) for k in (prot, carb, fat)}
    g = {prot: 0.0, carb: 0.0, fat: 0.0}
    for _ in range(60):
        g[prot] = max(0.0, (need["p"] - per[carb]["p"] * g[carb] / 100 - per[fat]["p"] * g[fat] / 100) / per[prot]["p"] * 100)
        g[carb] = max(0.0, (need["c"] - per[prot]["c"] * g[prot] / 100 - per[fat]["c"] * g[fat] / 100) / per[carb]["c"] * 100)
        g[fat] = max(0.0, (need["f"] - per[prot]["f"] * g[prot] / 100 - per[carb]["f"] * g[carb] / 100) / per[fat]["f"] * 100)
    items = [(k, gr) for k, gr in extras]
    for k in (prot, carb, fat):
        gr = round(g[k] / 5) * 5
        if gr >= 5:
            items.append((k, gr))
    return items


def build_menu(plan: Plan, meals: int, diet: str, training_hour: str) -> list:
    order = _ORDER[meals]
    if isinstance(order, dict):
        order = order.get(training_hour, order["evening"])
    shares = [_OMNI[m][2] for m in order]
    total_share = sum(shares)
    out = []
    for key, share in zip(order, shares):
        name, icon, _, prot, carb, fat, extras = _OMNI[key]
        extras = list(extras)
        if diet == "veg":
            prot = _VEG_SWAP.get(prot, prot)
            extras += _VEG_EXTRA.get(key, [])
        # البروتين موزع بالتساوي، والكربوهيدرات حسب أهمية الوجبة حول التمرين،
        # والدهون أقل قبل/بعد التمرين لتسريع الهضم.
        fat_w = 0.5 if key in ("pre", "post") else 1.0
        fat_total_w = sum(0.5 if k in ("pre", "post") else 1.0 for k in order)
        target = {"p": plan.protein / meals,
                  "c": plan.carbs * share / total_share,
                  "f": plan.fat * fat_w / fat_total_w}
        items = _solve_meal(target, prot, carb, fat, extras)
        rows, tot = [], {"p": 0.0, "c": 0.0, "f": 0.0, "kcal": 0.0}
        for k, gr in items:
            m = food_macros(k, gr)
            rows.append({"food": FOODS[k][0], "grams": int(gr), "kcal": round(m["kcal"]),
                         "p": round(m["p"]), "c": round(m["c"]), "f": round(m["f"])})
            for n in tot:
                tot[n] += m[n]
        out.append({"key": key, "name": name, "icon": icon, "items": rows,
                    "kcal": round(tot["kcal"]), "p": round(tot["p"]), "c": round(tot["c"]), "f": round(tot["f"])})
    return out


def _sum_totals(meals: list) -> dict:
    t = {"kcal": 0, "p": 0, "c": 0, "f": 0}
    for m in meals:
        for n in t:
            t[n] += m[n]
    return t


SUPPLEMENTS = [
    {"name": "كرياتين مونوهيدرات", "dose": "3–5 غ يومياً في أي وقت، بلا حاجة لمرحلة تحميل",
     "why": "أكثر مكمل مدعوم بالأدلة لزيادة القوة والكتلة العضلية، وآمن للأصحاء على المدى الطويل.",
     "refs": ["kreider2017"]},
    {"name": "كافيين", "dose": "3–6 ملغ/كجم قبل التمرين بـ 30–60 دقيقة (لا تتجاوز ~400 ملغ يومياً)",
     "why": "يحسّن الأداء والقدرة على التحمل والقوة؛ تجنبه قبل النوم بـ 6–8 ساعات.",
     "refs": ["guest2021"]},
    {"name": "بروتين Whey", "dose": "حسب الحاجة لإكمال البروتين اليومي (20–40 غ للحصة)",
     "why": "ليس ضرورياً إن كفى الطعام؛ مجرد وسيلة مريحة لبلوغ الهدف اليومي.",
     "refs": ["morton2018", "jager2017"]},
    {"name": "بروتين قبل النوم (كازين/زبادي/جبن قريش)", "dose": "30–40 غ",
     "why": "خيار مفيد لرفع البروتين اليومي ودعم التعافي الليلي.",
     "refs": ["snijders2019"]},
]

PRINCIPLES = [
    {"title": "السعرات تحدد اتجاه الوزن، والبروتين يحدد ما تخسره أو تكسبه",
     "body": "العجز أو الفائض في الطاقة يحدد تغير الوزن، بينما يحمي البروتين الكافي مع تمارين المقاومة الكتلة العضلية في العجز ويزيدها في الفائض.",
     "refs": ["helms2014", "morton2018"]},
    {"title": "سرعة التغيير المثالية",
     "body": "للتنشيف: 0.5–1% من وزن الجسم أسبوعياً؛ الأبطأ يحافظ على القوة والعضل أفضل. للضخامة النظيفة: 0.25–0.5% أسبوعياً.",
     "refs": ["garthe2011", "iraki2019"]},
    {"title": "توزيع البروتين",
     "body": "قسّم البروتين على 3–5 وجبات (~0.4 غ/كجم للوجبة). الجرعات الأكبر في وجبة واحدة ليست ضائعة، لكن التوزيع يسهّل بلوغ الهدف اليومي.",
     "refs": ["schoenfeld2018meal", "trommelen2023"]},
    {"title": "الكربوهيدرات وقود الأداء",
     "body": "ضع أكبر حصة كربوهيدرات في الوجبة قبل التمرين وبعده؛ تساعد على أداء المجموعات وإعادة ملء الجلايكوجين.",
     "refs": ["kerksick2018", "thomas2016"]},
    {"title": "الدهون للصحة الهرمونية",
     "body": "حافظ على 20–35% من السعرات من الدهون وبحد أدنى 0.6 غ/كجم، مع أولوية لزيت الزيتون والمكسرات والأسماك.",
     "refs": ["thomas2016", "helms2014"]},
    {"title": "الجودة الغذائية",
     "body": "ألياف ~14 غ لكل 1000 سعرة، 5 حصص خضار وفاكهة يومياً، وسكريات حرة أقل من 10% من الطاقة.",
     "refs": ["who_sugar2015"]},
    {"title": "راقب وعدّل",
     "body": "زن نفسك صباحاً 3–7 مرات أسبوعياً وقارن متوسط الأسبوع. إن لم يتغير المتوسط كما هو متوقع بعد أسبوعين، عدّل السعرات ±150–250.",
     "refs": ["helms2014"]},
]

ALL_SWAPS = SWAPS
