"""PREREG K K3: decision-layer perturbation (top-k robustness), French L3.

Pre-registered in ../PREREG_FRENCH49.md (Addendum K, 2026-07-20, commit
a02b9f8 pushed) BEFORE this script was written. Mirrors the walkforward
block of e_french_L3.py EXACTLY (per-arm seeding 1311*s+17, K=2, hard
memory, probe 15, min_dormancy 90, dd 15%) except the decision layer:
two cells, (k=3, w_max=1/3) and (k=10, w_max=0.1), both holding gross
exposure k*w_max = 1.0 as in the headline (k=5, w_max=0.2). Arms
[A1, A9, A5, A6], 20 seeds.

Output: ../results/e_french49_L3_topk.json
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
                      dormancy_diag, RESULTS)
from e_french_L3 import label_L3

ARMS = ["A1-monolith-erm", "A9-oracle-pinned", "A5-risp-erm", "A6-risp-inv"]
PAIRS = [("A6-risp-inv", "A5-risp-erm"),
         ("A6-risp-inv", "A1-monolith-erm"),
         ("A5-risp-erm", "A1-monolith-erm"),
         ("A6-risp-inv", "A9-oracle-pinned"),
         ("A5-risp-erm", "A9-oracle-pinned"),
         ("A1-monolith-erm", "A9-oracle-pinned")]
CELLS = [("k3_wmax0.333", 3, 1.0 / 3.0),
         ("k10_wmax0.1", 10, 0.1)]


def paired(res, a, b):
    d = np.array(res[a]["post_react"]) - np.array(res[b]["post_react"])
    return {"pair": f"{a} - {b}",
            "mean": float(d.mean()),
            "ci95": float(1.96 * d.std(ddof=1) / np.sqrt(len(d))),
            "positive_significant": bool(
                d.mean() - 1.96 * d.std(ddof=1) / np.sqrt(len(d)) > 0)}


def main(seeds=20):
    ret, dropped = load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
    mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
    sched = mkt.schedule()
    diag = dormancy_diag(sched)
    print(f"[K3/L3-topk/wf] dormancy diag: {diag}", flush=True)

    out = {"config": {"seeds": seeds, "K": 2, "memory": "hard",
                      "probe": PROBE, "min_dormancy": 90,
                      "dd_thresh": 0.15, "seeding": "1311*s+17",
                      "arms": ARMS, "diag": diag,
                      "gross_exposure": "k*w_max = 1.0 in both cells "
                                        "(headline: k=5, w_max=0.2)",
                      "prereg": "Addendum K K3, spec commit a02b9f8"},
           "cells": {}}
    from types import SimpleNamespace
    for name, k_sel, wmax in CELLS:
        cfg = SimpleNamespace(n_assets=X.shape[1], d=X.shape[2],
                              k=k_sel, w_max=wmax, R=4)
        res = {a: {"overall": [], "post_react": []} for a in ARMS}
        t0 = time.time()
        for s in range(seeds):
            for a in ARMS:
                arm = ARM_FACTORIES[a](cfg, np.random.default_rng(
                    1311 * s + 17), 2, "hard")
                m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                            min_dormancy=90)
                res[a]["overall"].append(m["overall"])
                res[a]["post_react"].append(m["post_react"])
            print(f"  [{name}] seed {s} done ({time.time()-t0:.0f}s)",
                  flush=True)
        pv = {}
        for a, b in PAIRS:
            _, p = welch(res[a]["post_react"], res[b]["post_react"])
            pv[f"{a} vs {b}"] = p
        gamma = paired(res, "A1-monolith-erm", "A9-oracle-pinned")
        a6_a1 = paired(res, "A1-monolith-erm", "A6-risp-inv")
        out["cells"][name] = {
            "k": k_sel, "w_max": wmax,
            "post_react": summarize({a: res[a]["post_react"] for a in ARMS}),
            "overall": summarize({a: res[a]["overall"] for a in ARMS}),
            "welch_p": pv, "holm_p": holm(pv),
            "gamma_A1_minus_A9": gamma,
            "A1_minus_A6": a6_a1,
            "A6_below_A1_direction": bool(a6_a1["mean"] > 0),
            "raw": res}
        print(f"[K3] {name}: Gamma={gamma['mean']:+.6f}±{gamma['ci95']:.6f} "
              f"sig={gamma['positive_significant']} "
              f"A1-A6={a6_a1['mean']:+.6f}±{a6_a1['ci95']:.6f} "
              f"A6<A1={a6_a1['mean'] > 0}", flush=True)
    with open(RESULTS / "e_french49_L3_topk.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("K3 TOPK BATTERY COMPLETE", flush=True)


if __name__ == "__main__":
    main()
