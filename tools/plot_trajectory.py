#!/usr/bin/env python3
"""Panel (b): campaign trajectories of two or more runs, drawn from their signed ledgers.

Each run gets a timeline (batches made and tests run, by instrument group, against the
simulated day) and a strip of cumulative credits beneath it. The hidden events of the
campaign (lot change, DSC service) are drawn as vertical lines, with the day each run
first acted on them marked. Production (day 20) is the solid line.

Usage (all runs must be on the same campaign):
  python tools/plot_trajectory.py --truth answers/truth_A.json \
      --run "Model X|81.0|runs/modelx_A/.vlab/ledger.jsonl" \
      --run "Model Y|60.5|runs/modely_A/.vlab/ledger.jsonl" \
      --out figures/trajectories_A

Writes <out>.png (300 dpi) and <out>.pdf. The truth is read into memory only.
"""
import argparse, json, re, subprocess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

GROUPS = [  # (row label, instruments, colour) - categorical slots 1-4, each on its own row
    ("Mechanical", {"tensile", "senb", "dma"}, "#2a78d6"),
    ("Thermal", {"dsc", "dsc-indium", "tga"}, "#eb6834"),
    ("Structure and powder", {"raman", "xrd", "bet", "sem"}, "#1baf7a"),
    ("Electrical and physical", {"resist2", "resist4", "density", "rheo", "rheology"}, "#eda100"),
]
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
BUDGET, PRODUCTION_DAY = 1800, 20


