"""Initial exercise library and program templates, migrated from the
original client-side (localStorage) version of IronCore. Each exercise
carries a target rep range so the double-progression engine in
logic.py has something to work against."""

# (name, muscle_group, min_reps, max_reps, increment_weight, tip)
_E = {
    "bench": ("Bench Press — بنش برس", "صدر", 6, 8, 2.5, "ثبّت كتفيك للخلف، قوس خفيف في أسفل الظهر"),
    "incline_db": ("Incline DB Press — مائل", "صدر علوي", 8, 12, 2.0, "زاوية 30–45°، تحكم في الهبوط"),
    "cable_fly": ("Cable Fly — فلاي كيبل", "صدر", 12, 15, 1.0, "ركّز على الانقباض الكامل"),
    "ohp": ("OHP — ضغط عسكري", "كتف أمامي", 6, 10, 2.5, "شدّ البطن، لا تقوس أسفل الظهر"),
    "lat_raise": ("Lateral Raise — رفع جانبي", "كتف جانبي", 15, 20, 1.0, "كوع خفيف الانحناء"),
    "tricep_push": ("Tricep Pushdown — تراي كيبل", "تراي", 10, 15, 1.0, "ثبّت الكوعين بجانب الجسم"),
    "oh_ext": ("Overhead Ext — تراي علوي", "تراي", 10, 15, 1.0, "كوع يشير للأعلى فقط"),
    "pullup": ("Pull-up / Lat Pulldown", "ظهر عريض", 6, 10, 2.0, "اجذب الكوعين للأسفل والخلف"),
    "bb_row": ("Barbell Row — سحب بار", "ظهر متوسط", 6, 8, 2.5, "ظهر مسطح موازٍ للأرض"),
    "seated_row": ("Seated Cable Row", "ظهر متوسط", 10, 12, 2.0, "اضغط لوحَي الكتف معاً"),
    "face_pull": ("Face Pull — فيس بول", "دالية خلفية", 15, 20, 1.0, "اسحب نحو الوجه"),
    "bb_curl": ("Barbell Curl — كيرل بار", "بايسبس", 8, 12, 1.0, "لا تأرجح الجسم"),
    "incline_curl": ("Incline DB Curl", "بايسبس", 10, 15, 1.0, "اطالة كاملة في الأسفل"),
    "squat": ("Squat — سكوات", "أرباعية / ردف", 6, 8, 2.5, "ركبة تتبع اتجاه الإصبع، عمق مناسب"),
    "rdl": ("Romanian Deadlift", "همسترينج / ردف", 8, 12, 2.5, "ظهر مسطح، دفع الوركين للخلف"),
    "leg_press": ("Leg Press — ليج برس", "أرباعية", 10, 15, 5.0, "لا تقفل الركبة في الأعلى"),
    "leg_curl": ("Leg Curl — كيرل ساق", "همسترينج", 10, 15, 2.0, "تحكم في الهبوط"),
    "leg_ext": ("Leg Extension — مد ساق", "أرباعية", 12, 20, 2.0, "اضغط في القمة ثانية كاملة"),
    "calf": ("Calf Raise — كالف", "ربلة", 15, 20, 2.0, "اطالة كاملة في الأسفل"),
    "incline_bb": ("Incline BB Press", "صدر علوي", 6, 8, 2.5, ""),
    "dips": ("Dips — ديبس", "صدر / تراي", 8, 12, 0.0, "أمل جسمك للأمام للتركيز على الصدر"),
    "pec_deck": ("Pec Deck / Butterfly", "صدر", 12, 15, 1.0, ""),
    "db_shoulder": ("DB Shoulder Press", "كتف", 8, 10, 1.0, ""),
    "cable_lat_raise": ("Cable Lateral Raise", "كتف جانبي", 15, 20, 1.0, ""),
    "skull": ("Skull Crushers — قاطعة", "تراي", 10, 12, 1.0, ""),
    "deadlift": ("Deadlift — ديدليفت", "ظهر كامل", 3, 6, 2.5, "الشكل الصحيح أولاً دائماً"),
    "chest_row": ("Chest Supported Row", "ظهر متوسط", 10, 12, 2.0, ""),
    "single_row": ("Single Arm DB Row", "ظهر عريض", 10, 12, 1.0, ""),
    "rear_delt": ("Rear Delt Fly", "دالية خلفية", 15, 20, 1.0, ""),
    "hammer_curl": ("Hammer Curl", "بايسبس", 10, 12, 1.0, ""),
    "preacher_curl": ("Preacher Curl", "بايسبس", 10, 15, 1.0, ""),
    "hack_squat": ("Hack Squat", "أرباعية", 8, 12, 2.5, ""),
    "bulgarian": ("Bulgarian Split Squat", "أرباعية / ردف", 10, 12, 1.0, "كل رجل على حدة"),
    "seated_leg_curl": ("Seated Leg Curl", "همسترينج", 12, 15, 2.0, ""),
    "hip_thrust": ("Hip Thrust — رفع الوركين", "ردف", 10, 15, 2.5, "اضغط الردف في القمة"),
    "plank": ("Plank — بلانك", "كور", 1, 1, 0.0, "بطن مشدود، جسم خط مستقيم (وقت بالثواني)"),
    "ab_wheel": ("Ab Wheel — عجلة البطن", "كور", 10, 15, 0.0, ""),
    "decline_press": ("Decline Press", "صدر سفلي", 10, 12, 2.0, ""),
    "shrugs": ("Shrugs — شراق", "شراوي", 10, 15, 2.5, ""),
    "front_raise": ("Front Raise", "كتف أمامي", 12, 15, 1.0, ""),
    "rear_delt_machine": ("Rear Delt Machine", "دالية خلفية", 15, 20, 2.0, ""),
    # ── إضافات "البرنامج المتقدم المخصص" ──
    "wrist_curl": ("Wrist Curl — ثني الرسغ", "سواعد", 12, 20, 1.0, "اسند الساعد على مقعد، حركة الرسغ فقط"),
    "rev_wrist_curl": ("Reverse Wrist Curl — رسغ عكسي", "سواعد", 12, 20, 1.0, "كفّ للأسفل، وزن خفيف وتحكم كامل"),
    "machine_chest_press": ("Machine Chest Press — ضغط صدر جهاز", "صدر", 8, 12, 2.5, ""),
    "reverse_pec_deck": ("Reverse Pec Deck — فراشة عكسية", "دالية خلفية", 12, 20, 2.5, ""),
    "ez_curl": ("EZ-Bar Curl — كيرل بار EZ", "بايسبس", 6, 10, 1.0, ""),
    "rope_pushdown": ("Rope Pushdown — دفع ترايسبس بالحبل", "ترايسبس", 8, 12, 1.0, ""),
    "single_cable_row": ("Single-Arm Cable Row — سحب كابل بذراع", "ظهر متوسط", 8, 12, 2.5, ""),
    "low_high_fly": ("Low-to-High Cable Fly — تفتيح كابل", "صدر علوي", 10, 15, 1.0, ""),
    "mg_pulldown": ("Medium-Grip Lat Pulldown — سحب علوي", "ظهر عريض", 8, 12, 2.5, ""),
    "machine_shoulder_press": ("Seated Machine Shoulder Press", "كتف أمامي", 8, 12, 2.5, ""),
    "reverse_cable_fly": ("Reverse Cable Fly — رفرفة خلفية كابل", "دالية خلفية", 12, 20, 1.0, ""),
    "adduction": ("Hip Adduction — تقريب الفخذ", "مقرّبات الفخذ", 12, 20, 2.5, ""),
    "abduction": ("Hip Abduction — فتح الورك", "ردف جانبي", 12, 20, 2.5, "ثبّت الحوض، اضغط للخارج ثم تحكم في العودة"),
    "seated_calf": ("Seated Calf Raise", "ربلة (سولياس)", 12, 20, 2.5, "ركبة بزاوية 90°، اطالة كاملة وتوقف ثانية في القمة"),
}


