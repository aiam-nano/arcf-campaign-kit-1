#!/usr/bin/env python3
"""Figures 2, 3, 4 and 6 and supplementary Figures S1 and S2 of the paper.

  python analysis/figures.py --data <deposit>

Reads runs.csv and baselines/baselines.csv from the deposit, and out/stats.json and
out/sensitivity_summary.csv from stats.py and sensitivity.py (run those first). Writes PNG and PDF
files to out/figures/. Figure 1 is a drawn schematic (analysis/assets/fig1_campaign_schematic.svg);
Figure 5 is drawn by tools/plot_trajectory.py (see analysis/README.md).
"""
import csv, json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import common as C

A = C.args("Figures for the paper.")
OUT = os.path.join(A.out, "figures"); os.makedirs(OUT, exist_ok=True)
S = json.load(open(os.path.join(A.out, "stats.json")))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": False, "savefig.dpi": 600, "pdf.fonttype": 42})
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
SYS = [(k, l.replace(" (", "\n("), c) for k, l, c in C.SYSTEMS]
COL = {k: c for k, _, c in SYS}; LAB = {k: l for k, l, _ in SYS}
CAPS = [name for _, name in C.CAPS]
runs = C.runs(A.data)
for r in runs:
    r["campaign"] = C.campaign_of(r["run_id"])
def sysof(r): return C.system_of(r["run_id"])
def ppass(r): return 100 * float(r["production_pass_all"])
def mins(r): return float(r["wall_clock_min"])
def save(fig, name):
    for ext in ("png", "pdf"): fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight", facecolor="white")
    plt.close(fig)

# Figure 2: the framework
CARDS = [("Project delivery", "submitted recipe passes the\nspecification in virtual\nproduction"),
 ("Experimental design", "powders screened early,\nfactors varied, final\nrecipe replicated"),
 ("Source scrutiny", "misleading datasheet caught;\nfiller thickness established\nfrom evidence"),
 ("Data analysis", "agent's reduction of raw data\nagrees with the examiner's\n(within 20%, 10%, 5%)"),
 ("Measurement judgement", "instrument checked after\nservice; four-terminal\nresistivity; humidity rejected"),
 ("Response to change", "new material lot\ncharacterised promptly;\nold lot retired"),
 ("Scientific insight", "five quantitative answers\non the hidden physics;\nmechanism graded"),
 ("Resource management", "share of budget spent;\nfinal recipe found early"),
 ("Honest reporting", "valid citations, all questions\nanswered, calibrated intervals,\nhonesty graded")]
fig = plt.figure(figsize=(6.7, 3.9)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 3); ax.set_ylim(-0.3, 3); ax.axis("off")
for i, (n, d) in enumerate(CARDS):
    x, y = i % 3, 2 - i // 3
    ax.add_patch(FancyBboxPatch((x + 0.03, y + 0.05), 0.94, 0.88, boxstyle="round,pad=0,rounding_size=0.04", fc="#f4f8fe", ec="#86b6ef", lw=0.8))
    ax.text(x + 0.08, y + 0.82, f"{i + 1}. {n}", fontsize=8, fontweight="bold", color=INK, va="top")
    ax.text(x + 0.08, y + 0.6, d, fontsize=6.8, color=INK2, va="top", linespacing=1.4)
ax.text(1.5, -0.12, "Six criteria per capability, two at each of three levels  ·  capability score = fraction of criteria met  ·  overall = mean of the nine",
        ha="center", fontsize=6.8, color=INK2)
fig.savefig(os.path.join(OUT, "fig2_capability_framework.png"), facecolor="white"); fig.savefig(os.path.join(OUT, "fig2_capability_framework.pdf"), facecolor="white"); plt.close(fig)

# Figure 3: overall scores
fig, (a, b) = plt.subplots(1, 2, figsize=(6.7, 2.9), gridspec_kw={"width_ratios": [1.15, 1]})
for i, (k, l, c) in enumerate(SYS):
    s = S["systems"][k]; lo, hi = s["score_90"]
    a.plot([lo, hi], [i, i], color=c, lw=2, solid_capstyle="round", zorder=2)
    a.scatter([s["score"]], [i], s=46, color=c, edgecolor="white", lw=1.2, zorder=3)
    for cmp, v in s["campaign_score"].items():
        a.scatter([v], [i - 0.25], s=9, color=c, alpha=0.6, lw=0, zorder=2)
    a.text(hi + 0.6, i, f"{s['score']:.1f}", va="center", fontsize=7.5, color=INK)
