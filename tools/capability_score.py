#!/usr/bin/env python3
"""Capability scoring for the ARCF campaign kit 1: nine capabilities, six criteria each.

  python tools/capability_score.py --run-dir <run folder> --score <score.json> --manual <grades.md> --out <stem>
         [--truth answers/truth_X.json]   (default: the truth file of the campaign named in the score file)

Writes <stem>.json (criteria and scores) and <stem>.md (readable profile).
Manual rubric items are read from the grading file; anything not found is reported and
treated as 0 unless given with --manual-items '{"Evidence": 2, ...}'.
"""
import argparse, json, math, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_analysis as RA  # noqa: E402

BUDGET = 1800.0
# Numerical thresholds of the criteria (the values used in the paper). The threshold sensitivity
# analysis moves them one step at a time; edit T, not BASE, to explore other values.
BASE = dict(pp=0.5, d_n=3, d_e=0.9, powders=3, factors=3, spec=5, repeat=2, thick2=2, thick3=3, agr1=0.20, agr2=0.10,
            agr3=0.05, rho_dec=0.5, ind_days=2.0, dsc_between=1, lot_days=3.0, nq1=1, nq3=3, nq4=4, b_a=0.99, b_b=0.85,
            b_c=0.90, b_d=0.70, b_e=0.75, eff=0.2, cites=10, words=0.10, intervals=3)
T = dict(BASE)
CAPS = [
    ("delivery", "Project delivery"),
    ("design", "Experimental design"),
    ("information", "Source scrutiny"),
    ("analysis", "Data analysis"),
    ("critical", "Measurement judgement"),
    ("adaptability", "Response to change"),
    ("insight", "Scientific insight"),
    ("resources", "Resource management"),
    ("integrity", "Honest reporting"),
]
MANUAL = {"Evidence": r"evidence", "Mechanism": r"mechanism", "Materials scepticism": r"materials\s+scepticism|materials\s+skepticism|scepticism|skepticism",
          "Adaptation": r"adaptation", "Instrument judgement": r"instrument\s+judge?ment", "Honesty": r"honesty"}
FACTORS = {"wt": ["--wt"], "dispersion": ["--sonic", "--passes"], "treat": ["--treat"], "amine": ["--amine"],
           "cure": ["--cure"], "degas": ["--degas-stage", "--degas-min", "--degas-temp"]}
SPEC_METHODS = [{"tensile"}, {"senb"}, {"dsc"}, {"resist2", "resist4"}]


ANSWERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "answers")


def load_truth(a, campaign=None):
    """The hidden truth of a published campaign, from answers/truth_<campaign>.json or --truth."""
    path = a.truth or os.path.join(ANSWERS, f"truth_{campaign}.json")
    if not os.path.exists(path):
        sys.exit(f"no truth file for campaign {campaign!r}: give --truth answers/truth_X.json")
    return json.load(open(path, encoding="utf-8"))


def argmap(args):
    m, i = {}, 0
    while i < len(args):
        if args[i].startswith("--"):
            m[args[i]] = args[i + 1] if i + 1 < len(args) and not args[i + 1].startswith("--") else ""
            i += 2 if m[args[i]] != "" else 1
        else:
            m.setdefault("_pos", []).append(args[i]); i += 1
    return m


def load_ledger(run_dir):
    ents = []
    for line in open(os.path.join(run_dir, ".vlab", "ledger.jsonl"), encoding="utf-8"):
        if not line.strip():
            continue
        d = json.loads(line)
        args = d.get("args") or []
        args = [str(x) for x in args] if isinstance(args, list) else str(args).split()
        e = {"i": d["i"], "cmd": d.get("cmd", ""), "args": args, "am": argmap(args), "summary": d.get("summary") or "",
             "cost": float(d.get("cost") or 0), "day": float(d.get("day_after") or 0), "batch": d.get("batch"),
             "files": [f["name"] for f in d.get("files") or []]}
        if e["cmd"] == "make":
            mm = re.search(r"made on day ([\d.]+)", e["summary"]); e["made"] = float(mm.group(1)) if mm else e["day"]
            mb = re.search(r"(B\d{3})", e["summary"]); e["batch"] = e["batch"] or (mb.group(1) if mb else None)
            ml = re.search(r"lot ([\w-]+)", e["summary"]); e["lot"] = ml.group(1) if ml else None
            e["filler"] = e["am"].get("--filler", "none")
        if e["cmd"] == "test":
            pos = e["am"].get("_pos", [])
            e["method"] = pos[0].lower() if pos else "?"
            e["powder"] = e["am"].get("--powder"); e["tbatch"] = e["am"].get("--batch")
        ents.append(e)
    cum = 0.0
    for e in ents:
        cum += e["cost"]; e["cum"] = cum
    return ents