def ex(key):
    n, m, mn, mx, inc, tip = _E[key]
    return {"name": n, "muscle_group": m, "min_reps": mn, "max_reps": mx,
            "increment_weight": inc, "tip": tip}


PROGRAMS = [
    {
        "name": "PPL — Push/Pull/Legs",
        "days": [
            {"name": "Push — صدر، كتف، تراي", "muscles": "صدر / كتف / تراي", "is_rest": False,
             "exercises": [(ex("bench"), 4), (ex("incline_db"), 3), (ex("cable_fly"), 3),
                           (ex("ohp"), 4), (ex("lat_raise"), 4), (ex("tricep_push"), 3), (ex("oh_ext"), 3)]},
            {"name": "Pull — ظهر وبايسبس", "muscles": "ظهر / بايسبس", "is_rest": False,
             "exercises": [(ex("pullup"), 4), (ex("bb_row"), 4), (ex("seated_row"), 3),
                           (ex("face_pull"), 3), (ex("bb_curl"), 3), (ex("incline_curl"), 3)]},
            {"name": "Legs — أرجل كامل", "muscles": "أرباعية / همسترينج / ردف", "is_rest": False,
             "exercises": [(ex("squat"), 4), (ex("rdl"), 3), (ex("leg_press"), 3),
                           (ex("leg_curl"), 3), (ex("leg_ext"), 3), (ex("calf"), 4)]},
            {"name": "Push 2 — إعادة", "muscles": "صدر / كتف / تراي", "is_rest": False,
             "exercises": [(ex("incline_bb"), 4), (ex("dips"), 3), (ex("pec_deck"), 3),
                           (ex("db_shoulder"), 4), (ex("cable_lat_raise"), 3), (ex("skull"), 3)]},
            {"name": "Pull 2 — إعادة", "muscles": "ظهر / بايسبس", "is_rest": False,
             "exercises": [(ex("deadlift"), 3), (ex("chest_row"), 3), (ex("single_row"), 3),
                           (ex("rear_delt"), 3), (ex("hammer_curl"), 3), (ex("preacher_curl"), 3)]},
            {"name": "Legs 2 + Core", "muscles": "أرجل / كور", "is_rest": False,
             "exercises": [(ex("hack_squat"), 4), (ex("bulgarian"), 3), (ex("seated_leg_curl"), 3),
                           (ex("hip_thrust"), 4), (ex("plank"), 3), (ex("ab_wheel"), 3)]},
            {"name": "🧘 راحة — Recovery", "muscles": "", "is_rest": True, "exercises": []},
        ],
    },
    {
        "name": "Upper/Lower (4 أيام)",
        "days": [
            {"name": "Upper A — علوي أ", "muscles": "صدر / ظهر / كتف / ذراع", "is_rest": False,
             "exercises": [(ex("bench"), 4), (ex("bb_row"), 4), (ex("ohp"), 3),
                           (ex("pullup"), 3), (ex("tricep_push"), 3), (ex("bb_curl"), 3)]},
            {"name": "Lower A — سفلي أ", "muscles": "أرجل", "is_rest": False,
             "exercises": [(ex("squat"), 4), (ex("rdl"), 3), (ex("leg_press"), 3),
                           (ex("leg_curl"), 3), (ex("calf"), 4)]},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
            {"name": "Upper B — علوي ب", "muscles": "صدر / ظهر / كتف", "is_rest": False,
             "exercises": [(ex("incline_db"), 4), (ex("pullup"), 4), (ex("db_shoulder"), 3),
                           (ex("seated_row"), 3), (ex("lat_raise"), 4), (ex("face_pull"), 3)]},
            {"name": "Lower B — سفلي ب", "muscles": "أرجل / كور", "is_rest": False,
             "exercises": [(ex("deadlift"), 3), (ex("hack_squat"), 3), (ex("hip_thrust"), 4),
                           (ex("leg_ext"), 3), (ex("plank"), 3)]},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
        ],
    },
    {
        "name": "Bro Split (5 أيام)",
        "days": [
            {"name": "الصدر — Chest", "muscles": "صدر", "is_rest": False,
             "exercises": [(ex("bench"), 5), (ex("incline_db"), 4), (ex("decline_press"), 3),
                           (ex("cable_fly"), 3), (ex("dips"), 3)]},
            {"name": "الظهر — Back", "muscles": "ظهر", "is_rest": False,
             "exercises": [(ex("deadlift"), 4), (ex("pullup"), 4), (ex("bb_row"), 4),
                           (ex("seated_row"), 3), (ex("face_pull"), 3)]},
            {"name": "الكتف — Shoulders", "muscles": "كتف", "is_rest": False,
             "exercises": [(ex("ohp"), 4), (ex("db_shoulder"), 3), (ex("lat_raise"), 5),
                           (ex("front_raise"), 3), (ex("rear_delt_machine"), 4), (ex("shrugs"), 3)]},
            {"name": "الأرجل — Legs", "muscles": "أرجل", "is_rest": False,
             "exercises": [(ex("squat"), 5), (ex("rdl"), 4), (ex("leg_press"), 3),
                           (ex("leg_curl"), 4), (ex("hip_thrust"), 3), (ex("calf"), 5)]},
            {"name": "الذراع — Arms", "muscles": "بايسبس / تراي", "is_rest": False,
             "exercises": [(ex("bb_curl"), 4), (ex("incline_curl"), 3), (ex("preacher_curl"), 3),
                           (ex("skull"), 4), (ex("tricep_push"), 3), (ex("hammer_curl"), 3)]},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
        ],
    },
    {
        "name": "Full Body (3 أيام)",
        "days": [
            {"name": "Full Body A", "muscles": "كامل الجسم", "is_rest": False,
             "exercises": [(ex("squat"), 3), (ex("bench"), 3), (ex("bb_row"), 3),
                           (ex("ohp"), 2), (ex("rdl"), 2), (ex("bb_curl"), 2), (ex("tricep_push"), 2)]},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
            {"name": "Full Body B", "muscles": "كامل الجسم", "is_rest": False,
             "exercises": [(ex("deadlift"), 3), (ex("incline_db"), 3), (ex("pullup"), 3),
                           (ex("db_shoulder"), 2), (ex("leg_press"), 2), (ex("hammer_curl"), 2), (ex("dips"), 2)]},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
            {"name": "Full Body C", "muscles": "كامل الجسم", "is_rest": False,
             "exercises": [(ex("hack_squat"), 3), (ex("dips"), 3), (ex("seated_row"), 3),
                           (ex("lat_raise"), 3), (ex("hip_thrust"), 3), (ex("face_pull"), 2), (ex("ab_wheel"), 3)]},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
            {"name": "🧘 راحة", "muscles": "", "is_rest": True, "exercises": []},
        ],
    },
]