a.set_yticks(range(5)); a.set_yticklabels([l.replace("\n", " ") for _, l, _ in SYS]); a.invert_yaxis()
a.set_xlim(68, 101); a.set_xlabel("Capability score (of 100)\nmean and 90% interval; small dots: campaigns A–C")
a.tick_params(axis="y", length=0); a.set_title("a", loc="left", fontweight="bold")
bl = list(csv.DictReader(open(os.path.join(A.data, "baselines", "baselines.csv"), encoding="utf-8")))
base = {n: [100 * float(r["production_pass_all"]) for r in bl if r["agent"] == a] for n, a in
        (("Random search", "random search"), ("Bayesian optimisation", "Bayesian optimisation"))}
base["Oracle"] = [100, 100, 100]  # the oracle passes in every production batch on each campaign (answers/reference_submission_*.json)
rows = [(l.replace("\n", " "), [ppass(r) for r in runs if sysof(r) == k], c) for k, l, c in SYS] + [(n, v, "#8a8984") for n, v in base.items()]
for i, (n, v, c) in enumerate(rows):
    b.scatter(v, [i] * len(v), s=16, color=c, alpha=0.85, lw=0, zorder=3)
    b.plot([min(v), max(v)], [i, i], color=c, lw=0.8, alpha=0.6, zorder=2)
b.set_yticks(range(len(rows))); b.set_yticklabels([n for n, _, _ in rows]); b.invert_yaxis(); b.tick_params(axis="y", length=0)
b.axhline(4.5, color=GRID, lw=0.8); b.set_xlim(-5, 105); b.set_xlabel("Production batches passing (%)\none point per run")
b.set_title("b", loc="left", fontweight="bold")
fig.tight_layout(); save(fig, "fig3_overall_scores")

# Figure 4: capability profiles
import numpy as np
M = np.array([[S["systems"][k]["capabilities"][c]["mean"] for k, _, _ in SYS] for c in CAPS])
fig, ax = plt.subplots(figsize=(5.2, 3.9))
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
im = ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
for i in range(len(CAPS)):
    for j in range(5):
        lo, hi = S["systems"][SYS[j][0]]["capabilities"][CAPS[i]]["90"]
        ax.text(j, i - 0.08, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=7.5, color="white" if M[i, j] > 0.55 else INK)
        ax.text(j, i + 0.27, f"{lo:.2f}–{hi:.2f}", ha="center", va="center", fontsize=5, color="white" if M[i, j] > 0.55 else INK2)
ax.set_xticks(range(5)); ax.set_xticklabels([l for _, l, _ in SYS], fontsize=7); ax.xaxis.tick_top()
ax.set_yticks(range(len(CAPS))); ax.set_yticklabels(CAPS); ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.set_xticks(np.arange(-.5, 5), minor=True); ax.set_yticks(np.arange(-.5, 9), minor=True)
ax.grid(which="minor", color="white", lw=2); ax.tick_params(which="minor", length=0)
cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label("Capability score (fraction of criteria met)", fontsize=7); cb.outline.set_visible(False)
save(fig, "fig4_capability_profiles")

# Figure 6: harness cross-over
fig, (a, b) = plt.subplots(1, 2, figsize=(6.7, 2.9), gridspec_kw={"width_ratios": [0.8, 1.2]})
for k, dx, lab in (("opus55", -0.08, "Claude Code"), ("opus55ag", 0.08, "Antigravity")):
    means = []
    for ci, cmp in enumerate("ABC"):
        v = [ppass(r) for r in runs if sysof(r) == k and r["campaign"].strip().upper().startswith(cmp)]
        a.scatter([ci + dx] * len(v), v, s=22, color=COL[k], edgecolor="white", lw=0.8, zorder=3)
        means.append(sum(v) / len(v))
    a.plot([c + dx for c in range(3)], means, color=COL[k], lw=1.2, zorder=2, label=f"Opus 5.5 in {lab}")
