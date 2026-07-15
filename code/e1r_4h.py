"""
E1r-4H: the ten-arm dissociation on the gate-PASSING real substrate.

Protocol logic (pre-registered 2026-07-14, before running): E0-intraday's
confirmation pass (results/e0_intraday_confirm.json) CONFIRMED exploitable
regime structure on the decision metric for 4H crypto under the bar-native
L2 labeler (gap +3.15%, z=+2.32, p<1e-4, split-half stable). The
diagnostic-first protocol that predicted a null E1s under a failed gate
makes the opposite prediction here: with the gate passed, the arms SHOULD
dissociate in the pre-registered ordering
    A6 < A5 (approx A4) << reward-driven cluster (A1/A2/A3/A8b)
on post-reactivation regret. If they do not, the gate's sufficiency is
refuted — reported either way.

Design (mirrors e1s() in run_experiments.py, substitutions only):
  - Substrate: 4H OHLCV panel, rich 10-feature inventory (build_xy_rich),
    L2 bar-native labels — exactly the confirmed cell.
  - BlockLibrary min_len=6 bars (keeps 24 blocks / 211 bars of the rare
    vol-up regime 2, the dormancy target).
  - Schedule: 16 cycles over regimes {0,1,3} with lengths 20-45 bars;
    regime 2 dormant, activated every 3rd cycle for 12-24 bars;
    min_dormancy=80 bars, probe=15 bars (bar-native throughout, matching
    the labeler convention that passed the gate).
  - 20 seeds, K=2, hard memory, same ten arms, same 6-pair pre-registered
    Welch family + Holm.

Output: ../results/e1r_4h_crypto.json
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, run_arm, welch, holm
from run_experiments import summarize, PROBE
from realdata import label_L2, BlockLibrary, StitchedMarket
from e0_intraday import load_ohlcv_panel, build_xy_rich

RESULTS = Path(__file__).resolve().parent / ".." / "results"

ARMS = ["A1-monolith-erm", "A2-router", "A3-recentperf", "A4-randomfixed",
        "A5-risp-erm", "A6-risp-inv", "A7-monolith-inv",
        "A8a-hedge-fixed", "A8b-hedge-learn", "A9-oracle-pinned"]

PAIRS = [("A6-risp-inv", "A5-risp-erm"),
         ("A6-risp-inv", "A1-monolith-erm"),
         ("A5-risp-erm", "A2-router"),
         ("A5-risp-erm", "A1-monolith-erm"),
         ("A6-risp-inv", "A8b-hedge-learn"),
         ("A6-risp-inv", "A9-oracle-pinned")]


def main(seeds=20, K=2):
    fields = load_ohlcv_panel("4H")
    X, Y, idx = build_xy_rich(fields)
    lab = np.nan_to_num(label_L2(fields["close"])[idx], nan=-1)
    lib = BlockLibrary(X, Y, lab, np.arange(len(idx)), min_len=6)
    print("block counts:", lib.counts(), flush=True)

    class CfgReal:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], 2, 0.25, 4

    cfg = CfgReal()
    res = {a: {"overall": [], "post_react": []} for a in ARMS}
    t0 = time.time()
    for s in range(seeds):
        rng = np.random.default_rng(3000 + s)
        seq = []
        for cyc in range(16):
            for r in rng.permutation([0, 1, 3]):
                seq.append((int(r), int(rng.integers(20, 45))))
            if cyc % 3 == 2:
                seq.append((2, int(rng.integers(12, 24))))
        mkt = StitchedMarket(lib, rng)
        sched = mkt.materialize(seq)
        for a in ARMS:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(77 * s + 5),
                                   K, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=80)
            res[a]["overall"].append(m["overall"])
            res[a]["post_react"].append(m["post_react"])
        if s == 0:
            print(f"seed 0 done in {time.time()-t0:.1f}s; "
                  f"n_react={m['n_react']}, T={sched.T}", flush=True)
    pv = {}
    for a, b in PAIRS:
        _, p = welch(res[a]["post_react"], res[b]["post_react"])
        pv[f"{a} vs {b}"] = p
    out = {"config": {"seeds": seeds, "K": K, "probe": PROBE,
                      "min_dormancy": 80, "min_len": 6,
                      "substrate": "4H/L2b/rich10 (confirmed gate cell)",
                      "block_counts": lib.counts()},
           "post_react": summarize({a: res[a]["post_react"] for a in ARMS}),
           "overall": summarize({a: res[a]["overall"] for a in ARMS}),
           "welch_p": pv, "holm_p": holm(pv),
           "raw": res}
    f = RESULTS / "e1r_4h_crypto.json"
    with open(f, "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"[saved] {f.resolve()}")
    for a in ARMS:
        m = out["post_react"][a]
        print(f"{a:22s} post_react {m['mean']:.5f} ± {m['ci95']:.5f}")
    for kk, v in pv.items():
        print(f"welch {kk}: p={v:.4g}  holm={out['holm_p'][kk]:.4g}")


if __name__ == "__main__":
    main()
