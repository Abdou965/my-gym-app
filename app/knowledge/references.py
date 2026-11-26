"""Peer-reviewed sources cited across the app.

Every guide, principle and nutrition rule refers to these by id (e.g.
"schoenfeld2017vol"). The UI shows the short citation and a PubMed search
link built from the exact title, so each claim can be checked at the
source.
"""
from urllib.parse import quote_plus

REFS: dict[str, dict] = {
    # ── حجم التدريب والتكرار الأسبوعي ─────────────────────────
    "schoenfeld2017vol": {
        "cite": "Schoenfeld BJ, Ogborn D, Krieger JW. J Sports Sci. 2017;35(11):1073-1082",
        "title": "Dose-response relationship between weekly resistance training volume and increases in muscle mass: a systematic review and meta-analysis",
        "type": "تحليل تلوي",
    },
    "pelland2025": {
        "cite": "Pelland JC, Remmert JF, Robinson ZP, et al. Sports Med. 2025",
        "title": "The resistance training dose response: meta-regressions exploring the effects of weekly volume and frequency on muscle hypertrophy and strength gain",
        "type": "تحليل انحدار تلوي",
    },
    "schoenfeld2016freq": {
        "cite": "Schoenfeld BJ, Ogborn D, Krieger JW. Sports Med. 2016;46(11):1689-1697",
        "title": "Effects of resistance training frequency on measures of muscle hypertrophy: a systematic review and meta-analysis",
        "type": "تحليل تلوي",
    },
    # ── الشدة ونطاق التكرارات ──────────────────────────────────
    "schoenfeld2017load": {
        "cite": "Schoenfeld BJ, Grgic J, Ogborn D, Krieger JW. J Strength Cond Res. 2017;31(12):3508-3523",
        "title": "Strength and hypertrophy adaptations between low- vs. high-load resistance training: a systematic review and meta-analysis",
        "type": "تحليل تلوي",
    },
    # ── القرب من الفشل (RIR) ──────────────────────────────────
    "refalo2023": {
        "cite": "Refalo MC, Helms ER, Trexler ET, Hamilton DL, Fyfe JJ. Sports Med. 2023;53(3):649-665",
        "title": "Influence of resistance training proximity-to-failure on skeletal muscle hypertrophy: a systematic review with meta-analysis",
        "type": "تحليل تلوي",
    },
    "robinson2024": {
        "cite": "Robinson ZP, Pelland JC, Remmert JF, et al. Sports Med. 2024;54:2209-2231",
        "title": "Exploring the dose-response relationship between estimated resistance training proximity to failure, strength gain, and muscle hypertrophy: a series of meta-regressions",
        "type": "تحليل انحدار تلوي",
    },
    # ── الراحة بين المجموعات ──────────────────────────────────
    "schoenfeld2016rest": {
        "cite": "Schoenfeld BJ, Pope ZK, Benik FM, et al. J Strength Cond Res. 2016;30(7):1805-1812",
        "title": "Longer interset rest periods enhance muscle strength and hypertrophy in resistance-trained men",
        "type": "تجربة عشوائية",
    },
    "singer2024": {
        "cite": "Singer A, Wolf M, Generoso L, et al. Front Sports Act Living. 2024;6:1429789",
        "title": "Give it a rest: a systematic review with Bayesian meta-analysis on the effect of inter-set rest interval duration on muscle hypertrophy",
        "type": "تحليل تلوي بايزي",
    },
    # ── الإيقاع ومدى الحركة وطول العضلة ───────────────────────
    "schoenfeld2015tempo": {
        "cite": "Schoenfeld BJ, Ogborn DI, Krieger JW. Sports Med. 2015;45(4):577-585",
        "title": "Effect of repetition duration during resistance training on muscle hypertrophy: a systematic review and meta-analysis",
        "type": "تحليل تلوي",
    },
    "pedrosa2022": {
        "cite": "Pedrosa GF, Lima FV, Schoenfeld BJ, et al. Eur J Sport Sci. 2022;22(8):1250-1260",
        "title": "Partial range of motion training elicits favorable improvements in muscular adaptations when carried out at long muscle lengths",
        "type": "تجربة عشوائية",
    },
    "wolf2023rom": {
        "cite": "Wolf M, Androulakis-Korakakis P, Fisher J, Schoenfeld B, Steele J. Int J Strength Cond. 2023;3(1)",
        "title": "Partial vs full range of motion resistance training: a systematic review and meta-analysis",
        "type": "تحليل تلوي",
    },
    "maeo2021": {
        "cite": "Maeo S, Huang M, Wu Y, et al. Med Sci Sports Exerc. 2021;53(4):825-837",
        "title": "Greater hamstrings muscle hypertrophy but similar damage protection after training at long versus short muscle lengths",
        "type": "تجربة عشوائية",
    },
    "maeo2023": {
        "cite": "Maeo S, Wu Y, Huang M, et al. Eur J Sport Sci. 2023;23(7):1240-1250",
        "title": "Triceps brachii hypertrophy is substantially greater after elbow extension training performed in the overhead versus neutral arm position",
        "type": "تجربة عشوائية",
    },
    "kassiano2023": {
        "cite": "Kassiano W, Costa B, Kunevaliki G, et al. J Strength Cond Res. 2023;37(9):1746-1753",
        "title": "Greater gastrocnemius muscle hypertrophy after partial range of motion training performed at long muscle lengths",
        "type": "تجربة عشوائية",
    },
    "plotkin2023": {
        "cite": "Plotkin DL, Rodas MA, Vigotsky AD, et al. Front Physiol. 2023;14:1279170",
        "title": "Hip thrust and back squat training elicit similar gluteus muscle hypertrophy and transfer similarly to the deadlift",
        "type": "تجربة عشوائية",
    },
    # ── التدرج والتفريغ ───────────────────────────────────────
    "plotkin2022": {
        "cite": "Plotkin D, Coleman M, Van Every D, et al. PeerJ. 2022;10:e14142",
        "title": "Progressive overload without progressing load? The effects of load or repetition progression on muscular adaptations",
        "type": "تجربة عشوائية",
    },
    "coleman2024": {
        "cite": "Coleman M, Burke R, Augustin F, et al. PeerJ. 2024;12:e16777",
        "title": "Gaining more from doing less? The effects of a one-week deload period during supervised resistance training on muscular adaptations",
        "type": "تجربة عشوائية",
    },
    # ── التقنية والأمان ───────────────────────────────────────
    "hackett2013": {
        "cite": "Hackett DA, Chow CM. J Strength Cond Res. 2013;27(8):2338-2345",
        "title": "The Valsalva maneuver: its effect on intra-abdominal pressure and safety issues during resistance exercise",
        "type": "مراجعة",
    },
    "keogh2017": {
        "cite": "Keogh JWL, Winwood PW. Sports Med. 2017;47(3):479-501",
        "title": "The epidemiology of injuries across the weight-training sports",
        "type": "مراجعة منهجية",
    },
    "fry2003": {
        "cite": "Fry AC, Smith JC, Schilling BK. J Strength Cond Res. 2003;17(4):629-633",
        "title": "Effect of knee position on hip and knee torques during the barbell squat",
        "type": "دراسة بيوميكانيكية",
    },
    "saraceni2020": {
        "cite": "Saraceni N, Kent P, Ng L, et al. J Orthop Sports Phys Ther. 2020;50(3):121-130",
        "title": "To flex or not to flex? Is there a relationship between lumbar spine flexion during lifting and low back pain? A systematic review with meta-analysis",
        "type": "تحليل تلوي",
    },
    "green2007": {
        "cite": "Green CM, Comfort P. Strength Cond J. 2007;29(5):10-14",
        "title": "The affect of grip width on bench press performance and risk of injury",
        "type": "مراجعة",
    },
    "lusk2010": {
        "cite": "Lusk SJ, Hale BD, Russell DM. J Strength Cond Res. 2010;24(7):1895-1900",
        "title": "Grip width and forearm orientation effects on muscle activity during the lat pull-down",
        "type": "دراسة EMG",
    },
    "nsca2016": {
        "cite": "Haff GG, Triplett NT (eds). Essentials of Strength Training and Conditioning. 4th ed. NSCA / Human Kinetics; 2016",
        "title": "Essentials of Strength Training and Conditioning",
        "type": "مرجع أكاديمي",
        "url": "https://www.nsca.com/education/books/essentials-of-strength-training-and-conditioning/",
    },
    # ── التنويع والتدريب المتزامن ─────────────────────────────
    "kassiano2022": {
        "cite": "Kassiano W, Nunes JP, Costa B, Ribeiro AS, Schoenfeld BJ, Cyrino ES. J Strength Cond Res. 2022",
        "title": "Does varying resistance exercises promote superior muscle hypertrophy and strength gains? A systematic review",
        "type": "مراجعة منهجية",
    },
    "schumann2022": {
        "cite": "Schumann M, Feuerbacher JF, Sünkeler M, et al. Sports Med. 2022;52(3):601-612",
        "title": "Compatibility of concurrent aerobic and strength training for skeletal muscle size and function: an updated systematic review and meta-analysis",
        "type": "تحليل تلوي",
    },
    "wilson2012": {
        "cite": "Wilson JM, Marin PJ, Rhea MR, et al. J Strength Cond Res. 2012;26(8):2293-2307",
        "title": "Concurrent training: a meta-analysis examining interference of aerobic and resistance exercises",
        "type": "تحليل تلوي",
    },
    # ── التغذية ───────────────────────────────────────────────
    "mifflin1990": {
        "cite": "Mifflin MD, St Jeor ST, Hill LA, et al. Am J Clin Nutr. 1990;51(2):241-247",
        "title": "A new predictive equation for resting energy expenditure in healthy individuals",
        "type": "دراسة تحقق",
    },
    "morton2018": {
        "cite": "Morton RW, Murphy KT, McKellar SR, et al. Br J Sports Med. 2018;52(6):376-384",
        "title": "A systematic review, meta-analysis and meta-regression of the effect of protein supplementation on resistance training-induced gains in muscle mass and strength in healthy adults",
        "type": "تحليل تلوي",
    },
    "jager2017": {
        "cite": "Jäger R, Kerksick CM, Campbell BI, et al. J Int Soc Sports Nutr. 2017;14:20",
        "title": "International Society of Sports Nutrition Position Stand: protein and exercise",
        "type": "موقف رسمي (ISSN)",
    },
    "schoenfeld2018meal": {
        "cite": "Schoenfeld BJ, Aragon AA. J Int Soc Sports Nutr. 2018;15:10",
        "title": "How much protein can the body use in a single meal for muscle-building? Implications for daily protein distribution",
        "type": "مراجعة",
    },
    "trommelen2023": {
        "cite": "Trommelen J, van Lieshout GAA, Nyakayiru J, et al. Cell Rep Med. 2023;4(12):101324",
        "title": "The anabolic response to protein ingestion during recovery from exercise has no upper limit in magnitude and duration in vivo in humans",
        "type": "تجربة سريرية",
    },
    "helms2014": {
        "cite": "Helms ER, Aragon AA, Fitschen PJ. J Int Soc Sports Nutr. 2014;11:20",
        "title": "Evidence-based recommendations for natural bodybuilding contest preparation: nutrition and supplementation",
        "type": "مراجعة",
    },
    "iraki2019": {
        "cite": "Iraki J, Fitschen P, Espinar S, Helms E. Sports (Basel). 2019;7(7):154",
        "title": "Nutrition recommendations for bodybuilders in the off-season: a narrative review",
        "type": "مراجعة",
    },
    "garthe2011": {
        "cite": "Garthe I, Raastad T, Refsnes PE, et al. Int J Sport Nutr Exerc Metab. 2011;21(2):97-104",
        "title": "Effect of two different weight-loss rates on body composition and strength and power-related performance in elite athletes",
        "type": "تجربة عشوائية",
    },
    "murphy2022": {
        "cite": "Murphy C, Koehler K. Scand J Med Sci Sports. 2022;32(1):125-137",
        "title": "Energy deficiency impairs resistance training gains in lean mass but not strength: a meta-analysis and meta-regression",
        "type": "تحليل تلوي",
    },
    "thomas2016": {
        "cite": "Thomas DT, Erdman KA, Burke LM. Med Sci Sports Exerc. 2016;48(3):543-568",
        "title": "American College of Sports Medicine Joint Position Statement. Nutrition and Athletic Performance",
        "type": "موقف رسمي (ACSM)",
    },
    "kerksick2018": {
        "cite": "Kerksick CM, Wilborn CD, Roberts MD, et al. J Int Soc Sports Nutr. 2018;15:38",
        "title": "ISSN exercise & sports nutrition review update: research & recommendations",
        "type": "موقف رسمي (ISSN)",
    },
    "kreider2017": {
        "cite": "Kreider RB, Kalman DS, Antonio J, et al. J Int Soc Sports Nutr. 2017;14:18",
        "title": "International Society of Sports Nutrition position stand: safety and efficacy of creatine supplementation in exercise, sport, and medicine",
        "type": "موقف رسمي (ISSN)",
    },
    "guest2021": {
        "cite": "Guest NS, VanDusseldorp TA, Nelson MT, et al. J Int Soc Sports Nutr. 2021;18:1",
        "title": "International Society of Sports Nutrition position stand: caffeine and exercise performance",
        "type": "موقف رسمي (ISSN)",
    },
    "snijders2019": {
        "cite": "Snijders T, Trommelen J, Kouw IWK, et al. Front Nutr. 2019;6:17",
        "title": "The impact of pre-sleep protein ingestion on the skeletal muscle adaptive response to exercise in humans: an update",
        "type": "مراجعة",
    },
    "knowles2018": {
        "cite": "Knowles OE, Drinkwater EJ, Urwin CS, et al. J Sci Med Sport. 2018;21(9):959-968",
        "title": "Inadequate sleep and muscle strength: implications for resistance training",
        "type": "مراجعة",
    },
    "usda_fdc": {
        "cite": "U.S. Department of Agriculture, Agricultural Research Service. FoodData Central",
        "title": "FoodData Central",
        "type": "قاعدة بيانات غذائية",
        "url": "https://fdc.nal.usda.gov/",
    },
    "who_sugar2015": {
        "cite": "World Health Organization. Guideline: Sugars intake for adults and children. Geneva: WHO; 2015",
        "title": "Guideline: sugars intake for adults and children",
        "type": "إرشاد رسمي (WHO)",
        "url": "https://www.who.int/publications/i/item/9789241549028",
    },
}


def ref_url(ref_id: str) -> str:
    r = REFS[ref_id]
    return r.get("url") or "https://pubmed.ncbi.nlm.nih.gov/?term=" + quote_plus(r["title"])


def resolve(ids) -> list[dict]:
    """[{id, cite, title, type, url}] for the given ids, skipping unknown ones."""
    out = []
    for rid in ids or []:
        if rid in REFS:
            out.append({"id": rid, **REFS[rid], "url": ref_url(rid)})
    return out