a.set_xticks(range(3)); a.set_xticklabels(["Campaign A\n(two runs each)", "B", "C"]); a.set_ylabel("Production batches passing (%)")
a.set_ylim(0, 105); a.legend(frameon=False, fontsize=7, loc="lower right"); a.set_title("a", loc="left", fontweight="bold")
H = S["harness"]; sdw = S["sd_within"]
keymap = dict(zip(CAPS, ["delivery", "design", "information", "analysis", "critical", "adaptability", "insight", "resources", "integrity"]))
for i, c in enumerate(CAPS):
    h = H[c]; d = h["antigravity"] - h["claude_code"]; sd = sdw[keymap[c]]
    b.barh(i, 2 * sd, left=-sd, height=0.6, color=GRID, zorder=1)
    b.scatter([d], [i], s=30, color=COL["opus55ag"] if d > 0 else (COL["opus55"] if d < 0 else "#8a8984"), zorder=3, edgecolor="white", lw=0.8)
    b.text(0.33, i, f"P = {h['p_antigravity_higher']:.2f}" if c != "Data analysis" else "both 1.00", va="center", fontsize=6.5, color=INK2)
b.axvline(0, color=INK2, lw=0.6); b.set_yticks(range(9)); b.set_yticklabels(CAPS); b.invert_yaxis(); b.tick_params(axis="y", length=0)
b.set_xlim(-0.25, 0.45); b.set_xlabel("Antigravity minus Claude Code (capability score)")
b.set_title("b", loc="left", fontweight="bold")
fig.tight_layout(); save(fig, "fig6_harness_crossover")

# Figure S1: threshold sensitivity
rows = list(csv.DictReader(open(os.path.join(A.out, "sensitivity_summary.csv"), encoding="utf-8")))
one = [r for r in rows if ":" in r["perturbation"] and not r["perturbation"].startswith("ALL")]
cols = {"fable52": "Fable 5.2", "carbon": "Carbon", "opus55ag": "Opus 5.5 (Antigravity)", "opus55": "Opus 5.5 (Claude Code)", "hydrogen": "Hydrogen"}
fig, ax = plt.subplots(figsize=(4.6, 2.4))
for i, (k, l, c) in enumerate(SYS):
    v = [float(r[cols[k]]) for r in one]; bl = float(rows[0][cols[k]])
    st = float(next(r for r in rows if r["perturbation"] == "ALL:stricter")[cols[k]]); le = float(next(r for r in rows if r["perturbation"] == "ALL:easier")[cols[k]])
    ax.plot([min(v), max(v)], [i, i], color=c, lw=5, alpha=0.45, solid_capstyle="round")
    ax.scatter([bl], [i], s=30, color=c, edgecolor="white", lw=1, zorder=3)
    ax.scatter([st, le], [i, i], marker="|", s=60, color=INK2, zorder=3)
ax.set_yticks(range(5)); ax.set_yticklabels([l.replace("\n", " ") for _, l, _ in SYS]); ax.invert_yaxis(); ax.tick_params(axis="y", length=0)
ax.set_xlabel("Capability score (of 100)"); ax.set_xlim(70, 96)
ax.set_title("dot: as scored  ·  band: 56 single-threshold moves  ·  ticks: all thresholds stricter / easier", fontsize=6.5, color=INK2, loc="left")
save(fig, "figS1_threshold_sensitivity")

# Figure S2: time vs score
fig, ax = plt.subplots(figsize=(3.4, 2.6))
for k, l, c in SYS:
    rr = [r for r in runs if sysof(r) == k]
    ax.scatter([mins(r) for r in rr], [float(r["capability_score_100"]) for r in rr], s=22, color=c, edgecolor="white", lw=0.8, label=l.replace("\n", " "))
ax.set_xlabel("Wall-clock time per run (min)"); ax.set_ylabel("Capability score (of 100)"); ax.set_xlim(0, 100)
ax.legend(frameon=False, fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
save(fig, "figS2_time_vs_score")
print("figures written to", OUT)
