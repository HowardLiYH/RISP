"""
Addendum O (lodged 2026-07-21, commit 851d060, BEFORE this script existed):
pooled cross-history event-level register, checkpoint (a).

Pool (independent histories once): US-modern L3@15% (n=27, from
e_french49_L3_loro.json), US-prewar 10% (n=56, from
e_prewar_event_level.json), Japan 15% (γ_i computed here via the declared
N1-style A1/A9 re-read with sanity vs e_japan_L3_dissoc.json raws).
NBER, 1958-89, North America, Developed ex US: excluded per the lodged rule.

Registered: pooled one-sided sign test + Wilcoxon (frequency-secondary);
dollar register sum γ_i·N_p,i with event bootstrap CI (economically
primary; 10,000 resamples, seed 20260721).

Outputs: ../results/e_japan_event_level.json,
         ../results/e_pooled_event_level.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, run_arm
from run_experiments import PROBE
from realdata import RealMarket
from e_french import build_xy_returns, price_panel, K_SEL, W_MAX, RESULTS
from e_french_L3 import label_L3
from e_japan import load_japan_vw, WINDOW_JP

SEEDS, MIN_DORM = 20, 90
ARMS2 = ["A1-monolith-erm", "A9-oracle-pinned"]
BOOT_N, BOOT_SEED = 10000, 20260721


def japan_events():
    ret, dropped = load_japan_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    dates = ret.index[idx]
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    mkt = RealMarket(X, Y, lab, np.arange(len(X)))
    sched = mkt.schedule()
    T = sched.T
    half = int(T * 0.5)
    windows = []
    for t0 in sched.reactivation_days(MIN_DORM):
        lo, hi = max(int(t0), half), min(int(t0) + PROBE, T)
        if hi > lo:
            windows.append((int(t0), lo, hi))
    n_react = len(windows)
    print(f"[japan] T={T} qualifying reactivations={n_react}", flush=True)
    detail = {a: np.zeros((SEEDS, n_react)) for a in ARMS2}
    agg = {a: [] for a in ARMS2}
    t0c = time.time()
    for s in range(SEEDS):
        for a in ARMS2:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(1311 * s + 17),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM, collect_react=True)
            agg[a].append(m["post_react"])
            det = {d["t_start"]: d["mean_probe_regret"]
                   for d in m["react_detail"]}
            assert set(det) == {w[0] for w in windows}
            for i, (tt, lo, hi) in enumerate(windows):
                detail[a][s, i] = det[tt]
    print(f"[japan] reruns done ({time.time()-t0c:.0f}s)", flush=True)

    ref = json.load(open(RESULTS / "e_japan_L3_dissoc.json"))
    ref = ref["walkforward"]["raw"]
    sanity = {}
    for a in ARMS2:
        got, exp = np.array(agg[a]), np.array(ref[a]["post_react"])
        sanity[a] = {"max_abs_diff": float(np.abs(got - exp).max()),
                     "match": bool(np.allclose(got, exp, rtol=0,
                                               atol=1e-12))}
        print(f"[japan] sanity {a}: {sanity[a]}", flush=True)
    assert all(v["match"] for v in sanity.values()), \
        "japan re-read does not reproduce e_japan_L3_dissoc.json"

    g = detail["A1-monolith-erm"] - detail["A9-oracle-pinned"]
    gamma_i = g.mean(axis=0)
    events = []
    for i, (tt, lo, hi) in enumerate(windows):
        events.append({"i": i, "date": str(dates[tt].date()),
                       "regime": int(sched.regimes[tt]),
                       "dormancy": int(sched.dormancy[tt]),
                       "n_probe_days_counted": int(hi - lo),
                       "gamma_i_mean": float(gamma_i[i]),
                       "gamma_i_ci95": float(1.96 * g[:, i].std(ddof=1)
                                             / np.sqrt(SEEDS))})
    out = {"prereg": "Addendum O, spec commit 851d060",
           "cell": "Japan L3@15% walk-forward (primary)",
           "window": WINDOW_JP, "seeding": "1311*s+17",
           "sanity_vs_published": sanity,
           "n_events": n_react,
           "per_reactivation_gamma": events}
    with open(RESULTS / "e_japan_event_level.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("[saved] results/e_japan_event_level.json", flush=True)
    return events


def main():
    japan = japan_events()

    us_modern = json.load(open(RESULTS / "e_french49_L3_loro.json"))
    us_modern = us_modern["contrasts"]["A1_minus_A9"]["per_reactivation_gamma"]
    prewar = json.load(open(RESULTS / "e_prewar_event_level.json"))
    prewar = prewar["cells"]["prewar_10pct"]["per_reactivation_gamma"]

    pool = []
    for hist, evs in (("US_modern_L3_15pct", us_modern),
                      ("US_prewar_10pct", prewar),
                      ("Japan_15pct", japan)):
        for e in evs:
            pool.append({"history": hist, "date": e.get("date"),
                         "gamma_i": float(e["gamma_i_mean"]),
                         "n_days": int(e["n_probe_days_counted"]),
                         "dollar_i": float(e["gamma_i_mean"]
                                           * e["n_probe_days_counted"])})
    g = np.array([e["gamma_i"] for e in pool])
    d = np.array([e["dollar_i"] for e in pool])
    n = len(pool)
    nz = g[g != 0.0]
    n_pos = int((nz > 0).sum())
    sign_p = float(stats.binomtest(n_pos, len(nz), 0.5,
                                   alternative="greater").pvalue)
    w_stat, w_p = stats.wilcoxon(g, alternative="greater")
    t_stat, t_two = stats.ttest_1samp(g, 0.0)
    t_one = float(t_two / 2 if t_stat > 0 else 1 - t_two / 2)

    rng = np.random.default_rng(BOOT_SEED)
    sums = np.array([d[rng.integers(0, n, n)].sum()
                     for _ in range(BOOT_N)])
    lo, hi = np.percentile(sums, [2.5, 97.5])
    dollar = {"sum_bps_days": float(d.sum() * 1e4),
              "bootstrap_ci95_bps_days": [float(lo * 1e4), float(hi * 1e4)],
              "ci_excludes_0": bool(lo > 0 or hi < 0),
              "per_history_sum_bps_days": {
                  h: float(sum(e["dollar_i"] for e in pool
                               if e["history"] == h) * 1e4)
                  for h in ("US_modern_L3_15pct", "US_prewar_10pct",
                            "Japan_15pct")},
              "n_resamples": BOOT_N, "bootstrap_seed": BOOT_SEED}

    out = {"prereg": "Addendum O, spec commit 851d060",
           "checkpoint": "(a) US_modern + US_prewar_10 + Japan",
           "pool_composition": {h: int(sum(1 for e in pool
                                           if e["history"] == h))
                                for h in ("US_modern_L3_15pct",
                                          "US_prewar_10pct",
                                          "Japan_15pct")},
           "excluded_by_rule": ["NBER (same US-modern history)",
                                "1958-89 (subset of prewar)",
                                "North America (overlaps US)",
                                "Developed ex US (composite)"],
           "n_events": n, "n_zero_dropped": int((g == 0.0).sum()),
           "n_positive": n_pos, "n_negative": int((nz < 0).sum()),
           "median_bps": float(np.median(g) * 1e4),
           "mean_bps": float(g.mean() * 1e4),
           "sign_test_p_one_sided": sign_p,
           "wilcoxon_stat": float(w_stat),
           "wilcoxon_p_one_sided": float(w_p),
           "t_stat_descriptive": float(t_stat),
           "t_p_one_sided_descriptive": t_one,
           "sign_test_pass_at_0.05": bool(sign_p < 0.05),
           "wilcoxon_pass_at_0.05": bool(w_p < 0.05),
           "dollar_register_economically_primary": dollar,
           "events": pool}
    with open(RESULTS / "e_pooled_event_level.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"[pooled] n={n} pos={n_pos} sign_p={sign_p:.4f} "
          f"wilcoxon_p={w_p:.4f} dollar={dollar['sum_bps_days']:+.0f} "
          f"bps·days CI=[{dollar['bootstrap_ci95_bps_days'][0]:+.0f},"
          f"{dollar['bootstrap_ci95_bps_days'][1]:+.0f}] "
          f"excl0={dollar['ci_excludes_0']}", flush=True)
    print("[saved] results/e_pooled_event_level.json", flush=True)


if __name__ == "__main__":
    main()
