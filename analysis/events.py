#!/usr/bin/env python3
"""Response to the planted events, the counts in Sections 4.4-4.6 and the time columns of Table S6.

  python analysis/events.py --data <deposit>

Reads each run's ledger, score file, capability profile and harness transcript from the deposit,
and the campaign truth files from answers/ in the kit. Writes out/events.md with ESI Table S3c and
the counts quoted in Sections 4.4 to 4.6 of the paper, and out/run_times.csv with the wall-clock time
and tool calls of every run (ESI Table S6).
"""
import csv, glob, json, os, re, statistics, sys

import common as C

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import audit_transcript as AT  # noqa: E402

KIT = os.path.dirname(HERE)
SYSTEMS = [("Claude Fable 5.2", "Claude Code", "Fable 5.2 (Claude Code)"),
           ("Gemini 4 Carbon", "Antigravity", "Carbon (Antigravity)"),
           ("Claude Opus 5.5", "Antigravity", "Opus 5.5 (Antigravity)"),
           ("Claude Opus 5.5", "Claude Code", "Opus 5.5 (Claude Code)"),
           ("Gemini 4 Hydrogen", "Antigravity", "Hydrogen (Antigravity)")]


def half_up(x, nd=0):
    """Round halves away from zero, so that 1,680.5 credits is 1,681 everywhere."""
    q = 10 ** nd
    v = int(x * q + 0.5 + 1e-9)  # the epsilon absorbs float sums such as 1680.4999999
    return v / q if nd else v


def run_events(d, run_id, campaign):
    truth = json.load(open(os.path.join(KIT, "answers", f"truth_{campaign}.json"), encoding="utf-8"))
    ents = AT.ledger_from_file(os.path.join(d, "run_folder", ".vlab", "ledger.jsonl"))
    rows, last = AT.trajectory(ents, truth)
    def after(name):
        # "+2.50 days after" in the trajectory row of the same name, as in the transcript audits
        row = next(r for r in rows if r[0] == name)
        m = re.search(r"([+-][\d.]+) days after", row[2])
        return float(m.group(1)) if m else None
    score = json.load(open(os.path.join(d, "scoring", "score.json"), encoding="utf-8"))
    items = {i["id"]: i for i in score["items"]}
    cap = json.load(open(os.path.join(d, "scoring", "capability.json"), encoding="utf-8"))
    res = {c["id"]: c["met"] for c in cap["capabilities"]["resources"]["criteria"]}
    return {"run_id": run_id,
            "lot_days": after("Lot change"),
            "indium_days": after("DSC offset"),
            "humidity_ok": items["D.humidity"].get("correct") is True,
            "aspect_ok": items["D.aspect"].get("correct") is True,
            "amine_ok": items["D.amine"].get("correct") is True,
            "pass": score["production_pass_fraction"]["All"],
            "credits": score["credits_spent"],
            "recipe_before_70": res.get("d") is True}


def main():
    a = C.args("Planted events, Section 4.4-4.6 counts and run times.")
    rows = C.runs(a.data)
    ev, times = {}, []
    for r in rows:
        d = os.path.join(a.data, "runs", r["run_id"])
        ev[r["run_id"]] = run_events(d, r["run_id"], r["campaign"])
        tr = glob.glob(os.path.join(d, "transcript", "*.jsonl"))[0]
        _, t = AT.load_transcript(tr)
        mins = (max(t["times"]) - min(t["times"])) / 60
        times.append({"run_id": r["run_id"], "wall_clock_min": round(mins), "tool_calls": len(t["calls"]),
                      "context_compactions": len(t["compactions"])})
    with open(os.path.join(a.out, "run_times.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(times[0])); w.writeheader(); w.writerows(times)

    def rng(v, nd=2):
        return f"{min(v):.{nd}f}–{max(v):.{nd}f}"

    o = ["# Response to the planted events", "",
         "| System | Runs | New lot characterised (days after delivery) | Indium check (days after DSC service) | "
         "Humidity judged to have no effect | Aspect ratio correct | Amine optimum correct | Production pass (%) | Credits spent (of 1,800) |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for model, harness, label in SYSTEMS:
        rs = [r for r in rows if r["model"] == model and r["harness"] == harness]
        es = [ev[r["run_id"]] for r in rs]
        camp = {}
        for r in rs:
            camp.setdefault(r["campaign"], []).append(ev[r["run_id"]]["pass"])
        pp = statistics.mean(statistics.mean(v) for v in camp.values())
        cr = [half_up(e["credits"]) for e in es]
        n = len(es)
        o.append(f"| {label} | {n} | {rng([e['lot_days'] for e in es])} | {rng([e['indium_days'] for e in es])} | "
                 f"{sum(e['humidity_ok'] for e in es)}/{n} | {sum(e['aspect_ok'] for e in es)}/{n} | "
                 f"{sum(e['amine_ok'] for e in es)}/{n} | {half_up(100 * pp)} | {min(cr):,}–{max(cr):,} |")
    allv = list(ev.values())
    credits = [e["credits"] for e in allv]
    after70 = sum(not e["recipe_before_70"] for e in allv)
    spare = {label: sum(1 for r in rows if r["model"] == m and r["harness"] == h and float(r["credits_spent"]) < 0.8 * 1800)
             for m, h, label in SYSTEMS}
    o += ["", "# Counts in Sections 4.4 to 4.6", "",
          f"- Credits spent: {half_up(min(credits)):,}–{half_up(max(credits)):,} of 1,800, median {half_up(statistics.median(credits)):,}.",
          f"- Runs in which the submitted recipe was first made only after 70% of the budget had gone: {after70} of {len(allv)}.",
          "- Runs leaving more than a fifth of the budget unspent, by system: " + ", ".join(f"{k} {v}" for k, v in spare.items()) + ".",
          f"- New lot characterised {rng([e['lot_days'] for e in allv])} days after delivery; first indium check "
          f"{rng([e['indium_days'] for e in allv])} days after the DSC service.",
          f"- Humidity judged to have an effect: {sum(not e['humidity_ok'] for e in allv)} of {len(allv)} runs.",
          f"- Aspect ratio misjudged: {sum(not e['aspect_ok'] for e in allv)} of {len(allv)} runs.",
          f"- Amine optimum found within tolerance: {sum(e['amine_ok'] for e in allv)} of {len(allv)} runs "
          "(the stated causes are classified by hand in ESI Table S3d)."]
    text = "\n".join(o) + "\n"
    open(os.path.join(a.out, "events.md"), "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
