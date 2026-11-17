#!/usr/bin/env python3
"""Threshold sensitivity (paper Section 4.9, ESI Section S4 and Fig. S1).

  python analysis/sensitivity.py --data <deposit>

Each of the 28 numerical thresholds of the criteria (tools/capability_score.py, BASE) is moved one step
down and one step up, one at a time, and all 17 runs are re-scored, giving 56 alternative scorings; all
thresholds are then moved together towards easier and towards stricter criteria. Writes
out/sensitivity_raw.json and out/sensitivity_summary.csv and prints the summary quoted in the paper.
"""
import csv, json, os, statistics as stt
import common as C
import capability_score as CS
from rescore import score

STEPS = dict(pp=(0.4, 0.6), d_n=(2, 4), d_e=(0.8, 0.95), powders=(2, 4), factors=(2, 4), spec=(4, 6), repeat=(1, 3),
             thick2=(1, 3), thick3=(2, 4), agr1=(0.15, 0.25), agr2=(0.075, 0.125), agr3=(0.025, 0.075), rho_dec=(0.3, 0.7),
             ind_days=(1.0, 3.0), dsc_between=(0, 2), lot_days=(2.0, 4.0), nq1=(0, 2), nq3=(2, 4), nq4=(3, 5), b_a=(0.94, 1.0),
             b_b=(0.80, 0.90), b_c=(0.85, 0.95), b_d=(0.65, 0.75), b_e=(0.70, 0.80), eff=(0.15, 0.25), cites=(8, 12),
             words=(0.0, 0.20), intervals=(2, 4))
# for each threshold, whether the higher value makes the criterion easier to meet
EASIER_IS_HI = dict(pp=0, d_n=0, d_e=0, powders=0, factors=0, spec=0, repeat=0, thick2=0, thick3=0, agr1=1, agr2=1, agr3=1,
                    rho_dec=1, ind_days=1, dsc_between=1, lot_days=1, nq1=0, nq3=0, nq4=0, b_a=1, b_b=1, b_c=1, b_d=1, b_e=1,
                    eff=0, cites=0, words=1, intervals=0)
NAMES = {"fable52": "Fable 5.2", "carbon": "Carbon", "opus55ag": "Opus 5.5 (Antigravity)", "opus55": "Opus 5.5 (Claude Code)",
         "hydrogen": "Hydrogen"}


def main():
    a = C.args("Threshold sensitivity of the capability scores.")
    ids = [r["run_id"] for r in C.runs(a.data)]
    # the reference reduction of raw data does not depend on the thresholds: compute it once per run
    ref, cache = CS.reference, {}
    def ref_cached(ents, run_dir, batches):
        k = (run_dir, tuple(e["i"] for e in batches))
        if k not in cache:
            cache[k] = ref(ents, run_dir, batches)
        return cache[k]
    CS.reference = ref_cached

    def score_all(T):
        out = {}
        for r in ids:
            res = score(a.data, r, T)
            caps = {k: v["score"] for k, v in res["capabilities"].items()}
            # unrounded overall score: criteria met out of 54 (each capability score is a multiple of 1/6)
            out[r] = {"overall": 100 * sum(round(6 * v) for v in caps.values()) / 54, "caps": caps}
        return out

    results = {"baseline": score_all(CS.BASE)}
    for k, (lo, hi) in STEPS.items():
        for tag, v in (("lo", lo), ("hi", hi)):
            T = dict(CS.BASE); T[k] = v
            results[f"{k}:{tag}={v}"] = score_all(T)
    easy, strict = dict(CS.BASE), dict(CS.BASE)
    for k, (lo, hi) in STEPS.items():
        easy[k], strict[k] = (hi, lo) if EASIER_IS_HI[k] else (lo, hi)
    results["ALL:easier"] = score_all(easy)
    results["ALL:stricter"] = score_all(strict)
    CS.T.clear(); CS.T.update(CS.BASE)
    json.dump({"steps": STEPS, "base": CS.BASE, "easier_is_hi": EASIER_IS_HI, "results": results},
              open(os.path.join(a.out, "sensitivity_raw.json"), "w"), indent=1)

    def sysmean(res, p, f):
        vals = []
        for c in C.CAMPAIGNS:
            reps = [f(v) for r, v in res.items() if C.system_of(r) == p and C.campaign_of(r) == c]
            vals.append(sum(reps) / len(reps))
        return sum(vals) / len(vals)

    base = {n: sysmean(results["baseline"], p, lambda v: v["overall"]) for p, n in NAMES.items()}
    border = sorted(base, key=lambda s: -base[s])
    rows = []
    for name, res in results.items():
        m = {n: sysmean(res, p, lambda v: v["overall"]) for p, n in NAMES.items()}
        order = sorted(m, key=lambda s: -m[s])
        capm = {n: {k: sysmean(res, p, lambda v, k=k: v["caps"][k]) for k, _ in C.CAPS} for p, n in NAMES.items()}
        rows.append({"perturbation": name, **{n: round(m[n], 1) for n in NAMES.values()},
                     "order": " > ".join(order), "same_order": order == border, "fable_first": order[0] == "Fable 5.2",
                     "fable_minus_3rd": round(m["Fable 5.2"] - sorted(m.values())[-3], 1),
                     "harness_gap_total": round(m["Opus 5.5 (Antigravity)"] - m["Opus 5.5 (Claude Code)"], 1),
                     "harness_gap_delivery": round(capm["Opus 5.5 (Antigravity)"]["delivery"] - capm["Opus 5.5 (Claude Code)"]["delivery"], 2),
                     "resources_lowest_all": all(capm[n]["resources"] <= min(capm[n].values()) + 1e-9 for n in NAMES.values()),
                     "analysis_ceiling_all": all(v["caps"]["analysis"] >= 0.999 for v in res.values()),
                     "max_abs_shift": round(max(abs(m[n] - base[n]) for n in NAMES.values()), 1)})
    with open(os.path.join(a.out, "sensitivity_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    one = [r for r in rows if ":" in r["perturbation"] and not r["perturbation"].startswith("ALL")]
    print("as scored:", {n: round(v, 1) for n, v in base.items()})
    print("single-threshold moves:", len(one), "| order unchanged:", sum(r["same_order"] for r in one),
          "| Fable first:", sum(r["fable_first"] for r in one))
    print("largest shift of any system mean:", max(r["max_abs_shift"] for r in one),
          "| median:", stt.median(r["max_abs_shift"] for r in one), "| moves changing nothing:", sum(r["max_abs_shift"] == 0 for r in one))
    for n in NAMES.values():
        print(f"  {n}: {min(r[n] for r in one)}-{max(r[n] for r in one)}")
    print("Fable minus third:", min(r["fable_minus_3rd"] for r in one), "-", max(r["fable_minus_3rd"] for r in one))
    print("harness gap, capability score:", min(r["harness_gap_total"] for r in one), "-", max(r["harness_gap_total"] for r in one),
          "| delivery:", min(r["harness_gap_delivery"] for r in one), "-", max(r["harness_gap_delivery"] for r in one))
    print("resource management lowest for every system:", sum(r["resources_lowest_all"] for r in one),
          "| data analysis at ceiling:", sum(r["analysis_ceiling_all"] for r in one))
    for r in rows:
        if r["perturbation"].startswith("ALL"):
            print(r["perturbation"], r["order"], {n: r[n] for n in NAMES.values()})


if __name__ == "__main__":
    main()
