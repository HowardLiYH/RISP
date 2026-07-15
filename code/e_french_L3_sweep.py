"""L3 threshold-robustness sweep (PRE-REGISTRATION C in PREREG_FRENCH49.md).

Walk-forward only (the design where the L3 effect lives), thresholds
10/12/20% (15% = the existing e_french49_L3_dissoc.json walkforward).
Output: ../results/e_french49_L3_sweep.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, run_arm, welch, holm
from run_experiments import summarize, PROBE
from realdata import RealMarket
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      dormancy_diag, ARMS, PAIRS, K_SEL, W_MAX, RESULTS)
from e_french_L3 import label_L3

ret, _ = load_french_vw()
X, Y, idx = build_xy_returns(ret)
px = price_panel(ret)


class Cfg:
    n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4


out = {}
for thresh in (0.10, 0.12, 0.20):
    lab = np.nan_to_num(label_L3(px, dd_thresh=thresh)[idx], nan=0).astype(int)
    mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
    sched = mkt.schedule()
    diag = dormancy_diag(sched)
    res = {a: {"post_react": [], "overall": []} for a in ARMS}
    t0 = time.time()
    for s in range(20):
        for a in ARMS:
            arm = ARM_FACTORIES[a](Cfg(), np.random.default_rng(2117 * s + 41),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, Cfg(), probe=PROBE, min_dormancy=90)
            res[a]["post_react"].append(m["post_react"])
            res[a]["overall"].append(m["overall"])
    pv = {}
    for a, b in PAIRS:
        _, p = welch(res[a]["post_react"], res[b]["post_react"])
        pv[f"{a} vs {b}"] = p
    d_fg = (np.array(res["A1-monolith-erm"]["post_react"])
            - np.array(res["A9-oracle-pinned"]["post_react"]))
    gamma = {"mean": float(d_fg.mean()),
             "ci95": float(1.96 * d_fg.std(ddof=1) / np.sqrt(len(d_fg))),
             "positive_significant": bool(
                 d_fg.mean() - 1.96 * d_fg.std(ddof=1) / np.sqrt(len(d_fg)) > 0)}
    a1 = np.mean(res["A1-monolith-erm"]["post_react"])
    a5 = np.mean(res["A5-risp-erm"]["post_react"])
    a6 = np.mean(res["A6-risp-inv"]["post_react"])
    out[f"{int(thresh*100)}pct"] = {
        "diag": diag,
        "post_react": summarize({a: res[a]["post_react"] for a in ARMS}),
        "welch_p": pv, "holm_p": holm(pv),
        "gate2_forgetting_deficit": gamma,
        "ordering_holds": bool(a6 < a5 < a1),
        "raw": res}
    print(f"[{int(thresh*100)}%] Γ={gamma['mean']:.5f}±{gamma['ci95']:.5f} "
          f"sig={gamma['positive_significant']} A6<A5<A1={a6 < a5 < a1} "
          f"(A6 {a6:.5f} A5 {a5:.5f} A1 {a1:.5f}) "
          f"min raw p={min(pv.values()):.2g} ({(time.time()-t0)/60:.1f} min)",
          flush=True)
with open(RESULTS / "e_french49_L3_sweep.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print("SWEEP COMPLETE", flush=True)
