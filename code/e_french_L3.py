"""
French 49-industry battery, L3 drawdown labeler (slow dormancy).

Pre-registered as PRE-REGISTRATION B in ../PREREG_FRENCH49.md BEFORE this
script was first run. Everything mirrors e_french.py except the labeler.

Outputs: ../results/e_french49_L3_gate.json, ../results/e_french49_L3_dissoc.json
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
from realdata import BlockLibrary, StitchedMarket, RealMarket
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      gate50, dormancy_diag, ARMS, PAIRS, K_SEL, W_MAX,
                      RESULTS)


def label_L3(px, dd_thresh=0.15, trend_win=50):
    """Drawdown-regime x trend. Causal: all inputs through t-1."""
    import pandas as pd
    lp = np.log(px).mean(axis=1)
    runmax = lp.cummax().shift(1)
    dd = 1.0 - np.exp(lp.shift(1) - runmax)
    crisis = (dd > dd_thresh).astype(int)
    trend = (lp.shift(1) - lp.shift(trend_win + 1)).fillna(0.0)
    up = (trend > 0).astype(int)
    return (crisis * 2 + (1 - up)).values


def main(seeds=20):
    ret, dropped = load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
    print("L3 regime counts:", {int(r): int((lab == r).sum())
                                for r in sorted(set(lab.tolist()))},
          flush=True)

    g = gate50(X, Y, lab)
    print(f"L3 gate: gap={g['gap_pct']:+.2f}% z={g['z_vs_shuffled']:+.2f} "
          f"p={g['p_one_sided']:.4g} PASS={g['PASS']}", flush=True)
    with open(RESULTS / "e_french49_L3_gate.json", "w") as fh:
        json.dump(g, fh, indent=1, default=float)

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    out = {}
    for design in ("walkforward", "stitched"):
        res = {a: {"overall": [], "post_react": []} for a in ARMS}
        t0 = time.time()
        if design == "walkforward":
            mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
            sched = mkt.schedule()
            diag = dormancy_diag(sched)
            print(f"[L3/wf] dormancy diag: {diag}", flush=True)
            for s in range(seeds):
                for a in ARMS:
                    arm = ARM_FACTORIES[a](cfg, np.random.default_rng(
                        1311 * s + 17), 2, "hard")
                    m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                                min_dormancy=90)
                    res[a]["overall"].append(m["overall"])
                    res[a]["post_react"].append(m["post_react"])
                if s == 0:
                    print(f"  seed0 {time.time()-t0:.0f}s "
                          f"n_react={m['n_react']}", flush=True)
        else:
            lib = BlockLibrary(X, Y, lab.astype(float), np.arange(len(idx)),
                               min_len=8)
            counts = lib.counts()
            crisis_pool = {r: c for r, c in counts.items() if r >= 2}
            rare = max(crisis_pool, key=crisis_pool.get) if any(
                crisis_pool.values()) else min(counts, key=counts.get)
            others = [r for r in range(4) if r != rare and counts[r] > 0]
            diag = {"block_counts": counts, "rare": rare}
            print(f"[L3/st] blocks={counts} rare(crisis)={rare}", flush=True)
            for s in range(seeds):
                rng = np.random.default_rng(5000 + s)
                seq = []
                for cyc in range(16):
                    for r in rng.permutation(others):
                        seq.append((int(r), int(rng.integers(25, 50))))
                    if cyc % 3 == 2:
                        seq.append((int(rare), int(rng.integers(15, 30))))
                mkt = StitchedMarket(lib, rng)
                sched = mkt.materialize(seq)
                for a in ARMS:
                    arm = ARM_FACTORIES[a](cfg, np.random.default_rng(
                        1733 * s + 29), 2, "hard")
                    m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                                min_dormancy=90)
                    res[a]["overall"].append(m["overall"])
                    res[a]["post_react"].append(m["post_react"])
        pv = {}
        for a, b in PAIRS:
            _, p = welch(res[a]["post_react"], res[b]["post_react"])
            pv[f"{a} vs {b}"] = p
        d_fg = (np.array(res["A1-monolith-erm"]["post_react"])
                - np.array(res["A9-oracle-pinned"]["post_react"]))
        gamma = {"mean": float(d_fg.mean()),
                 "ci95": float(1.96 * d_fg.std(ddof=1) / np.sqrt(len(d_fg))),
                 "positive_significant": bool(
                     d_fg.mean() - 1.96 * d_fg.std(ddof=1)
                     / np.sqrt(len(d_fg)) > 0)}
        out[design] = {"diag": diag,
                       "post_react": summarize({a: res[a]["post_react"]
                                                for a in ARMS}),
                       "overall": summarize({a: res[a]["overall"]
                                             for a in ARMS}),
                       "welch_p": pv, "holm_p": holm(pv),
                       "gate2_forgetting_deficit": gamma, "raw": res}
        print(f"[L3/{design}] Γ={gamma['mean']:.5f}±{gamma['ci95']:.5f} "
              f"sig={gamma['positive_significant']} "
              f"min raw p={min(pv.values()):.4f} "
              f"({(time.time()-t0)/60:.1f} min)", flush=True)
    with open(RESULTS / "e_french49_L3_dissoc.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("L3 BATTERY COMPLETE", flush=True)


if __name__ == "__main__":
    main()
