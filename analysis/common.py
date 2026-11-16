"""Shared helpers for the analysis scripts: where the data deposit is, the systems and the capabilities."""
import argparse, csv, os, sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KIT, "tools"))

SYSTEMS = [  # (run prefix, label, colour) in the order of the paper's figures
    ("fable52", "Fable 5.2 (Claude Code)", "#2a78d6"),
    ("carbon", "Carbon (Antigravity)", "#eb6834"),
    ("opus55ag", "Opus 5.5 (Antigravity)", "#1baf7a"),
    ("opus55", "Opus 5.5 (Claude Code)", "#eda100"),
    ("hydrogen", "Hydrogen (Antigravity)", "#e87ba4"),
]
CAPS = [("delivery", "Project delivery"), ("design", "Experimental design"), ("information", "Source scrutiny"),
        ("analysis", "Data analysis"), ("critical", "Measurement judgement"), ("adaptability", "Response to change"),
        ("insight", "Scientific insight"), ("resources", "Resource management"), ("integrity", "Honest reporting")]
CAMPAIGNS = ["A", "B", "C"]


def args(description, extra=None):
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--data", default=os.environ.get("ARCF_DATA"),
                    help="the unpacked run-records deposit, which holds runs.csv (see analysis/README.md)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    if extra:
        extra(ap)
    a = ap.parse_args()
    if not a.data or not os.path.exists(os.path.join(a.data, "runs.csv")):
        ap.error("give --data (or set ARCF_DATA) as the folder of the run-records deposit, which holds runs.csv")
    os.makedirs(a.out, exist_ok=True)
    return a


def system_of(run_id):
    return run_id.rsplit("_", 1)[0]


def campaign_of(run_id):
    return run_id.rsplit("_", 1)[1][0]


def runs(data):
    return list(csv.DictReader(open(os.path.join(data, "runs.csv"), encoding="utf-8")))
