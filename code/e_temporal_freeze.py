"""Temporal-deployment freeze (PREREG_TEMPORAL_DEPLOYMENT.md, OSF-lodged
2026-07-15 23:35 ET): compute the frozen diagnostics on all data through
2026-06-30 and commit. Vendored panel ends 2026-05-29 (Ken French 2026-05
build) — all available data <= freeze date; noted per the registration."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e_french
from e_french import build_xy_returns, price_panel, dormancy_diag
from e_french_L3 import label_L3
from e_french_nber import label_LNBER
from risp import ARM_FACTORIES, run_arm
from realdata import RealMarket
from run_experiments import PROBE

e_french.WINDOW = ("1990-01-01", "2026-06-30")
ret, dropped = e_french.load_french_vw()
X, Y, idx = build_xy_returns(ret)
px = price_panel(ret)
out = {"freeze_date": "2026-06-30", "panel_end": str(ret.index[-1].date()),
       "note": "all published data <= freeze date; panel is the vendored 2026-05 build",
       "cells": {}}
labels = {"L-NBER-primary": np.nan_to_num(label_LNBER(px, "announced")[idx], nan=0).astype(int),
          "L3-15pct": np.nan_to_num(label_L3(px, dd_thresh=0.15)[idx], nan=0).astype(int)}

class Cfg: n_assets, d, k, w_max, R = X.shape[1], X.shape[2], 5, 0.2, 4

for name, lab in labels.items():
    mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
    sched = mkt.schedule()
    diffs = []
    for s in range(20):
        vals = {}
        for a in ("A1-monolith-erm", "A9-oracle-pinned"):
            arm = ARM_FACTORIES[a](Cfg(), np.random.default_rng(1311*s+17), 2, "hard")
            m = run_arm(arm, mkt, sched, Cfg(), probe=PROBE, min_dormancy=90)
            vals[a] = m["post_react"]
        diffs.append(vals["A1-monolith-erm"] - vals["A9-oracle-pinned"])
    d_arr = np.array(diffs)
    g = {"mean": float(d_arr.mean()),
         "ci95": float(1.96*d_arr.std(ddof=1)/np.sqrt(len(d_arr))),
         "sign": "positive" if d_arr.mean() > 0 else "nonpositive",
         "significant": bool(abs(d_arr.mean()) > 1.96*d_arr.std(ddof=1)/np.sqrt(len(d_arr)))}
    out["cells"][name] = {"gamma_frozen": g, "raw": d_arr.tolist()}
    print(f"{name}: Γ̂_frozen = {g['mean']:+.5f} ± {g['ci95']:.5f} ({g['sign']}, sig={g['significant']})", flush=True)

with open(Path(__file__).resolve().parent / ".." / "results" / "temporal_freeze_2026-06-30.json", "w") as fh:
    json.dump(out, fh, indent=1)
print("FREEZE COMMITTED")
