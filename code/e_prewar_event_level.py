"""
Addendum N1 (lodged 2026-07-20, commit 7add739, BEFORE this script existed):
event-level inference for the two withheld-era POSITIVE cells.

K1 analysis plan verbatim: one-sided sign test + one-sided Wilcoxon on
per-reactivation gamma_i (H1: median/pseudomedian > 0), alpha=0.05 per
test, t descriptive-only. gamma_i from a LORO-style instrumented re-read
(collect_react=True, arms A1/A9 only), byte-identical seeding to the
published cells, with hard sanity assertions vs the published raws.

Output: ../results/e_prewar_event_level.json
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
from e_french import K_SEL, W_MAX, RESULTS
from e_french_L3 import label_L3
from e_french_prewar import prep

SEEDS, MIN_DORM = 20, 90
ARMS2 = ["A1-monolith-erm", "A9-oracle-pinned"]

CELLS = {
    "prewar_10pct": {
        "window": ("1926-07-01", "1989-12-31"), "dd_thresh": 0.10,
        "seed_mult": 2117, "seed_add": 41,
        "ref_file": "e_french49_prewar_L3_sweep.json",
        "ref_path": ["10pct", "raw"]},
    "subera_1958_1989_15pct": {
        "window": ("1958-01-01", "1989-12-31"), "dd_thresh": 0.15,
        "seed_mult": 1311, "seed_add": 17,
        "ref_file": "e_french49_prewar_L3_subera.json",
        "ref_path": ["1958-1989", "raw"]},
}


def run_cell(name, spec):
    ret, dropped, X, Y, idx, px, dates = prep(spec["window"])
    lab = np.nan_to_num(label_L3(px, dd_thresh=spec["dd_thresh"])[idx],
                        nan=0).astype(int)

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
    print(f"[{name}] T={T} qualifying reactivations={n_react}", flush=True)

    detail = {a: np.zeros((SEEDS, n_react)) for a in ARMS2}
    agg = {a: [] for a in ARMS2}
    tstart = time.time()
    for s in range(SEEDS):
        rng_seed = spec["seed_mult"] * s + spec["seed_add"]
        for a in ARMS2:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(rng_seed),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM, collect_react=True)
            agg[a].append(m["post_react"])
            det = {d["t_start"]: d["mean_probe_regret"]
                   for d in m["react_detail"]}
            assert set(det) == {w[0] for w in windows}
            for i, (tt, lo, hi) in enumerate(windows):
                detail[a][s, i] = det[tt]
    print(f"[{name}] reruns done ({time.time()-tstart:.0f}s)", flush=True)

    ref = json.load(open(RESULTS / spec["ref_file"]))
    for k in spec["ref_path"]:
        ref = ref[k]
    sanity = {}
    for a in ARMS2:
        got, exp = np.array(agg[a]), np.array(ref[a]["post_react"])
        sanity[a] = {"max_abs_diff": float(np.abs(got - exp).max()),
                     "match": bool(np.allclose(got, exp, rtol=0,
                                               atol=1e-12))}
        print(f"[{name}] sanity {a}: max|diff|="
              f"{sanity[a]['max_abs_diff']:.3e} match={sanity[a]['match']}",
              flush=True)
    assert all(v["match"] for v in sanity.values()), \
        f"{name}: re-read does not reproduce the published raws"

    g = detail["A1-monolith-erm"] - detail["A9-oracle-pinned"]
    gamma_i = g.mean(axis=0)                       # per-event, seed-averaged
    per_react = []
    for i, (tt, lo, hi) in enumerate(windows):
        per_react.append({
            "i": i, "date": str(dates[tt].date()),
            "regime": int(sched.regimes[tt]),
            "dormancy": int(sched.dormancy[tt]),
            "n_probe_days_counted": int(hi - lo),
            "gamma_i_mean": float(gamma_i[i]),
            "gamma_i_ci95": float(1.96 * g[:, i].std(ddof=1)
                                  / np.sqrt(SEEDS))})

    vals = gamma_i[gamma_i != 0.0]
    n_zero = int((gamma_i == 0.0).sum())
    n_pos = int((vals > 0).sum())
    sign_p = float(stats.binomtest(n_pos, len(vals), 0.5,
                                   alternative="greater").pvalue)
    w_stat, w_p = stats.wilcoxon(gamma_i, alternative="greater")
    t_stat, t_two = stats.ttest_1samp(gamma_i, 0.0)
    t_one = float(t_two / 2 if t_stat > 0 else 1 - t_two / 2)
    rec = {
        "window": spec["window"], "dd_thresh": spec["dd_thresh"],
        "seeding": f"np.random.default_rng({spec['seed_mult']}*s+"
                   f"{spec['seed_add']}) per arm",
        "sanity_vs_published": sanity,
        "n_events": int(n_react), "n_zero_dropped": n_zero,
        "n_positive": n_pos, "n_negative": int((vals < 0).sum()),
        "mean_bps": float(gamma_i.mean() * 1e4),
        "median_bps": float(np.median(gamma_i) * 1e4),
        "sign_test_p_one_sided": sign_p,
        "wilcoxon_stat": float(w_stat),
        "wilcoxon_p_one_sided": float(w_p),
        "t_stat_descriptive": float(t_stat),
        "t_p_one_sided_descriptive": t_one,
        "sign_test_pass_at_0.05": bool(sign_p < 0.05),
        "wilcoxon_pass_at_0.05": bool(w_p < 0.05),
        "per_reactivation_gamma": per_react}
    print(f"[{name}] n={n_react} pos={n_pos} median={rec['median_bps']:.2f}"
          f"bps sign_p={sign_p:.4f} wilcoxon_p={w_p:.4f} "
          f"(pass {rec['sign_test_pass_at_0.05']}/"
          f"{rec['wilcoxon_pass_at_0.05']})", flush=True)
    return rec


def main():
    out = {"prereg": "Addendum N1, spec commit 7add739",
           "alpha": 0.05,
           "registered_tests": ["sign_test_one_sided", "wilcoxon_one_sided"],
           "t_test_status": "descriptive only (events cluster by era)",
           "cells": {}}
    for name, spec in CELLS.items():
        out["cells"][name] = run_cell(name, spec)
    with open(RESULTS / "e_prewar_event_level.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("[saved] results/e_prewar_event_level.json", flush=True)


if __name__ == "__main__":
    main()