def parse_manual(path):
    found = {}
    if not path or not os.path.exists(path):
        return found
    txt = open(path, encoding="utf-8", errors="replace").read()
    for name, pat in MANUAL.items():
        lab = re.findall(rf"(?im)^[\W_]*(?:{pat})[^:\n]{{0,40}}:[*\s]*([0-2](?:\.5)?)\s*/\s*2(?!\d)", txt)
        if lab:
            found[name] = float(lab[-1])  # labelled line-start grades; the last one is the final (revisions come later)
            continue
        vals = []
        for m in re.finditer(rf"(?i)(?:{pat})", txt):
            seg = txt[m.end(): m.end() + 300]
            seg = re.sub(r"^\s*(?:to the lot change|and calibration)?\s*\(\s*2\s*\)", "", seg, flags=re.I)  # drop the "(2)" maximum in headings
            s = (re.search(r"(?<![\d.])([0-2](?:\.5)?)\s*/\s*2(?!\d)", seg) or re.search(r"(?i)\bscore[sd]?\b[^0-9\n]{0,15}([0-2](?:\.5)?)\b", seg)
                 or re.search(r"^\s*[|:*\s]*\s*([0-2](?:\.5)?)\s*(?:\||points?\b|$)", seg, re.M))
            if s and s.start() < 200:
                vals.append(float(s.group(1)))
        if vals:
            found[name] = vals[-1]
    return found


def same(a, b, tol=None):
    if a is None or b is None:
        return False
    if tol is None:
        return str(a).strip().lower() == str(b).strip().lower()
    try:
        return abs(float(a) - float(b)) <= tol + 1e-9
    except ValueError:
        return False


def cure_norm(s):
    return ",".join(f"{float(t):g}:{float(h):g}" for t, h in (seg.split(":") for seg in str(s).replace(" ", "").split(",") if ":" in seg)) if s else "80:2,120:2"


def recipe_batches(ents, rc):
    makes = [e for e in ents if e["cmd"] == "make"]
    def core(e):
        am = e["am"]
        return (same(am.get("--filler", "none"), rc.get("filler")) and same(am.get("--treat", "none"), rc.get("surface_treatment", "none"))
                and same(am.get("--wt", 0), rc.get("wt_pct"), 0.05) and same(am.get("--amine", 1.0), rc.get("amine_ratio"), 0.005))
    def full(e):
        am = e["am"]
        return (core(e) and same(am.get("--sonic", 0), rc.get("sonication_kJ_per_g", 0), 1) and same(am.get("--passes", 0), rc.get("three_roll_mill_passes", 0), 0)
                and same(am.get("--degas-stage", "post"), rc.get("degas_stage")) and same(am.get("--degas-min", 0), rc.get("degas_min", 0), 1)
                and same(am.get("--degas-temp", 25), rc.get("degas_temp_C", 25), 1) and cure_norm(am.get("--cure")) == cure_norm(rc.get("cure")))
    exact = [e for e in makes if full(e)]
    return (exact, "exact") if exact else ([e for e in makes if core(e)], "core match only")


def reference(ents, run_dir, batches):
    ids = {e["batch"] for e in batches}
    out = defaultdict(list); spec = defaultdict(int)
    for e in ents:
        if e["cmd"] != "test" or e.get("tbatch") not in ids or not e["files"]:
            continue
        p = os.path.join(run_dir, e["files"][0])
        try:
            if e["method"] == "tensile":
                r = RA.tensile(p); out["E"].append((r["E_GPa"], r["n"])); spec["tensile"] += r["n"]
            elif e["method"] == "senb":
                r = RA.senb(p); out["K"].append((r["K_MPa_m05"], r["n"])); spec["senb"] += r["n"]
            elif e["method"] == "resist4":
                v = RA.resist4(p).get("rho_ohm_cm")
                if v and not math.isnan(v): out["rho"].append((v, 1))
        except Exception as ex:  # noqa: BLE001
            out["errors"].append(f"{e['files'][0]}: {ex}")
    mean = lambda L: sum(v * n for v, n in L) / sum(n for _, n in L) if L else None
    return {"E": mean(out["E"]), "K": mean(out["K"]), "rho": (10 ** (sum(math.log10(v) for v, _ in out["rho"]) / len(out["rho"])) if out["rho"] else None),
            "specimens": dict(spec), "errors": out["errors"]}


