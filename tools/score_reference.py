#!/usr/bin/env python3
"""Seal and score the oracle's reference submissions.

For each campaign this makes a fresh folder with the agent binary, the campaign key and the
reference submission in answers/, waits to day 20, opens the questions, seals the submission and
scores the folder with the public scorer. It writes results/reference_scores.json, which the figure
code reads for the oracle in Fig. 3b.

  python tools/score_reference.py [--platform linux_x64] [--campaigns A B C D E]
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"{' '.join(cmd)} failed in {cwd}:\n{r.stdout}{r.stderr}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--platform", default="linux_x64",
                    help="folder under agent_kit/bin and scorer/ (linux_x64, linux_arm64, macos_x64, macos_arm64, windows_x64, windows_arm64)")
    ap.add_argument("--campaigns", nargs="+", default=list("ABCDE"))
    a = ap.parse_args()
    exe = ".exe" if a.platform.startswith("windows") else ""
    vlab = os.path.join(KIT, "agent_kit", "bin", a.platform, "vlab" + exe)
    scorer = os.path.join(KIT, "scorer", a.platform, "vlab-score" + exe)
    out = {}
    for c in a.campaigns:
        d = tempfile.mkdtemp(prefix=f"reference_{c}_")
        try:
            shutil.copy(vlab, d)
            shutil.copy(os.path.join(KIT, "campaigns", f"campaign_{c}.key"), os.path.join(d, "campaign.key"))
            shutil.copy(os.path.join(KIT, "answers", f"reference_submission_{c}.json"), os.path.join(d, "submission.json"))
            with open(os.path.join(d, "report.md"), "w", encoding="utf-8") as f:
                f.write("# Reference submission\n")
            v = os.path.join(d, "vlab" + exe)
            run([v, "wait", "--days", "20"], d)
            run([v, "questions", "--confirm"], d)
            run([v, "submit", "submission.json"], d)
            run([scorer, "score", "--dir", d, "--out", os.path.join(d, "score.json")], d)
            s = json.load(open(os.path.join(d, "score.json"), encoding="utf-8"))
            disc = [i for i in s["items"] if i["id"].startswith("D.")]
            out[c] = {"production_pass_all": s["production_pass_fraction"]["All"],
                      "production_pass": s["production_pass_fraction"],
                      "discovery_correct": sum(1 for i in disc if i.get("correct")),
                      "discovery_items": len(disc)}
            print(f"campaign {c}: production pass {100 * out[c]['production_pass_all']:.1f}%, "
                  f"{out[c]['discovery_correct']} of {out[c]['discovery_items']} discovery items correct")
        finally:
            shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(KIT, "results"), exist_ok=True)
    with open(os.path.join(KIT, "results", "reference_scores.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
