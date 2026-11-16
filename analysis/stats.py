#!/usr/bin/env python3
"""System means, bootstrap intervals, run-to-run spread and paired comparisons (paper Sections 3.5 and 4).

  python analysis/stats.py --data <deposit>

Writes out/stats.json and out/stats.md.

Method
  * A system is a model in a harness. Each system ran campaigns A, B and C; Opus 5.5 ran campaign A
    twice in each harness.
  * Campaign score of a system = mean of its runs on that campaign; system score = mean of its three
    campaign scores, each campaign weighted equally.
  * Run-to-run spread from the two replicate pairs: SD_within = sqrt(sum(d^2) / 2n), where d is the
    difference between the two runs of a pair and n = 2 is the number of pairs.
  * 90% intervals: hierarchical bootstrap, 20,000 draws. Each draw resamples the three campaigns with
    replacement and, where a campaign has two runs, picks one at random; a campaign with a single run
    has normal noise with SD_within added. Each quantity uses its own seeded generator, so a result does
    not depend on which other quantities are computed. Paired comparisons use the same resampled
    campaigns for both systems and report the share of draws in which the first scores higher.
"""
import json, math, os, random
import common as C

N = 20000


def main():
    a = C.args("Statistics for the paper.")
    rows = C.runs(a.data)
    keys = ["capability_score_100"] + [k for k, _ in C.CAPS]
    runs = {}
    for r in rows:
        rec = {"id": r["run_id"], **{k: float(r[k]) for k in keys}, "pass": float(r["production_pass_all"])}
        runs.setdefault(C.system_of(r["run_id"]), {}).setdefault(C.campaign_of(r["run_id"]), []).append(rec)
    mean = lambda xs: sum(xs) / len(xs)
    pairs = [v for s in runs.values() for v in s.values() if len(v) == 2]
    sdw = {k: math.sqrt(sum((p[0][k] - p[1][k]) ** 2 for p in pairs) / (2 * len(pairs))) for k in keys + ["pass"]}
    camp = lambda s, c, k: mean([x[k] for x in runs[s][c]])
    sysm = lambda s, k: mean([camp(s, c, k) for c in C.CAMPAIGNS])

    def draws(key, lo, hi):
        rng = random.Random("bootstrap:" + key)
        out = {s: [] for s, _, _ in C.SYSTEMS}
        for _ in range(N):
            cs = [rng.choice(C.CAMPAIGNS) for _ in C.CAMPAIGNS]
            for s, _, _ in C.SYSTEMS:
                vals = []
                for c in cs:
                    rr = runs[s][c]
                    v = rng.choice(rr)[key] if len(rr) > 1 else rr[0][key] + rng.gauss(0, sdw[key])
                    vals.append(min(max(v, lo), hi))
                out[s].append(mean(vals))
        return out

    def pct(xs, q):
        s = sorted(xs); i = q * (len(s) - 1); f = math.floor(i)
        return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (i - f)

    boot = {"capability_score_100": draws("capability_score_100", 0, 100)}
    for k, _ in C.CAPS:
        boot[k] = draws(k, 0, 1)
    p_greater = lambda key, x, y: round(sum(u > v for u, v in zip(boot[key][x], boot[key][y])) / N, 4)

    res = {"n_runs": len(rows), "sd_within": {k: round(v, 3) for k, v in sdw.items()},
           "replicate_pairs": [[x["id"] for x in p] for p in pairs], "systems": {}}
    for s, lab, _ in C.SYSTEMS:
        b = boot["capability_score_100"][s]
        res["systems"][s] = {
            "label": lab, "runs": sum(len(v) for v in runs[s].values()),
            "campaign_score": {c: round(camp(s, c, "capability_score_100"), 1) for c in C.CAMPAIGNS},
            "score": round(sysm(s, "capability_score_100"), 1), "score_90": [round(pct(b, .05), 1), round(pct(b, .95), 1)],
            "production_pass_mean": round(100 * sysm(s, "pass"), 1),
            "capabilities": {name: {"mean": round(sysm(s, k), 2), "90": [round(pct(boot[k][s], .05), 2), round(pct(boot[k][s], .95), 2)]}
                             for k, name in C.CAPS}}
    order = [s for s, _, _ in C.SYSTEMS]
    res["paired"] = {f"{x}>{y}": {"share_of_draws": p_greater("capability_score_100", x, y),
                                  "difference": round(sysm(x, "capability_score_100") - sysm(y, "capability_score_100"), 1)}
                     for i, x in enumerate(order) for y in order[i + 1:]}
    res["harness"] = {name: {"antigravity": round(sysm("opus55ag", k), 2), "claude_code": round(sysm("opus55", k), 2),
                             "p_antigravity_higher": p_greater(k, "opus55ag", "opus55"), "sd_within": round(sdw[k], 2)}
                      for k, name in C.CAPS}
    json.dump(res, open(os.path.join(a.out, "stats.json"), "w"), indent=1)

    L = ["# Statistics", "", f"Runs: {len(rows)}. Run-to-run SD (capability score): {sdw['capability_score_100']:.1f}.", "",
         "| System | Runs | A | B | C | Capability score, mean [90% interval] | Production pass (%) |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for s in sorted(order, key=lambda s: -res["systems"][s]["score"]):
        x = res["systems"][s]
        L.append(f"| {x['label']} | {x['runs']} | " + " | ".join(f"{x['campaign_score'][c]:.1f}" for c in C.CAMPAIGNS)
                 + f" | {x['score']:.1f} [{x['score_90'][0]:.1f}–{x['score_90'][1]:.1f}] | {x['production_pass_mean']:.0f} |")
    L += ["", "| Capability | " + " | ".join(res["systems"][s]["label"] for s in order) + " |", "| --- |" + " --- |" * len(order)]
    for _, name in C.CAPS:
        L.append(f"| {name} | " + " | ".join("{mean:.2f} [{lo:.2f}–{hi:.2f}]".format(mean=res["systems"][s]["capabilities"][name]["mean"],
                 lo=res["systems"][s]["capabilities"][name]["90"][0], hi=res["systems"][s]["capabilities"][name]["90"][1]) for s in order) + " |")
    L += ["", "Paired comparisons (share of bootstrap draws in which the first system scores higher):", ""]
    L += [f"- {k}: {v['share_of_draws']:.2f} (difference {v['difference']:+.1f})" for k, v in res["paired"].items()]
    open(os.path.join(a.out, "stats.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