def load_truth(a):
    if a.truth:
        return json.load(open(a.truth, encoding="utf-8"))
    out = subprocess.run([a.examiner, "truth", "--key", a.key], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def load_ledger(path):
    ents = []
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        d = json.loads(line)
        args = d.get("args") or []
        args = [str(x) for x in args] if isinstance(args, list) else str(args).split()
        summ = d.get("summary") or ""
        cmd = d.get("cmd", "")
        day = float(d.get("day_after") or 0)
        e = {"i": d["i"], "cmd": cmd, "args": args, "summary": summ, "cost": float(d.get("cost") or 0), "day": day}
        if cmd == "make":
            m = re.search(r"made on day ([\d.]+)", summ)
            e["day"] = float(m.group(1)) if m else day
            e["filler"] = args[args.index("--filler") + 1] if "--filler" in args else "?"
        if cmd == "test":
            e["method"] = next((x for x in args if not x.startswith("--")), "?").lower()
            e["powder"] = args[args.index("--powder") + 1] if "--powder" in args else None
        ents.append(e)
    return ents


def events(ents, truth):
    grades = truth["Grades"]
    liar = next(g["Name"] for g in grades if g.get("Role") == "liar")
    lotg = grades[truth["LotGrade"]]
    new_lot = lotg["Lots"][-1]["ID"]
    lot_day, dsc_day = truth["LotDay"], truth["DSCDay"]
    first = lambda p: next((e for e in ents if p(e)), None)
    return {
        "liar": liar,
        "liar_batches": sum(1 for e in ents if e["cmd"] == "make" and e.get("filler") == liar),
        "lot_grade": lotg["Name"], "lot_day": lot_day, "dsc_day": dsc_day,
        "lot_seen": first(lambda e: e["cmd"] == "test" and e.get("powder") == lotg["Name"] and new_lot in e["summary"]),
        "indium": first(lambda e: e["cmd"] == "test" and e.get("method") == "dsc-indium" and e["day"] > dsc_day),
    }


def draw_run(ax, axc, label, score, ents, ev, xmax):
    rows = ["Batches made"] + [g[0] for g in GROUPS]
    ypos = {r: len(rows) - 1 - k for k, r in enumerate(rows)}
    for y in ypos.values():
        ax.axhline(y, color=GRID, lw=0.6, zorder=0)
    mk = [e for e in ents if e["cmd"] == "make"]
    ax.scatter([e["day"] for e in mk], [ypos["Batches made"]] * len(mk), marker="s", s=46,
               color=INK2, edgecolor="white", linewidth=0.8, zorder=3)
    for name, methods, col in GROUPS:
        t = [e for e in ents if e["cmd"] == "test" and e.get("method") in methods]
        ax.scatter([e["day"] for e in t], [ypos[name]] * len(t), marker="|", s=110, color=col, linewidths=1.6, zorder=3)
    for x, txt in ((ev["lot_day"], f"{ev['lot_grade']} lot change"), (ev["dsc_day"], "DSC service")):
        for a in (ax, axc):
            a.axvline(x, color=MUTED, lw=0.9, ls=(0, (4, 3)), zorder=1)
        ax.text(x + 0.2, len(rows) - 0.75, txt, fontsize=7.5, color=INK2, va="bottom", zorder=5,
                bbox=dict(boxstyle="square,pad=0.15", facecolor="white", edgecolor="none"))
    for a in (ax, axc):
        a.axvline(PRODUCTION_DAY, color=INK, lw=1.0, zorder=1)
    ax.text(PRODUCTION_DAY + 0.2, len(rows) - 0.75, "production", fontsize=7.5, color=INK, va="bottom")
    for key, row, base, verb in (("lot_seen", "Structure and powder", ev["lot_day"], "new lot checked"),
                                 ("indium", "Thermal", ev["dsc_day"], "indium check")):
        e = ev[key]
        if e:
            ax.scatter([e["day"]], [ypos[row]], marker="o", s=70, facecolor="none", edgecolor=INK, linewidth=1.2, zorder=4)
            right = e["day"] > xmax - 6
            ax.annotate(f"{verb} +{e['day'] - base:.1f} d", (e["day"], ypos[row]), xytext=(-6 if right else 6, 7),
                        textcoords="offset points", fontsize=7.5, color=INK, ha="right" if right else "left", zorder=5,
                        bbox=dict(boxstyle="square,pad=0.15", facecolor="white", edgecolor="none"))
        else:
            ax.text(xmax - 0.3, ypos[row] + 0.18, f"no {verb}", fontsize=7.5, color=INK, ha="right")
    ax.set_yticks(list(ypos.values()), list(ypos.keys()), fontsize=8, color=INK2)
    ax.set_ylim(-0.6, len(rows) - 0.1)
    n_tests = sum(1 for e in ents if e["cmd"] == "test")
    ax.set_title(f"{label}   {score}/100", loc="left", fontsize=10, color=INK, pad=16, fontweight="medium")
    nl = ev["liar_batches"]
    liar_txt = f"no batches on {ev['liar']}" if nl == 0 else f"{nl} batch{'es' if nl > 1 else ''} on {ev['liar']}"
    ax.text(0, 1.0, f"{len(mk)} batches, {n_tests} tests, {liar_txt} (misleading datasheet)",
            transform=ax.transAxes, fontsize=7.5, color=INK2, va="bottom")
    xs, cs, c = [0.0], [0.0], 0.0
    for e in sorted(ents, key=lambda e: e["i"]):
        c += e["cost"]
        xs.append(float(e["day"] if e["cmd"] != "make" else e["day"] + 1)); cs.append(c)
    axc.step(xs, cs, where="post", color=INK2, lw=1.4)
    axc.axhline(BUDGET, color=MUTED, lw=0.6)
    axc.set_ylim(0, BUDGET * 1.08)
    axc.set_yticks([0, 900, 1800], ["0", "900", "1,800"], fontsize=7.5, color=INK2)
    axc.set_ylabel("credits", fontsize=7.5, color=INK2)
    for a in (ax, axc):
        for s in ("top", "right", "left"):
            a.spines[s].set_visible(False)
        a.spines["bottom"].set_color(MUTED)
        a.tick_params(axis="both", length=0, colors=INK2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth"); ap.add_argument("--key"); ap.add_argument("--examiner")
    ap.add_argument("--run", action="append", required=True, help='"label|score|ledger.jsonl"')
    ap.add_argument("--campaign", default=None, help="campaign letter for the axis label")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    truth = load_truth(a)
    runs = []
    for r in a.run:
        label, score, path = r.split("|", 2)
        ents = load_ledger(path)
        runs.append((label, score, ents, events(ents, truth)))
    xmax = max(max(e["day"] for e in ents) for _, _, ents, _ in runs) + 1.0
    xmax = max(xmax, PRODUCTION_DAY + 2)
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(7.2, 3.2 * len(runs)))
    gs = fig.add_gridspec(3 * len(runs) - 1, 1, height_ratios=([3.2, 1.0, 0.7] * len(runs))[:-1], hspace=0.18)
    ax0 = None
    for k, (label, score, ents, ev) in enumerate(runs):
        ax = fig.add_subplot(gs[3 * k], sharex=ax0); ax0 = ax0 or ax
        axc = fig.add_subplot(gs[3 * k + 1], sharex=ax0)
        draw_run(ax, axc, label, score, ents, ev, xmax)
        plt.setp(ax.get_xticklabels(), visible=False)
        if k < len(runs) - 1:
            plt.setp(axc.get_xticklabels(), visible=False)
    ax0.set_xlim(-0.5, xmax)
    axc.set_xlabel(f"simulated laboratory day" + (f" (campaign {a.campaign})" if a.campaign else ""), fontsize=8.5, color=INK2)
    handles = [Line2D([], [], marker="s", ls="", color=INK2, ms=6, label="batch made")]
    handles += [Line2D([], [], marker="|", ls="", color=c, ms=9, mew=1.6, label=n.lower()) for n, _, c in GROUPS]
    handles += [Line2D([], [], marker="o", ls="", mfc="none", mec=INK, ms=7, label="first acted on hidden event")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.subplots_adjust(left=0.2, right=0.98, top=0.9, bottom=0.12 if len(runs) > 1 else 0.2)
    for ext in ("png", "pdf"):
        fig.savefig(f"{a.out}.{ext}", dpi=300, facecolor="white",
                    metadata={"Software": None} if ext == "png" else {"Creator": None, "Producer": None, "CreationDate": None})
    print("wrote", a.out + ".png", a.out + ".pdf")


if __name__ == "__main__":
    main()
