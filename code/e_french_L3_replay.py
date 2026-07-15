"""PREREG D2: replay arm on the French L3 walk-forward battery.

Pre-registered in ../PREREG_FRENCH49.md (pre-registration D, D2 + the
implementation register) BEFORE this script was first run.

Mirrors the walkforward block of e_french_L3.py EXACTLY (same per-arm
seeding 1311*s+17, K=2, hard memory, probe 15, min_dormancy 90, dd 15%),
with arms {A1, A9, A5, A6, A1r-replay-erm, A1r-replay-inv}, 20 seeds.

Output: ../results/e_french49_L3_replay.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, EXTRA_ARM_FACTORIES, run_arm, welch, holm
from run_experiments import summarize, PROBE
from realdata import RealMarket
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      dormancy_diag, K_SEL, W_MAX, RESULTS)
from e_french_L3 import label_L3

ARMS = ["A1-monolith-erm", "A9-oracle-pinned", "A5-risp-erm", "A6-risp-inv",
        "A1r-replay-erm", "A1r-replay-inv"]
PAIRS = [
    # D2 replay family
    ("A1r-replay-erm", "A9-oracle-pinned"),
    ("A1r-replay-erm", "A1-monolith-erm"),
    ("A6-risp-inv", "A1r-replay-erm"),
    ("A6-risp-inv", "A1r-replay-inv"),
    ("A1r-replay-inv", "A9-oracle-pinned"),
    ("A1r-replay-inv", "A1r-replay-erm"),
    # applicable original prereg pairs (context)
    ("A6-risp-inv", "A5-risp-erm"),
    ("A6-risp-inv", "A1-monolith-erm"),
    ("A5-risp-erm", "A1-monolith-erm"),
    ("A6-risp-inv", "A9-oracle-pinned"),
]


def paired_gamma(res, a, b, key="post_react"):
    d = np.array(res[a][key]) - np.array(res[b][key])
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

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    factories = {**ARM_FACTORIES, **EXTRA_ARM_FACTORIES}
    mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
    sched = mkt.schedule()
    diag = dormancy_diag(sched)
    print(f"[D2/L3-replay/wf] dormancy diag: {diag}", flush=True)

    res = {a: {"overall": [], "post_react": []} for a in ARMS}
    bursts = {a: [] for a in ARMS}
    t0 = time.time()
    for s in range(seeds):
        for a in ARMS:
            arm = factories[a](cfg, np.random.default_rng(1311 * s + 17),
                               2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=90)
            res[a]["overall"].append(m["overall"])
            res[a]["post_react"].append(m["post_react"])
            nb = getattr(getattr(arm, "s", None), "n_burst_refits", None)
            if nb is not None:
                bursts[a].append(nb)
        print(f"  seed {s} done ({time.time()-t0:.0f}s)", flush=True)

    pv = {}
    for a, b in PAIRS:
        _, p = welch(res[a]["post_react"], res[b]["post_react"])
        pv[f"{a} vs {b}"] = p
    gammas = {
        "gate2_A1_minus_A9": paired_gamma(res, "A1-monolith-erm",
                                          "A9-oracle-pinned"),
        "replay_A1r_erm_minus_A9": paired_gamma(res, "A1r-replay-erm",
                                                "A9-oracle-pinned"),
        "replay_A1r_inv_minus_A9": paired_gamma(res, "A1r-replay-inv",
                                                "A9-oracle-pinned"),
        "deficit_closed_A1_minus_A1r_erm": paired_gamma(
            res, "A1-monolith-erm", "A1r-replay-erm"),
        "A1r_erm_minus_A6": paired_gamma(res, "A1r-replay-erm",
                                         "A6-risp-inv"),
        "A1r_inv_minus_A6": paired_gamma(res, "A1r-replay-inv",
                                         "A6-risp-inv"),
    }
    out = {"config": {"seeds": seeds, "K": 2, "memory": "hard",
                      "probe": PROBE, "min_dormancy": 90,
                      "dd_thresh": 0.15, "seeding": "1311*s+17",
                      "arms": ARMS, "diag": diag},
           "post_react": summarize({a: res[a]["post_react"] for a in ARMS}),
           "overall": summarize({a: res[a]["overall"] for a in ARMS}),
           "welch_p": pv, "holm_p": holm(pv),
           "paired_gammas": gammas,
           "burst_refits_per_run": {a: float(np.mean(b))
                                    for a, b in bursts.items() if b},
           "raw": res}
    with open(RESULTS / "e_french49_L3_replay.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    for k, g in gammas.items():
        print(f"[D2] {k}: {g['mean']:+.5f} ± {g['ci95']:.5f} "
              f"sig={g['positive_significant']}", flush=True)
    print("D2 REPLAY BATTERY COMPLETE", flush=True)


if __name__ == "__main__":
    main()
