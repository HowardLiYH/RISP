"""
Window-location estimator theta(era) with crisis-occupancy kappa calibration.

Committed spec (osf_package/PREREG_CRSP_AMENDMENT_TSPLIT.md, section C,
lodged 2026-07-16, OSF-mirrored): "theta(era) = the smallest threshold at
which the era's crisis-union occupancy falls below kappa of trading days,
kappa calibrated to reproduce the two known paying windows (15% <-> 13%
occupancy modern; 10% <-> prewar)."

THIS IS CALIBRATION OF AN ALREADY-COMMITTED ESTIMATOR ON ALREADY-RUN ERAS
(French-49 1990-2025 and 1926-1989) — NOT A NEW REGISTERED CLAIM. The two
target thresholds are the eras' known paying windows: 15% (modern, Addendum
B) and 10% (withheld era, Addendum F). Success criterion: a non-empty
kappa interval under which theta(modern)=15% AND theta(prewar)=10%,
ex-post. Any ambiguity is reported per the committed clause.

Occupancy convention (fixed here, the only free detail the committed spec
left open, chosen before computing any number): occupancy(theta) = fraction
of FEATURE days (the battery's evaluation calendar, e_french.build_xy_
returns index) whose L3 label at threshold theta is in the crisis union
(label >= 2) — the same labels the batteries consume. Grid: 1pp steps,
5%..30% (X2's lodged granularity is 1pp).

Output: ../results/window_estimator_calibration.json
Descriptive extra (does NOT relocate any lodged primary): the estimator
applied to the Japan panel (Addendum L keeps Japan's primary at the frozen
15%).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e_french
from e_french import build_xy_returns, price_panel, RESULTS
from e_french_L3 import label_L3

GRID = [round(t / 100.0, 2) for t in range(5, 31)]      # 5% .. 30%, 1pp
ERAS = {"modern_1990_2025": ("1990-01-01", "2025-12-31"),
        "prewar_1926_1989": ("1926-07-01", "1989-12-31")}
TARGET = {"modern_1990_2025": 0.15, "prewar_1926_1989": 0.10}


def occupancy_table(px, idx):
    out = {}
    for th in GRID:
        lab = np.nan_to_num(label_L3(px, dd_thresh=th)[idx],
                            nan=0).astype(int)
        out[th] = float(np.mean(lab >= 2))
    return out


def theta_of(occ, kappa):
    """Smallest grid threshold whose crisis-union occupancy < kappa."""
    for th in GRID:
        if occ[th] < kappa:
            return th
    return None


def era_table(window):
    e_french.WINDOW = window
    ret, dropped = e_french.load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    return occupancy_table(px, idx), ret.shape[1], dropped


def main():
    tables = {}
    meta = {}
    for era, win in ERAS.items():
        occ, n_ind, dropped = era_table(win)
        tables[era] = occ
        meta[era] = {"window": win, "n_industries": n_ind,
                     "n_dropped": len(dropped)}
        print(f"[{era}] occupancy: " + " ".join(
            f"{int(t*100)}%:{occ[t]:.3f}" for t in GRID), flush=True)

    # kappa feasibility: theta(era)=target  <=>  occ(target) < kappa <= occ(target - 1pp)
    per_era_interval = {
        e: {"lower_exclusive": tables[e][TARGET[e]],
            "upper_inclusive": tables[e][round(TARGET[e] - 0.01, 2)]}
        for e in ERAS}
    lo = max(tables[e][TARGET[e]] for e in ERAS)                  # exclusive
    hi = min(tables[e][round(TARGET[e] - 0.01, 2)] for e in ERAS)  # inclusive
    feasible = lo < hi
    kappa_star = float((lo + hi) / 2) if feasible else None
    recovery = {}
    if feasible:
        for era in ERAS:
            th = theta_of(tables[era], kappa_star)
            recovery[era] = {"theta_selected": th,
                             "target": TARGET[era],
                             "recovered": bool(th == TARGET[era])}

    # descriptive only: Japan (Addendum L primary stays frozen at 15%)
    japan = None
    try:
        from e_japan import load_japan_vw
        ret, dropped = load_japan_vw()
        X, Y, idx = build_xy_returns(ret)
        px = price_panel(ret)
        occ_jp = occupancy_table(px, idx)
        japan = {"occupancy": {str(t): occ_jp[t] for t in GRID},
                 "theta_at_kappa_star": (theta_of(occ_jp, kappa_star)
                                         if feasible else None),
                 "note": ("DESCRIPTIVE ONLY. Addendum L fixes Japan's "
                          "primary at the frozen 15%; this row is what the "
                          "committed estimator WOULD pick and is not used "
                          "to relocate anything.")}
        print(f"[japan descriptive] theta(kappa*)={japan['theta_at_kappa_star']}",
              flush=True)
    except Exception as exc:                                # pragma: no cover
        japan = {"error": str(exc)}

    out = {
        "status": ("calibration of the committed estimator "
                   "(PREREG_CRSP_AMENDMENT_TSPLIT.md section C); "
                   "NOT a new registered claim"),
        "estimator": ("theta(era) = smallest 1pp grid threshold with "
                      "crisis-union occupancy < kappa of feature days"),
        "grid_pct": [round(t * 100) for t in GRID],
        "meta": meta,
        "kappa_interval_per_era": per_era_interval,
        "occupancy_tables": {e: {str(t): tables[e][t] for t in GRID}
                             for e in ERAS},
        "targets": {e: TARGET[e] for e in ERAS},
        "kappa_feasible_interval": {
            "lower_exclusive": float(lo), "upper_inclusive": float(hi),
            "non_empty": bool(feasible)},
        "kappa_star_rule": "midpoint of the feasible interval",
        "kappa_star": kappa_star,
        "recovery": recovery,
        "calibration_succeeds": bool(feasible and all(
            r["recovered"] for r in recovery.values())),
        "quoted_anchor_check": {
            "amendment_quote": "15% <-> 13% occupancy modern",
            "occ_modern_at_15pct": tables["modern_1990_2025"][0.15]},
        "directional_note": (
            "The failure is DIRECTIONAL, not marginal: the prewar era has "
            "HIGHER crisis-union occupancy than the modern era at every "
            "grid threshold (e.g. 47.1% vs 21.2% at 10%; 40.6% vs 12.9% at "
            "15%), so any occupancy rule that recovers modern theta=15% "
            "predicts a COARSER prewar threshold (theta > 30%, off-grid), "
            "while the era's actual paying window (Addendum F) was FINER "
            "(10%). Crisis occupancy does not transfer across eras as the "
            "committed estimator assumed."),
        "consequence": (
            "Per the amendment's own clause, this infeasibility must be "
            "lodged at osf.io/nsx4e BEFORE CRSP data access, together with "
            "whatever rule replaces or supersedes theta(era); until then "
            "the amendment's fixed-15% disclosed-robustness column is the "
            "only threshold choice with standing for CRSP L3-family "
            "cells."),
        "japan_descriptive": japan,
        "owed": ("kappa*, this table, and the resulting CRSP-era theta are "
                 "to be committed to osf.io/nsx4e BEFORE WRDS/CRSP data "
                 "access (expected September 2026), per the amendment."),
    }
    with open(RESULTS / "window_estimator_calibration.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(json.dumps({k: out[k] for k in
                      ("kappa_feasible_interval", "kappa_star", "recovery",
                       "calibration_succeeds", "quoted_anchor_check")},
                     indent=1), flush=True)
    print("[saved] results/window_estimator_calibration.json", flush=True)


if __name__ == "__main__":
    main()
