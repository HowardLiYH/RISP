"""PREREG J D8: probe-length / dormancy-threshold sensitivity, French L3 wf.

Pre-registered in ../PREREG_FRENCH49.md (Addendum J, 2026-07-20, commit
c742c5c pushed) BEFORE this script was written or run.

Cells (6 unique of 7 lodged): probe {5,10,15,30} x min_dormancy 90, and
min_dormancy {60,90,120} x probe 15; (15,90) is the registered primary
re-read at 10 seeds. As declared in the registration, probe and
min_dormancy enter run_arm ONLY through the post-hoc evaluation masks,
so each seed's daily trajectory is computed ONCE (arms A1, A9, seeding
1311*s+17, s in 0..9) and the cells are measurement re-reads of the same
10 trajectories -- exactly like-for-like across cells by construction.
The mask logic below replicates run_arm's post_react computation
verbatim (probe window from each qualifying reactivation, clipped to the
evaluated second half).

Output: ../results/e_french49_L3_sensitivity.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, run_arm
from realdata import RealMarket
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      dormancy_diag, K_SEL, W_MAX, RESULTS)
from e_french_L3 import label_L3

ARMS = ["A1-monolith-erm", "A9-oracle-pinned"]
CELLS = [(5, 90), (10, 90), (15, 90), (30, 90), (15, 60), (15, 120)]
SEEDS = 10


def post_react_from_daily(daily, sched, probe, min_dorm):
    """Replicates run_arm's post_react + n_react for arbitrary (probe,
    min_dormancy) from a stored daily-regret trajectory."""
    T = sched.T
    react = sched.reactivation_days(min_dorm)
    probe_mask = np.zeros(T, dtype=bool)
    for t0 in react:
        probe_mask[t0:t0 + probe] = True
    half = int(T * 0.5)
    sel = probe_mask & (np.arange(T) >= half)
    pr = float(daily[sel].mean()) if sel.any() else float("nan")
    n_react = int(sum(1 for t0 in react if t0 >= half))
    return pr, n_react


def main(seeds=SEEDS):
    ret, dropped = load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
    sched = mkt.schedule()
    diag = dormancy_diag(sched)
    print(f"[J/D8/L3-sens/wf] dormancy diag: {diag}", flush=True)

    # one trajectory per (seed, arm); cells are measurement re-reads
    dailies = {a: [] for a in ARMS}
    t0 = time.time()
    for s in range(seeds):
        for a in ARMS:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(1311 * s + 17),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=15, min_dormancy=90)
            dailies[a].append(m["daily"])
        print(f"  seed {s} done ({time.time()-t0:.0f}s)", flush=True)

    cells_out = {}
    for probe, dorm in CELLS:
        pr = {a: [] for a in ARMS}
        n_react = None
        for s in range(seeds):
            for a in ARMS:
                v, nr = post_react_from_daily(dailies[a][s], sched,
                                              probe, dorm)
                pr[a].append(v)
                n_react = nr
        d = np.array(pr["A1-monolith-erm"]) - np.array(pr["A9-oracle-pinned"])
        ci = float(1.96 * d.std(ddof=1) / np.sqrt(len(d)))
        key = f"probe{probe}_dorm{dorm}"
        cells_out[key] = {
            "probe": probe, "min_dormancy": dorm, "n_react": n_react,
            "gamma_A1_minus_A9": {"mean": float(d.mean()), "ci95": ci,
                                  "positive_significant": bool(
                                      d.mean() - ci > 0)},
            "post_react_A1": {"mean": float(np.mean(pr["A1-monolith-erm"])),
                              "ci95": float(1.96 * np.std(
                                  pr["A1-monolith-erm"], ddof=1)
                                  / np.sqrt(seeds))},
            "post_react_A9": {"mean": float(np.mean(pr["A9-oracle-pinned"])),
                              "ci95": float(1.96 * np.std(
                                  pr["A9-oracle-pinned"], ddof=1)
                                  / np.sqrt(seeds))},
            "raw_gamma_per_seed": d.tolist(),
        }
        g = cells_out[key]["gamma_A1_minus_A9"]
        print(f"[D8] {key}: G={g['mean']:+.5f} ± {g['ci95']:.5f} "
              f"sig={g['positive_significant']} n_react={n_react}",
              flush=True)

    out = {"config": {"seeds": seeds, "K": 2, "memory": "hard",
                      "dd_thresh": 0.15, "seeding": "1311*s+17",
                      "arms": ARMS, "cells": CELLS, "diag": diag,
                      "design": ("shared trajectories; probe/min_dormancy "
                                 "are measurement-only (Addendum J D8)"),
                      "prereg": "Addendum J D8, spec commit c742c5c"},
           "cells": cells_out}
    with open(RESULTS / "e_french49_L3_sensitivity.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("D8 SENSITIVITY BATTERY COMPLETE", flush=True)


if __name__ == "__main__":
    main()
