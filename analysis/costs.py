#!/usr/bin/env python3
"""Token counts and API-equivalent cost of every run from its harness transcript (ESI Table S6).

  python analysis/costs.py --data <deposit>

Writes out/costs.csv. Prices are USD per million tokens, the standard list prices in force when the runs
were made. Claude Code reports usage per API response (counted once per message id), with cache writes
split into 5-minute and 1-hour writes. Antigravity reports input, output and cache-read tokens per step but
not cache writes, so for Claude Opus 5.5 in Antigravity input is priced at the base input rate (low) and at
the 5-minute cache-write rate (high). Gemini 4 Carbon was priced at an introductory rate when the runs
were made and at its standard rate afterwards; the range spans the two.
"""
import csv, json, os
import common as C
import audit_transcript as AT

P = {  # input, 5-minute cache write, 1-hour cache write, cache read, output
    "opus55": dict(i=4, w5=5, w1=8, r=0.20, o=20),
    "fable52": dict(i=8, w5=10, w1=16, r=0.20, o=40),
    "carbon": dict(i=4, w5=4, w1=4, r=0.20, o=20),
    "carbon_intro": dict(i=2, w5=2, w1=2, r=0.10, o=10),
    "hydrogen": dict(i=1.50, w5=1.50, w1=1.50, r=0.075, o=7.50),
}


def claude_code_tokens(path):
    t = dict(i=0, w5=0, w1=0, r=0, o=0); seen = set()
    for line in open(path, encoding="utf-8"):
        m = json.loads(line).get("message") or {}
        u = m.get("usage")
        if not u or m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        t["i"] += u.get("input_tokens") or 0; t["o"] += u.get("output_tokens") or 0
        t["r"] += u.get("cache_read_input_tokens") or 0
        cc = u.get("cache_creation") or {}
        w5, w1 = cc.get("ephemeral_5m_input_tokens"), cc.get("ephemeral_1h_input_tokens")
        if w5 is None and w1 is None:
            w5, w1 = u.get("cache_creation_input_tokens") or 0, 0
        t["w5"] += w5 or 0; t["w1"] += w1 or 0
    return t


def antigravity_tokens(path):
    tk = AT.read_antigravity([json.loads(l) for l in open(path, encoding="utf-8") if l.strip()])["tokens"]
    return dict(i=tk["input_tokens"], w5=0, w1=0, r=tk["cache_read_tokens"], o=tk["output_tokens"])


def cost(t, p, input_as_write=False):
    return (t["i"] * (p["w5"] if input_as_write else p["i"]) + t["w5"] * p["w5"] + t["w1"] * p["w1"] + t["r"] * p["r"] + t["o"] * p["o"]) / 1e6


def main():
    a = C.args("Token counts and API-equivalent costs.")
    rows = []
    for r in C.runs(a.data):
        run, s = r["run_id"], C.system_of(r["run_id"])
        tdir = os.path.join(a.data, "runs", run, "transcript")
        if r["harness"] == "Antigravity":
            t = antigravity_tokens(os.path.join(tdir, "antigravity_transcript_full.jsonl"))
        else:
            t = claude_code_tokens(os.path.join(tdir, "claude_code_session.jsonl"))
        model = "opus55" if s == "opus55ag" else s
        if model == "carbon":
            lo, hi = cost(t, P["carbon_intro"]), cost(t, P["carbon"])
        elif r["harness"] == "Antigravity" and model == "opus55":
            lo, hi = cost(t, P[model]), cost(t, P[model], True)
        else:
            lo = hi = cost(t, P[model])
        rows.append(dict(run_id=run, harness=r["harness"], input_tokens=t["i"], cache_write_tokens=t["w5"] + t["w1"],
                         cache_read_tokens=t["r"], output_tokens=t["o"], usd_low=round(lo, 2), usd_high=round(hi, 2)))
        print(f"{run:12} {r['harness']:11} in {t['i']:>9,} write {t['w5'] + t['w1']:>9,} read {t['r']:>11,} out {t['o']:>9,}  "
              f"${lo:.2f}" + ("" if abs(hi - lo) < 0.005 else f"-{hi:.2f}"))
    with open(os.path.join(a.out, "costs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    lo = sum(r["usd_low"] for r in rows); hi = sum(r["usd_high"] for r in rows)
    print(f"all {len(rows)} runs: ${lo:.0f}-{hi:.0f}")


if __name__ == "__main__":
    main()
