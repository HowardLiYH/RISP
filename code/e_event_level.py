"""PREREG K K1: event-level inference on the LORO per-reactivation gammas.

Pre-registered in ../PREREG_FRENCH49.md (Addendum K, 2026-07-20, commit
a02b9f8 pushed) BEFORE this script was written. Honest scope: the
gamma_i_mean values consumed here were already released in the two LORO
JSONs; K1 registers the ANALYSIS PLAN (tests, sidedness, alpha,
consequences), not data custody.

Registered tests per cell, alpha 0.05, no cross-cell correction:
  - one-sided sign test (H1: median per-event Gamma > 0), zeros dropped
  - one-sided Wilcoxon signed-rank (H1: pseudomedian > 0)
  - one-sample t reported as DESCRIPTIVE only (events cluster by era)

Output: ../results/e_event_level_inference.json
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, wilcoxon, ttest_1samp

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

CELLS = {
    "L3_walkforward": "e_french49_L3_loro.json",
    "NBER_walkforward": "e_french49_nber_loro.json",
}


def analyze(fname: str) -> dict:
    with open(RESULTS / fname) as fh:
        d = json.load(fh)
    per = d["contrasts"]["A1_minus_A9"]["per_reactivation_gamma"]
    g = np.array([e["gamma_i_mean"] for e in per], dtype=float)
    n = len(g)
    n_zero = int((g == 0).sum())
    nz = g[g != 0]                       # sign-test convention: drop zeros
    n_pos = int((nz > 0).sum())
    sign = binomtest(n_pos, len(nz), 0.5, alternative="greater")
    w = wilcoxon(g, alternative="greater")
    t = ttest_1samp(g, 0.0, alternative="greater")
    return {
        "source": fname,
        "n_events": n,
        "n_zero_dropped": n_zero,
        "n_positive": n_pos,
        "n_negative": int((nz < 0).sum()),
        "mean_bps": float(g.mean() * 1e4),
        "median_bps": float(np.median(g) * 1e4),
        "sign_test_p_one_sided": float(sign.pvalue),
        "wilcoxon_stat": float(w.statistic),
        "wilcoxon_p_one_sided": float(w.pvalue),
        "t_stat_descriptive": float(t.statistic),
        "t_p_one_sided_descriptive": float(t.pvalue),
        "sign_test_pass_at_0.05": bool(sign.pvalue < 0.05),
        "wilcoxon_pass_at_0.05": bool(w.pvalue < 0.05),
    }


def main():
    out = {"prereg": "Addendum K K1, spec commit a02b9f8",
           "alpha": 0.05,
           "registered_tests": ["sign_test_one_sided",
                                "wilcoxon_one_sided"],
           "t_test_status": "descriptive only (events cluster by era)",
           "cells": {}}
    for cell, fname in CELLS.items():
        r = analyze(fname)
        out["cells"][cell] = r
        print(f"[K1] {cell}: n={r['n_events']} n_pos={r['n_positive']} "
              f"median={r['median_bps']:+.2f}bps "
              f"sign p={r['sign_test_p_one_sided']:.4g} "
              f"wilcoxon p={r['wilcoxon_p_one_sided']:.4g} "
              f"t={r['t_stat_descriptive']:+.2f} "
              f"(p={r['t_p_one_sided_descriptive']:.4g} descr.)",
              flush=True)
    with open(RESULTS / "e_event_level_inference.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("K1 EVENT-LEVEL INFERENCE COMPLETE", flush=True)


if __name__ == "__main__":
    main()