# ── البرنامج المتقدم المخصص (وفق تقرير المختص، 4 نوفمبر 2026) ───────────
# الترتيب: الأحد..السبت (index 0 = الأحد) ليتوافق مع
# crud.get_today_suggested_day التي تُدوّر حسب يوم الأسبوع الفعلي.
# كل تمرين: lk(مفتاح, مجموعات, (أدنى, أعلى) تكرارات, (أدنى, أعلى) راحة بالثواني,
#              RIR المستهدف, ملاحظة تنفيذ). القيم تتجاوز قيم مكتبة التمارين لهذا
# البرنامج فقط، فلا تتأثر البرامج الأخرى التي تستخدم التمرين نفسه.
ADVANCED_PROGRAM_NAME = "البرنامج المتقدم المخصص"

RIR_MAIN = "1–3"    # المركبات الرئيسية
RIR_ISO = "1–2"     # الأجهزة والعزل
RIR_ARMS = "2–3"    # حصة الذراعين (تداخل مع حصتي الجزء العلوي)


def lk(key, sets, reps, rest, rir, note=""):
    return (ex(key), sets, {
        "min_reps": reps[0], "max_reps": reps[1],
        "rest_min": rest[0], "rest_max": rest[1],
        "rir_target": rir, "note": note,
    })


