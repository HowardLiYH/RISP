"""PREREG D5: CVaR / upper-quantile panel of per-reactivation regret.

Pre-registered in ../PREREG_FRENCH49.md (PRE-REGISTRATION D, D5) BEFORE this
script was first run. Question: does the A5-A6 gap concentrate in the UPPER
quantiles of per-reactivation regret (q75/q90/CVaR gaps exceeding the median
gap), per the revised Proposition 3's interpretation?

Part 1 (confirmatory): synthetic E1 arms {A5, A6}, 100 seeds, exactly the
e1() conventions (schedule rng 1000+s, market seed 5000+s, arm rng 99*s+7,
K=2, hard memory, probe=15, min_dormancy=90), run_arm(collect_react=True).
Per seed and arm: median, q75, q90, CVaR@10% (mean of the worst
ceil(0.10*n) events) of the per-reactivation mean probe regrets. Per-seed
paired gap g_stat = stat(A5) - stat(A6); the concentration tests are paired
one-sample t-tests of g_q75-g_med, g_q90-g_med, g_cvar10-g_med (Holm over
the 3), lodged in D5.

Part 2 (DESCRIPTIVE-ONLY, declared in advance in D5): the French-L3
walk-forward panel (~27 qualifying reactivation events, fixed real
schedule), arms {A5, A6}, 20 seeds (1311*s+17, mirroring e_french_L3.py).
Stored, labeled descriptive; no test is scored on it.

Output: ../results/e_cvar_panel.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import (SynthConfig, SyntheticMarket, make_schedule, run_arm,
                  ARM_FACTORIES, welch, holm, ci95)
from run_experiments import summarize, PROBE, MIN_DORM

RESULTS = Path(__file__).resolve().parent / ".." / "results"
ARMS = ["A5-risp-erm", "A6-risp-inv"]
STATS = ("median", "q75", "q90", "cvar10")


def react_stats(events):
    """median/q75/q90/CVaR@10% of one run's per-reactivation regrets."""
    x = np.asarray([ev["mean_probe_regret"] for ev in events], dtype=float)
    if len(x) == 0:
        return {s: float("nan") for s in STATS} | {"n_events": 0,
                                                   "mean": float("nan")}
    ktail = max(1, int(np.ceil(0.10 * len(x))))
    tail = np.sort(x)[-ktail:]
    return {"median": float(np.median(x)),
            "q75": float(np.quantile(x, 0.75)),
            "q90": float(np.quantile(x, 0.90)),
            "cvar10": float(tail.mean()),
            "mean": float(x.mean()),
            "n_events": int(len(x))}


def part1_synth(seeds=100):
    per_seed = {a: {s: [] for s in STATS + ("mean", "n_events")}
                for a in ARMS}
    post = {a: [] for a in ARMS}
    t0 = time.time()
    for s in range(seeds):
        cfg = SynthConfig()
        rng = np.random.default_rng(1000 + s)
        sched = make_schedule(rng)
        for a in ARMS:
            mkt = SyntheticMarket(cfg, seed=5000 + s)
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(99 * s + 7),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM, collect_react=True)
            st = react_stats(m["react_detail"])
            for k in per_seed[a]:
                per_seed[a][k].append(st[k])
            post[a].append(m["post_react"])
        if s % 20 == 0:
            print(f"  [D5/synth] seed {s} ({time.time()-t0:.0f}s), "
                  f"n_events={st['n_events']}", flush=True)

    out = {"per_seed": per_seed,
           "post_react_check": summarize(post),
           "n_events_per_seed": {a: ci95(per_seed[a]["n_events"])
                                 for a in ARMS}}
    # per-seed paired gaps A5 - A6 at each statistic
    gaps = {}
    for stat in STATS + ("mean",):
        g = (np.asarray(per_seed["A5-risp-erm"][stat])
             - np.asarray(per_seed["A6-risp-inv"][stat]))
        gaps[stat] = g
        m, h = ci95(g)
        out.setdefault("gap_A5_minus_A6", {})[stat] = {
            "mean": m, "ci95": h,
            "positive_significant": bool(m - h > 0)}
    # D5 lodged concentration tests: gap at upper stat minus gap at median
    from scipy import stats as sps
    conc, pv = {}, {}
    for stat in ("q75", "q90", "cvar10"):
        d = gaps[stat] - gaps["median"]
        m, h = ci95(d)
        t, p = sps.ttest_1samp(d, 0.0)
        conc[stat] = {"mean_excess_gap": m, "ci95": h, "t": float(t),
                      "p_two_sided": float(p),
                      "ratio_gap_vs_median": float(
                          gaps[stat].mean() / gaps["median"].mean())
                      if gaps["median"].mean() != 0 else float("nan")}
        pv[f"gap({stat}) - gap(median)"] = float(p)
    out["concentration_tests"] = conc
    out["concentration_holm_p"] = holm(pv)
    # arm-level welch at each stat (context)
    out["welch_p_A5_vs_A6_by_stat"] = {
        stat: welch(per_seed["A5-risp-erm"][stat],
                    per_seed["A6-risp-inv"][stat])[1]
        for stat in STATS + ("mean",)}
    return out


