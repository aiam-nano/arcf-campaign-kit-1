"""Non-LLM baseline agents for the Composite Campaign .

  python baselines.py random|bo  --vlab /path/vlab --key campaign.key --work /tmp/run --seed 1

Both agents use the same CLI and budget as an LLM agent. Each evaluation makes a batch and measures
modulus, toughness, resistivity and DSC Tg; cost is computed from the catalogue rules. The random agent
samples recipes uniformly; the BO agent fits a Gaussian process to a desirability score and picks the
next recipe by upper confidence bound. Neither reads datasheets, logs or powders.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import ref_analysis as RA  # noqa: E402

SPEC = dict(E=3.90, K=0.84, rlo=1e4, rhi=1e8, Tg=140, cost=16.0)
GRADES = ["G1", "G2", "G3", "G4", "GO"]
TREATS = ["none", "silane", "dispersant"]


class Lab:
    def __init__(self, vlab, key, work):
        self.vlab, self.work = os.path.abspath(vlab), os.path.abspath(work)
        if os.path.exists(work):
            shutil.rmtree(work)
        os.makedirs(work)
        shutil.copy(key, os.path.join(work, "campaign.key"))
        self.prices = {}
        for line in self.run("catalogue").splitlines():
            m = re.match(r"\s+(G\d|GO)\s.*price GBP (\d+)/kg", line)
            if m:
                self.prices[m.group(1)] = float(m.group(2))

    def run(self, *args):
        r = subprocess.run([self.vlab, *args], cwd=self.work, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip())
        return r.stdout

    def remaining(self):
        m = re.search(r"\(([\d.]+) remaining\)", self.run("status"))
        return float(m.group(1))

    def last_file(self, out):
        m = re.search(r"-> (lab_data/\S+)", out)
        return os.path.join(self.work, m.group(1))


def cost_of(rc, prices):
    fc = prices[rc["filler"]] + {"none": 0, "silane": 40, "dispersant": 25}[rc["treat"]]
    if rc["filler"] == "GO":
        fc += 20 + rc["reduce"] / 10
    return (1 - rc["wt"] / 100) * 8 + rc["wt"] / 100 * fc


def args_of(rc):
    a = ["--filler", rc["filler"], "--wt", f"{rc['wt']:.2f}", "--sonic", f"{rc['sonic']:.0f}", "--passes", str(rc["passes"]),
         "--treat", rc["treat"], "--amine", f"{rc['amine']:.3f}", "--degas-stage", rc["stage"], "--degas-min", f"{rc['dmin']:.0f}",
         "--degas-temp", f"{rc['dtemp']:.0f}", "--cure", f"80:2,{rc['cureT']:.0f}:{rc['cureH']:.1f}"]
    if rc["filler"] == "GO":
        a += ["--reduce", f"{rc['reduce']:.0f}"]
    return a


def pot_life(T):
    return 90 * math.exp(-(T - 25) / 18)


def sample(rng):
    rc = dict(filler=GRADES[rng.integers(5)], wt=float(rng.uniform(0.5, 6)), sonic=float(rng.uniform(0, 400)), passes=int(rng.integers(0, 6)),
              treat=TREATS[rng.integers(3)], amine=float(rng.uniform(0.95, 1.12)), stage=["pre", "post"][rng.integers(2)],
              dtemp=float(rng.uniform(25, 70)), dmin=float(rng.uniform(5, 90)), cureT=float(rng.uniform(120, 175)), cureH=float(rng.uniform(1, 5)),
              reduce=float(rng.uniform(300, 1000)))
    if rc["stage"] == "post":
        rc["dmin"] = min(rc["dmin"], 0.75 * pot_life(rc["dtemp"]))
    return rc


def encode(rc):
    v = [GRADES.index(rc["filler"]) == i for i in range(5)] + [TREATS.index(rc["treat"]) == i for i in range(3)]
    v += [rc["wt"] / 6, rc["sonic"] / 400, rc["passes"] / 6, (rc["amine"] - 0.95) / 0.17, rc["stage"] == "pre", (rc["dtemp"] - 25) / 45,
          rc["dmin"] / 90, (rc["cureT"] - 120) / 55, (rc["cureH"] - 1) / 4, (rc["reduce"] - 300) / 700 if rc["filler"] == "GO" else 0]
    return np.array(v, dtype=float)


def evaluate(lab, rc):
    out = lab.run("make", *args_of(rc))
    b = re.search(r"(B\d{3}) made", out).group(1)
    if "GELLED" in out:
        return None
    E = RA.tensile(lab.last_file(lab.run("test", "tensile", "--batch", b, "--n", "3")))["E_GPa"]
    K = RA.senb(lab.last_file(lab.run("test", "senb", "--batch", b, "--n", "3")))["K_MPa_m05"]
    r4 = RA.resist4(lab.last_file(lab.run("test", "resist4", "--batch", b, "--n", "2")))["rho_ohm_cm"]
    rho = r4 if not math.isnan(r4) else RA.resist2(lab.last_file(lab.run("test", "resist2", "--batch", b, "--n", "2")))["rho_ohm_cm"]
    Tg = RA.dsc(lab.last_file(lab.run("test", "dsc", "--batch", b)))["Tg_scan1_C"]
    return dict(E=E, K=K, rho=rho, Tg=Tg, cost=cost_of(rc, lab.prices), batch=b)


def desirability(m):
    if m is None:
        return -10.0
    lr = math.log10(max(m["rho"], 1e-3))
    pen = [min(0, (m["E"] - SPEC["E"]) / 0.3), min(0, (m["K"] - SPEC["K"]) / 0.08), min(0, (lr - 4) / 1.0), min(0, (8 - lr) / 1.0),
           min(0, (m["Tg"] - SPEC["Tg"]) / 10), min(0, (SPEC["cost"] - m["cost"]) / 2)]
    return sum(pen) + (1.0 if all(p == 0 for p in pen) else 0)


def gp_ucb(X, y, cand, beta=2.0, ls=0.35, noise=1e-3):
    X, cand = np.array(X), np.array(cand)
    ym, ys = y.mean(), y.std() + 1e-9
    yn = (y - ym) / ys
    def k(a, b):
        d = ((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)
        return np.exp(-d / (2 * ls * ls * a.shape[1] / 8))
    Kxx = k(X, X) + noise * np.eye(len(X))
    L = np.linalg.cholesky(Kxx)
    alpha = np.linalg.solve(L.T, np.linalg.solve(L, yn))
    Ks = k(cand, X)
    mu = Ks @ alpha
    v = np.linalg.solve(L, Ks.T)
    var = np.clip(1 - (v * v).sum(0), 1e-9, None)
    return mu + beta * np.sqrt(var)


def run(kind, vlab, key, work, seed):
    rng = np.random.default_rng(seed)
    lab = Lab(vlab, key, work)
    hist = []
    per_eval = 110
    while lab.remaining() > per_eval:
        if kind == "random" or len(hist) < 6:
            rc = sample(rng)
        else:
            cands = [sample(rng) for _ in range(4000)]
            X = [encode(h[0]) for h in hist]
            y = np.array([h[2] for h in hist])
            ucb = gp_ucb(X, y, [encode(c) for c in cands])
            rc = cands[int(np.argmax(ucb))]
        try:
            m = evaluate(lab, rc)
        except RuntimeError as e:
            if "insufficient credits" in str(e):
                break
            raise
        hist.append((rc, m, desirability(m)))
    best = max(hist, key=lambda h: h[2])
    rc, m = best[0], best[1] or dict(E=3, K=0.7, rho=1e10, Tg=130)
    sub = {"recipe": {"filler": rc["filler"], "wt_pct": round(rc["wt"], 2), "sonication_kJ_per_g": round(rc["sonic"]), "three_roll_mill_passes": rc["passes"],
                      "surface_treatment": rc["treat"], "amine_ratio": round(rc["amine"], 3), "degas_stage": rc["stage"], "degas_min": round(rc["dmin"]),
                      "degas_temp_C": round(rc["dtemp"]), "cure": f"80:2,{rc['cureT']:.0f}:{rc['cureH']:.1f}", "reduce_temp_C": round(rc["reduce"]) if rc["filler"] == "GO" else 0},
           "predicted": {"modulus_GPa": [m["E"] * 0.93, m["E"], m["E"] * 1.07], "KIC_MPa_m05": [m["K"] * 0.9, m["K"], m["K"] * 1.1],
                         "resistivity_ohm_cm": [m["rho"] / 10, m["rho"], m["rho"] * 10], "Tg_C": [m["Tg"] - 6, m["Tg"], m["Tg"] + 6]},
           "answers": {}, "report_file": "report.md"}
    with open(os.path.join(work, "submission.json"), "w") as fh:
        json.dump(sub, fh, indent=1)
    with open(os.path.join(work, "report.md"), "w") as fh:
        fh.write(f"Baseline {kind}: best measured batch {m.get('batch')} with desirability {best[2]:.2f} after {len(hist)} evaluations.\n")
    m_day = float(re.search(r"day ([\d.]+)", lab.run("status")).group(1))
    if m_day < 20:
        lab.run("wait", "--days", str(20.5 - m_day))
    lab.run("questions", "--confirm")
    lab.run("submit", "submission.json")
    return len(hist), best[2]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["random", "bo"])
    ap.add_argument("--vlab", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    print(run(a.kind, a.vlab, a.key, a.work, a.seed))
