"""Reference reduction of vlab raw data files (used by the capability scorer and the baseline agents).

Each function takes a CSV path and returns derived quantities. These are deliberately
straightforward textbook reductions; a strong agent should arrive at the same numbers.
"""
import csv
import math
import sys
from collections import defaultdict

import numpy as np


def _rows(path):
    with open(path) as fh:
        lines = [l for l in fh if not l.startswith("#")]
    return list(csv.DictReader(lines))


def _meta(path):
    meta = {}
    with open(path) as fh:
        for l in fh:
            if l.startswith("# ") and ":" in l:
                k, v = l[2:].split(":", 1)
                meta[k.strip()] = v.strip()
    return meta


def tensile(path):
    by = defaultdict(list)
    for r in _rows(path):
        by[r["specimen_id"]].append(r)
    Es, uts = [], []
    for sid, rs in by.items():
        A = float(rs[0]["width_mm"]) * float(rs[0]["thickness_mm"])
        e = np.array([float(r["strain"]) for r in rs])
        s = np.array([float(r["force_N"]) for r in rs]) / A
        m = (e >= 0.0005) & (e <= 0.0025)
        Es.append(np.polyfit(e[m], s[m], 1)[0] / 1000)
        uts.append(s.max())
    return {"E_GPa": float(np.mean(Es)), "E_sd": float(np.std(Es, ddof=1)), "UTS_MPa": float(np.mean(uts)), "n": len(Es)}


def senb(path):
    by = defaultdict(list)
    for r in _rows(path):
        by[r["specimen_id"]].append(r)
    Ks = []
    for sid, rs in by.items():
        W, B, a = (float(rs[0][k]) for k in ("W_mm", "B_mm", "a_mm"))
        P = max(float(r["load_N"]) for r in rs) / 1000  # kN
        x = a / W
        f = 6 * math.sqrt(x) * (1.99 - x * (1 - x) * (2.15 - 3.93 * x + 2.7 * x * x)) / ((1 + 2 * x) * (1 - x) ** 1.5)
        Ks.append(P / ((B / 10) * math.sqrt(W / 10)) * f)
    return {"K_MPa_m05": float(np.mean(Ks)), "K_sd": float(np.std(Ks, ddof=1)), "n": len(Ks)}


def resist4(path):
    by = defaultdict(list)
    for r in _rows(path):
        if r["status"] == "OK":
            by[r["bar_id"]].append((float(r["current_A"]), float(r["inner_voltage_V"])))
    rhos = []
    for bid, pts in by.items():
        I = np.array([p[0] for p in pts]); V = np.array([p[1] for p in pts])
        if len(I) < 2:
            continue
        R = np.polyfit(I, V, 1)[0] if len(I) > 2 else V[-1] / I[-1]
        rhos.append(R * (10e-3 * 4e-3) / 20e-3 * 100)  # ohm cm
    return {"rho_ohm_cm": float(np.exp(np.mean(np.log(rhos)))) if rhos else float("nan"), "n": len(rhos)}


def resist2(path):
    by = defaultdict(list)
    for r in _rows(path):
        by[r["bar_id"]].append((float(r["applied_voltage_V"]), float(r["current_A"])))
    rhos = []
    for bid, pts in by.items():
        V = np.array([p[0] for p in pts]); I = np.array([p[1] for p in pts])
        G = np.polyfit(V, I, 1)[0]
        if G <= 0:
            continue
        rhos.append((1 / G) * (10e-3 * 4e-3) / 50e-3 * 100)
    return {"rho_ohm_cm": float(np.exp(np.mean(np.log(rhos)))) if rhos else float("nan"), "n": len(rhos)}


def density(path):
    rh = []
    for r in _rows(path):
        ma, mw, T = float(r["mass_in_air_g"]), float(r["apparent_mass_in_water_g"]), float(r["water_temp_C"])
        rw = 0.99820 - 0.00021 * (T - 20)
        rh.append(ma * rw / (ma - mw))
    return {"rho_g_cm3": float(np.mean(rh))}


def dsc(path):
    rows = _rows(path)
    out = {}
    for scan in ("1", "2"):
        T = np.array([float(r["temperature_C"]) for r in rows if r["scan"] == scan])
        H = np.array([float(r["heat_flow_W_per_g"]) for r in rows if r["scan"] == scan])
        k = 9
        Hs = np.convolve(H, np.ones(k) / k, mode="same")
        dH = np.gradient(Hs, T)
        win = (T > 60) & (T < 220)
        i = np.argmin(np.where(win, dH, 0))  # steepest downward step (endothermic Cp step)
        out[f"Tg_scan{scan}_C"] = float(T[i])
    # residual exotherm area on scan 1 above Tg (relative to scan 2 as baseline)
    T1 = np.array([float(r["temperature_C"]) for r in rows if r["scan"] == "1"])
    H1 = np.array([float(r["heat_flow_W_per_g"]) for r in rows if r["scan"] == "1"])
    H2 = np.array([float(r["heat_flow_W_per_g"]) for r in rows if r["scan"] == "2"])
    m = T1 > out["Tg_scan1_C"] + 8
    diff = np.clip(H1[m] - H2[m], 0, None)
    out["residual_J_per_g"] = float(np.trapezoid(diff, T1[m]) / (10 / 60))
    return out


def indium(path):
    rows = _rows(path)
    T = np.array([float(r["temperature_C"]) for r in rows]); H = np.array([float(r["heat_flow_mW"]) for r in rows])
    base = np.median(H[:50])
    i = np.argmax(H < base - 0.5)
    return {"onset_C": float(T[i]), "offset_vs_certified_C": float(T[i] - 156.60)}


def bet(path):
    rows = _rows(path)
    x = np.array([float(r["relative_pressure_P_P0"]) for r in rows]); v = np.array([float(r["volume_adsorbed_cm3STP_per_g"]) for r in rows])
    m = (x >= 0.05) & (x <= 0.30)
    y = x[m] / (v[m] * (1 - x[m]))
    s, c0 = np.polyfit(x[m], y, 1)
    vm = 1 / (s + c0)
    ssa = vm * 4.353
    return {"SSA_m2_g": float(ssa), "thickness_nm_est": float(2 / (2.2e6 * ssa) * 1e9)}


def xrd(path, lo=20, hi=32):
    rows = _rows(path)
    tt = np.array([float(r["two_theta_deg"]) for r in rows]); I = np.array([float(r["intensity_counts"]) for r in rows])
    m = (tt > lo) & (tt < hi)
    t, y = tt[m], I[m]
    base = np.linspace(np.median(y[:10]), np.median(y[-10:]), len(y))
    yy = np.convolve(y - base, np.ones(5) / 5, mode="same")
    j = np.argmax(yy); half = yy[j] / 2
    l = j
    while l > 0 and yy[l] > half: l -= 1
    r = j
    while r < len(yy) - 1 and yy[r] > half: r += 1
    fw = t[r] - t[l]
    beta = math.radians(math.sqrt(max(fw ** 2 - 0.08 ** 2, 1e-6)))
    Lc = 0.9 * 0.15406 / (beta * math.cos(math.radians(t[j] / 2)))
    return {"peak_deg": float(t[j]), "fwhm_deg": float(fw), "Lc_nm": float(Lc)}


if __name__ == "__main__":
    kind, path = sys.argv[1], sys.argv[2]
    print(globals()[kind](path))
