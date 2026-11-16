#!/usr/bin/env python3
"""Recompute every run's capability profile from its records and check it against runs.csv.

  python analysis/rescore.py --data <deposit>

Writes out/capability_scores.csv. Each profile is computed by tools/capability_score.py from the run
folder, the automatic score file and the rubric grades, with the campaign's truth file from answers/.
"""
import csv, os, types
import common as C
import capability_score as CS


def score(data, run_id, thresholds=None):
    d = os.path.join(data, "runs", run_id)
    a = types.SimpleNamespace(run_dir=os.path.join(d, "run_folder"), score=os.path.join(d, "scoring", "score.json"),
                              manual=os.path.join(d, "scoring", "rubric_grades.md"), manual_items=None, truth=None, word_margin=0.10)
    if thresholds is not None:
        CS.T.clear(); CS.T.update(thresholds)
    return CS.score_run(a)


def main():
    a = C.args("Recompute the capability profile of every run.")
    rows, bad = [], 0
    for r in C.runs(a.data):
        res = score(a.data, r["run_id"])
        row = {"run_id": r["run_id"], "capability_score_100": res["capability_score_100"],
               **{k: res["capabilities"][k]["score"] for k, _ in C.CAPS}}
        same = abs(row["capability_score_100"] - float(r["capability_score_100"])) < 1e-9 and \
            all(abs(row[k] - float(r[k])) < 1e-9 for k, _ in C.CAPS)
        bad += not same
        print(f"{r['run_id']:12} {row['capability_score_100']:5.1f}  {'matches runs.csv' if same else 'DIFFERS from runs.csv'}")
        rows.append(row)
    with open(os.path.join(a.out, "capability_scores.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("all runs match" if not bad else f"{bad} run(s) differ")


if __name__ == "__main__":
    main()