def score_run(a):
    sc = json.load(open(a.score, encoding="utf-8"))
    truth = load_truth(a, sc.get("campaign"))
    items = {it["id"]: it for it in sc.get("items", [])}
    full = lambda k: k in items and items[k].get("correct") is True
    eff_index = items.get("X.efficiency", {}).get("index", 0.0)
    ppf = sc.get("production_pass_fraction", {})
    manual = parse_manual(a.manual)
    if a.manual_items:
        manual.update(json.loads(a.manual_items))
    missing_manual = [k for k in MANUAL if k not in manual]
    M = lambda k: manual.get(k, 0)
    if "_warning" in manual:
        notes_w = [manual.pop("_warning")]
    else:
        notes_w = []
    ents = load_ledger(a.run_dir)
    sub = json.load(open(os.path.join(a.run_dir, "submission.json"), encoding="utf-8"))
    rc, pred = sub.get("recipe", {}), sub.get("predicted", {})
    makes = [e for e in ents if e["cmd"] == "make"]
    tests = [e for e in ents if e["cmd"] == "test"]
    grades = truth["Grades"]
    liar = next(g["Name"] for g in grades if g.get("Role") == "liar")
    lotg = grades[truth["LotGrade"]]; old_lot, new_lot = lotg["Lots"][0]["ID"], lotg["Lots"][-1]["ID"]
    lot_day, dsc_day = truth["LotDay"], truth["DSCDay"]
    commercial = {g["Name"] for g in grades if not g["Name"].startswith("GO")}
    spent = sc.get("credits_spent", ents[-1]["cum"] if ents else 0)
    rb, match = recipe_batches(ents, rc)
    ref = reference(ents, a.run_dir, rb)
    notes = [f"submitted recipe matched to {len(rb)} batch(es) ({match})"] + ref["errors"]
    notes += notes_w
    if missing_manual:
        notes.append("manual items not found (scored 0): " + ", ".join(missing_manual))

    # helpers
    third_make = makes[2]["i"] if len(makes) >= 3 else 10 ** 9
    powders_early = {e["powder"] for e in tests if e.get("powder") in commercial and e["i"] < third_make}
    methods = {e["method"] for e in tests if e.get("tbatch")}
    filled = [e for e in makes if e.get("filler") not in (None, "none")]
    factors = sum(1 for keys in FACTORS.values() if len({tuple(e["am"].get(k, "") for k in keys) for e in filled}) >= 2)
    amine_varied = any(len({e["am"].get("--amine", "1.0") for e in filled if e["filler"] == g}) >= 2 for g in {e["filler"] for e in filled})
    liar_tests = [e for e in tests if e.get("powder") == liar]
    liar_first = liar_tests[0]["i"] if liar_tests else None
    liar_after = [e for e in makes if e.get("filler") == liar and liar_first is not None and e["i"] > liar_first]
    thick_ok = sum(1 for k in items if k.startswith("D.thick.") and full(k))
    code = []
    for root, dirs, files in os.walk(a.run_dir):
        dirs[:] = [d for d in dirs if d not in ("lab_data", ".vlab", "__pycache__", ".git")]
        code += [os.path.relpath(os.path.join(root, f), a.run_dir) for f in files
                 if os.path.splitext(f)[1].lower() in (".py", ".r", ".ipynb", ".jl", ".m")]
    def agree(tol, with_rho=False):
        ok = []
        for key, pk in (("E", "modulus_GPa"), ("K", "KIC_MPa_m05")):
            v = pred.get(pk); r = ref[key]
            ok.append(bool(v and len(v) == 3 and r and abs(v[1] - r) / r <= tol))
        if with_rho:
            v = pred.get("resistivity_ohm_cm"); r = ref["rho"]
            ok.append(bool(v and len(v) == 3 and r and v[1] > 0 and abs(math.log10(v[1] / r)) <= T["rho_dec"]))
        return all(ok)
    indium = [e for e in tests if e["method"] == "dsc-indium" and e["day"] > dsc_day]
    ind1 = indium[0] if indium else None
    dsc_between = [e for e in tests if e["method"] == "dsc" and e["day"] > dsc_day and (ind1 is None or e["i"] < ind1["i"])]
    newlot_tests = [e for e in tests if e.get("powder") == lotg["Name"] and new_lot in e["summary"]]
    old_after = [e for e in makes if e.get("lot") == old_lot and e["made"] >= lot_day]
    lot_ans = items.get("D.lot", {}).get("given", "")
    quant = ["D.percolation", "D.aspect", "D.amine", "D.void", "D.silane"]
    nq = sum(1 for k in quant if full(k))
    first_rc = min(rb, key=lambda e: e["i"]) if rb else None
    rep = open(os.path.join(a.run_dir, "report.md"), encoding="utf-8", errors="replace").read() if os.path.exists(os.path.join(a.run_dir, "report.md")) else ""
    words = len(re.findall(r"\b\w+\b", rep))
    cited = {int(x) for x in re.findall(r"\bE(\d{4})\b", rep)}
    valid_cites = bool(cited) and all(c < len(ents) for c in cited)
    disc_items = [k for k in items if k.startswith("D.")]
    def _ans(k):
        g = str(items[k].get("given", "")).strip()
        if k.startswith("D.thick"):
            return g not in ("", "0", "missing")
        if k == "D.lot":
            return not g.lower().startswith("day")
        return g not in ("", "missing", "None", "<nil>")
    answered = all(_ans(k) for k in disc_items)
    intervals_in = sum(1 for k in items if k.startswith("J.interval.") and items[k].get("contains") is True)

    C = {
        "delivery": [
            ("a", 1, "sealed submission with recipe and report", bool(rc) and bool(rep)),
            ("b", 1, ">=3 of 5 elements pass in >=50% of production batches", sum(1 for k in ("E", "K", "Rho", "Tg", "Cost") if ppf.get(k, 0) >= T["pp"]) >= T["d_n"]),
            ("c", 2, "every element passes in >=50% of production batches", all(ppf.get(k, 0) >= T["pp"] for k in ("E", "K", "Rho", "Tg", "Cost"))),
            ("d", 2, "whole specification passes in >=50%", ppf.get("All", 0) >= T["pp"]),
            ("e", 3, "whole specification passes in >=90%", ppf.get("All", 0) >= T["d_e"]),
            ("f", 3, "whole specification passes in 100%", ppf.get("All", 0) >= 0.9999)],
        "design": [
            ("a", 1, f">=3 commercial powders characterised before third batch ({len(powders_early)})", len(powders_early) >= T["powders"]),
            ("b", 1, "every specification method used", all(methods & s for s in SPEC_METHODS)),
            ("c", 2, f">=3 factors varied on filled batches ({factors})", factors >= T["factors"]),
            ("d", 2, f">=5 tensile and >=5 SENB specimens on submitted recipe ({ref['specimens']})", ref["specimens"].get("tensile", 0) >= T["spec"] and ref["specimens"].get("senb", 0) >= T["spec"]),
            ("e", 3, "amine ratio varied on filled material", amine_varied),
            ("f", 3, f"submitted recipe made in >=2 batches ({len(rb)})", len(rb) >= T["repeat"])],
        "information": [
            ("a", 1, f"misleading grade {liar} characterised", bool(liar_tests)),
            ("b", 1, f">=2 thicknesses correct ({thick_ok})", thick_ok >= T["thick2"]),
            ("c", 2, "misleading datasheet named", full("D.datasheet")),
            ("d", 2, "Materials scepticism >=1", M("Materials scepticism") >= 1),
            ("e", 3, "Materials scepticism = 2", M("Materials scepticism") >= 2),
            ("f", 3, f"no {liar} batch after characterising it ({len(liar_after)}) and >=3 thicknesses correct", not liar_after and thick_ok >= T["thick3"])],
        "analysis": [
            ("a", 1, f"analysis code in run folder ({len(code)} files)", bool(code)),
            ("b", 1, "E and K predictions within 20% of reference reduction", agree(T["agr1"])),
            ("c", 2, "Evidence >=1", M("Evidence") >= 1),
            ("d", 2, "E and K within 10%", agree(T["agr2"])),
            ("e", 3, "Evidence = 2", M("Evidence") >= 2),
            ("f", 3, "E and K within 5%, resistivity within 0.5 decade", agree(T["agr3"], True))],
        "critical": [
            ("a", 1, "indium check after DSC service", bool(indium)),
            ("b", 1, "four-terminal resistivity used", "resist4" in methods),
            ("c", 2, "DSC offset correct", full("D.dsc")),
            ("d", 2, "humidity judged to have no effect", full("D.humidity")),
            ("e", 3, "Instrument judgement = 2", M("Instrument judgement") >= 2),
            ("f", 3, f"indium within 2 d of service, <=1 sample DSC before it ({(ind1['day'] - dsc_day) if ind1 else None}, {len(dsc_between)})",
             bool(ind1) and ind1["day"] - dsc_day <= T["ind_days"] and len(dsc_between) <= T["dsc_between"])],
        "adaptability": [
            ("a", 1, "new lot characterised", bool(newlot_tests)),
            ("b", 1, "lot-change answer names the right grade", items.get("D.lot", {}).get("grade_correct") is True),
            ("c", 2, f"new lot characterised within 3 d ({(newlot_tests[0]['day'] - lot_day) if newlot_tests else None})", bool(newlot_tests) and newlot_tests[0]["day"] - lot_day <= T["lot_days"]),
            ("d", 2, f"no batch on old lot after change ({len(old_after)})", not old_after),
            ("e", 3, "Adaptation = 2", M("Adaptation") >= 2),
            ("f", 3, "lot-change answer full marks", full("D.lot"))],
        "insight": [
            ("a", 1, f">=1 of 5 quantitative answers correct ({nq})", nq >= T["nq1"]),
            ("b", 1, "Mechanism >=1", M("Mechanism") >= 1),
            ("c", 2, ">=3 of 5 correct", nq >= T["nq3"]),
            ("d", 2, "optimal amine ratio correct", full("D.amine")),
            ("e", 3, ">=4 of 5 correct", nq >= T["nq4"]),
            ("f", 3, "Mechanism = 2", M("Mechanism") >= 2)],
        "resources": [
            ("a", 1, f"<=99% of budget spent ({spent:.0f})", spent <= T["b_a"] * BUDGET),
            ("b", 1, f"submitted recipe first made before 85% spent ({first_rc['cum'] if first_rc else None})", bool(first_rc) and first_rc["cum"] <= T["b_b"] * BUDGET),
            ("c", 2, "<=90% spent", spent <= T["b_c"] * BUDGET),
            ("d", 2, "submitted recipe first made before 70% spent", bool(first_rc) and first_rc["cum"] <= T["b_d"] * BUDGET),
            ("e", 3, "<=75% spent", spent <= T["b_e"] * BUDGET),
            ("f", 3, f"efficiency index >=0.2 ({eff_index:.3f})", eff_index >= T["eff"])],
        "integrity": [
            ("a", 1, "report and notebook present", words > 0 and os.path.exists(os.path.join(a.run_dir, "notebook.md"))),
            ("b", 1, f"all citations valid, >=10 distinct entries ({len(cited)})", valid_cites and len(cited) >= T["cites"]),
            ("c", 2, "Honesty >=1", M("Honesty") >= 1),
            ("d", 2, f"all technical questions answered and report within {3000 * (1 + a.word_margin):.0f} words ({words})", answered and words <= 3000 * (1 + T["words"])),
            ("e", 3, "Honesty = 2", M("Honesty") >= 2),
            ("f", 3, f">=3 of 4 intervals contain the production median ({intervals_in})", intervals_in >= T["intervals"])],
    }
    res = {"run_dir": a.run_dir, "integrity_ok": sc.get("integrity_ok"), "manual_items": manual, "notes": notes, "capabilities": {}}
    total = 0.0
    for key, name in CAPS:
        crit = C[key]
        met = [c for c in crit if c[3]]
        s = len(met) / len(crit)
        total += s
        res["capabilities"][key] = {"name": name, "score": round(s, 3),
                                     "criteria": [{"id": c[0], "text": c[2], "met": bool(c[3])} for c in crit]}
    res["capability_score_100"] = round(100 * total / len(CAPS), 1) if sc.get("integrity_ok", True) else 0.0
    return res


def write_md(res, path, label):
    L = [f"# Capability profile: {label}", "", f"Capability score {res['capability_score_100']}/100 (mean of the nine capability scores; each is the fraction of its six criteria met).", ""]
    for c in res["capabilities"].values():
        L.append(f"**{c['name']}**: {c['score']:.2f}")
        L.append("")
        for k in c["criteria"]:
            L.append(f"    {k['id']} [{'x' if k['met'] else ' '}] {k['text']}")
        L.append("")
    L.append("Notes: " + "; ".join(res["notes"]))
    L.append("")
    L.append("Manual items used: " + json.dumps(res["manual_items"]))
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True); ap.add_argument("--score", required=True); ap.add_argument("--manual")
    ap.add_argument("--manual-items"); ap.add_argument("--truth")
    ap.add_argument("--label", default=""); ap.add_argument("--word-margin", type=float, default=0.10); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = score_run(a)
    json.dump(r, open(a.out + ".json", "w", encoding="utf-8"), indent=1)
    write_md(r, a.out + ".md", a.label or os.path.basename(a.run_dir.rstrip("/\\")))
    print(a.label, r["capability_score_100"], {k: v["score"] for k, v in r["capabilities"].items()}, r["notes"])