def part2_french_descriptive(seeds=20):
    from realdata import RealMarket
    from e_french import (load_french_vw, build_xy_returns, price_panel,
                          K_SEL, W_MAX)
    from e_french_L3 import label_L3
    ret, dropped = load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
    sched = mkt.schedule()
    per_seed = {a: {s: [] for s in STATS + ("mean", "n_events")}
                for a in ARMS}
    events = {a: [] for a in ARMS}       # per seed: list of event dicts
    t0 = time.time()
    for s in range(seeds):
        for a in ARMS:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(1311 * s + 17),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=90,
                        collect_react=True)
            st = react_stats(m["react_detail"])
            for k in per_seed[a]:
                per_seed[a][k].append(st[k])
            events[a].append(m["react_detail"])
        print(f"  [D5/L3] seed {s} ({time.time()-t0:.0f}s)", flush=True)
    # event-level panel: same fixed real schedule for every seed/arm ->
    # average each event's probe regret across seeds, then the A5-A6 gap
    ev_meta = [{"t_start": ev["t_start"], "regime": ev["regime"],
                "dormancy": ev["dormancy"], "n_days": ev["n_days"]}
               for ev in events[ARMS[0]][0]]
    ev_mean = {a: np.mean([[ev["mean_probe_regret"] for ev in run]
                           for run in events[a]], axis=0) for a in ARMS}
    gap_ev = ev_mean["A5-risp-erm"] - ev_mean["A6-risp-inv"]
    x = gap_ev
    ktail = max(1, int(np.ceil(0.10 * len(x))))
    out = {"descriptive_only": True,
           "n_events": len(ev_meta), "events": ev_meta,
           "event_mean_probe_regret": {a: ev_mean[a].tolist() for a in ARMS},
           "event_gap_A5_minus_A6": gap_ev.tolist(),
           "gap_quantiles": {"median": float(np.median(x)),
                             "q75": float(np.quantile(x, 0.75)),
                             "q90": float(np.quantile(x, 0.90)),
                             "cvar10": float(np.sort(x)[-ktail:].mean())},
           "arm_event_quantiles": {a: react_stats(
               [{"mean_probe_regret": v} for v in ev_mean[a]])
               for a in ARMS},
           "per_seed": per_seed}
    # per-seed gap-at-stat means (still descriptive)
    for stat in STATS + ("mean",):
        g = (np.asarray(per_seed["A5-risp-erm"][stat])
             - np.asarray(per_seed["A6-risp-inv"][stat]))
        m, h = ci95(g)
        out.setdefault("gap_A5_minus_A6_per_seed", {})[stat] = {
            "mean": m, "ci95": h}
    return out


def main(seeds_synth=100, seeds_french=20):
    out = {"config": {
        "arms": ARMS, "seeds_synth": seeds_synth,
        "seeds_french": seeds_french, "probe": PROBE,
        "min_dormancy_synth": MIN_DORM, "min_dormancy_french": 90,
        "cvar_def": "CVaR@10% = mean of the worst ceil(0.10*n) "
                    "per-reactivation probe-window regrets",
        "lodged_tests": "paired one-sample t of gap(q75/q90/cvar10) - "
                        "gap(median) over 100 synthetic seeds, Holm-3; "
                        "French-L3 panel descriptive-only (PREREG D5)"}}
    print("[D5] part 1: synthetic 100-seed panel", flush=True)
    out["synthetic"] = part1_synth(seeds_synth)
    print("[D5] part 2: French-L3 descriptive panel", flush=True)
    out["french_L3_descriptive"] = part2_french_descriptive(seeds_french)
    with open(RESULTS / "e_cvar_panel.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("D5 CVAR PANEL COMPLETE", flush=True)


if __name__ == "__main__":
    main()