ADVANCED_PROGRAM = {
    "name": ADVANCED_PROGRAM_NAME,
    "managed": True,   # يُزامَن مع هذا الملف عند كل تشغيل (انظر crud.sync_managed_programs)
    "days": [
        {"name": "الأحد — الحصة A: صدر وظهر وكتف", "muscles": "صدر / ظهر / كتف",
         "is_rest": False,
         "note": "الهدف: أولوية للصدر العلوي وسماكة الظهر وعرضه مع الكتف الجانبي والخلفي. "
                 "الحجم المباشر: 16 مجموعة. لا ضغط كتف أمامي ثقيل اليوم لتجنب تكرار حمل الكتف الأمامي بعد الصدر.",
         "exercises": [
             lk("incline_db", 3, (6, 10), (120, 180), RIR_MAIN,
                "ميل المقعد 20–30° إن كان مريحاً للكتف، مع نزول متحكَّم به."),
             lk("chest_row", 3, (8, 12), (120, 120), RIR_MAIN,
                "ثبّت الجذع واسحب المرفقين للخلف دون اندفاع أو تقويس زائد."),
             lk("pullup", 3, (6, 10), (120, 120), RIR_MAIN,
                "عقلة بقبضة محايدة بوزن الجسم أو بوزن إضافي؛ السحب العلوي المحايد بديل إن تعذرت التقنية."),
             lk("machine_chest_press", 2, (8, 12), (90, 120), RIR_ISO),
             lk("cable_lat_raise", 3, (12, 20), (60, 90), RIR_ISO),
             lk("reverse_pec_deck", 2, (12, 20), (60, 90), RIR_ISO),
         ]},
        {"name": "الإثنين — بايسبس وترايسبس وسواعد", "muscles": "بايسبس / ترايسبس / سواعد",
         "is_rest": False,
         "note": "الهدف: ذراعان مباشرة مع مراعاة مشاركتهما في حصة الأحد والأربعاء. الحجم: 17 مجموعة "
                 "(بايسبس 7، ترايسبس 6، سواعد 4). معظم المجموعات بـ RIR 2–3 دون فشل متكرر؛ "
                 "عند ألم المرفق أو تراجع أداء الأربعاء راجع حجم الذراعين أولاً لا زيادة الجهد.",
         "exercises": [
             lk("ez_curl", 3, (6, 10), (90, 120), RIR_ARMS),
             lk("rope_pushdown", 3, (8, 12), (75, 90), RIR_ARMS),
             lk("incline_curl", 2, (10, 15), (75, 90), RIR_ARMS),
             lk("oh_ext", 3, (10, 15), (75, 90), RIR_ARMS),
             lk("hammer_curl", 2, (10, 15), (75, 90), RIR_ARMS),
             lk("wrist_curl", 2, (12, 20), (60, 60), RIR_ARMS,
                "راقب الرسغين والمرفقين؛ لا تستخدم أوزاناً تسبب ألماً."),
             lk("rev_wrist_curl", 2, (12, 20), (60, 60), RIR_ARMS,
                "كفّ للأسفل، وزن خفيف وتحكم كامل."),
         ]},
        {"name": "🧘 الثلاثاء — راحة وتعافٍ", "muscles": "", "is_rest": True,
         "note": "راحة من تمارين المقاومة. مشي خفيف أو حركات مرونة غير مرهقة عند الحاجة، "
                 "لاستعادة الأداء قبل الحصة B.",
         "exercises": []},
        {"name": "الأربعاء — الحصة B: صدر وظهر وكتف", "muscles": "صدر / ظهر / كتف",
         "is_rest": False,
         "note": "الهدف: استكمال الصدر والظهر بزوايا مختلفة عن الأحد مع ضغط كتف رأسي بجرعة محدودة. "
                 "الحجم المباشر: 17 مجموعة. الأحد + الأربعاء = صدر 10، ظهر 12، كتف أمامي/جانبي/خلفي 2/5/4 مجموعات مباشرة.",
         "exercises": [
             lk("bench", 3, (6, 10), (120, 180), RIR_MAIN,
                "ثبّت لوحتي الكتف واستخدم مدى حركة مريحاً دون ارتداد البار عن الصدر."),
             lk("single_cable_row", 3, (8, 12), (90, 120), RIR_MAIN,
                "امنع دوران الجذع للحصول على التكرار؛ البديل سحب كابل جالس بالذراعين."),
             lk("low_high_fly", 2, (10, 15), (60, 90), RIR_ISO),
             lk("mg_pulldown", 3, (8, 12), (90, 120), RIR_MAIN),
             lk("machine_shoulder_press", 2, (8, 12), (120, 120), RIR_ISO,
                "مجموعتان فقط: الكتف الأمامي شارك في ضغط الصدر، ولتقليل التداخل مع تعافي الذراعين."),
             lk("cable_lat_raise", 2, (12, 20), (60, 90), RIR_ISO),
             lk("reverse_cable_fly", 2, (12, 20), (60, 90), RIR_ISO),
         ]},
        {"name": "الخميس — أرجل وسمانة", "muscles": "فخذ أمامي / خلفي / ورك / سمانة",
         "is_rest": False,
         "note": "الهدف: الفخذ الأمامي والخلفي والورك ومبعدات ومقربات الفخذ والسمانة. الحجم: 21 مجموعة، "
                 "ويُستهدف إنجازها في 70–75 دقيقة بتنظيم العزل في أزواج. لا تختصر الراحة في الهاك سكوات "
                 "والرفعة الرومانية؛ وإن ضاق الوقت اخفض مجموعة أو مجموعتين من تمارين العزل.",
         "exercises": [
             lk("hack_squat", 3, (6, 10), (120, 180), RIR_MAIN,
                "ضبط العمق وفق قدرتك الحركية وأي أعراض بالركبة."),
             lk("rdl", 3, (6, 10), (120, 180), RIR_MAIN,
                "ظهر مسطح ودفع الوركين للخلف؛ المدى حسب مرونتك."),
             lk("leg_press", 2, (10, 15), (90, 120), RIR_ISO),
             lk("seated_leg_curl", 3, (10, 15), (90, 90), RIR_ISO,
                "بالتناوب مع مد الرجل لتوفير الوقت."),
             lk("leg_ext", 2, (12, 15), (60, 90), RIR_ISO),
             lk("abduction", 2, (12, 20), (60, 60), RIR_ISO,
                "بالتناوب مع تقريب الفخذ."),
             lk("adduction", 2, (12, 20), (60, 60), RIR_ISO),
             lk("calf", 2, (8, 12), (90, 90), RIR_ISO,
                "إطالة كاملة في الأسفل وتوقف ثانية في القمة."),
             lk("seated_calf", 2, (12, 20), (60, 90), RIR_ISO),
         ]},
        {"name": "🧘 الجمعة — راحة كاملة", "muscles": "", "is_rest": True,
         "note": "راحة كاملة. النوم والتغذية والتعافي قبل أسبوع جديد.",
         "exercises": []},
        {"name": "🏃‍♂️ السبت — كارديو", "muscles": "سباحة / جري / كرة قدم",
         "is_rest": False, "is_cardio": True,
         "note": "اختر نشاطاً واحداً معتدلاً: سباحة 30–40 دقيقة، أو جري 25–35 دقيقة، "
                 "أو كرة قدم 45–60 دقيقة. خفّف كرة القدم إن أثّرت في تعافي حصة الأرجل.",
         "exercises": []},
    ],
}

PROGRAMS.append(ADVANCED_PROGRAM)
