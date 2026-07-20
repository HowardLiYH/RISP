"""
Addendum N2 (lodged 2026-07-20, commit 7add739, BEFORE this script existed):
net-of-cost register for the two withheld-era POSITIVE cells.

D3 convention verbatim: both-pay adjudicating register, turnover =
0.5*sum|dz|*2 sides, arm-only-pays sensitivity; one instrumented run at
25 bps, exact rescalings to {50,100}; 25 bps adjudicates. Arms
{A1,A9,A5,A6}, 20 seeds, each cell's published seeding; gross post_react
must reproduce the published raws exactly (costs are pure accounting).

Output: ../results/e_prewar_costs.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, run_arm, welch
from run_experiments import PROBE
from realdata import RealMarket
from e_french import K_SEL, W_MAX, RESULTS
from e_french_L3 import label_L3
from e_french_prewar import prep
from e_french_L3_costs import tier_metrics, paired, TIERS
from e_prewar_event_level import CELLS

SEEDS, MIN_DORM = 20, 90
ARMS4 = ["A1-monolith-erm", "A9-oracle-pinned", "A5-risp-erm",
         "A6-risp-inv"]
NET_KEYS = ("overall_net", "post_react_net", "steady_net",
            "overall_net_armonly", "post_react_net_armonly",
            "steady_net_armonly")


def run_cell(name, spec):
    ret, dropped, X, Y, idx, px, dates = prep(spec["window"])
    lab = np.nan_to_num(label_L3(px, dd_thresh=spec["dd_thresh"])[idx],
                        nan=0).astype(int)

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    mkt = RealMarket(X, Y, lab, np.arange(len(X)))
    sched = mkt.schedule()
    res = {a: {"post_react": [], "mean_turnover_arm": [],
               "tiers": {str(b): {k: [] for k in NET_KEYS} for b in TIERS}}
           for a in ARMS4}
    t0 = time.time()
    for s in range(SEEDS):
        rng_seed = spec["seed_mult"] * s + spec["seed_add"]
        for a in ARMS4:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(rng_seed),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM, cost_bps=25.0)
            res[a]["post_react"].append(m["post_react"])
            res[a]["mean_turnover_arm"].append(
                m["cost"]["mean_turnover_arm"])
            for b in TIERS:
                tm = tier_metrics(m["daily"], m["cost"], b)
                for k in NET_KEYS:
                    res[a]["tiers"][str(b)][k].append(tm[k])
    print(f"[{name}] runs done ({time.time()-t0:.0f}s)", flush=True)

    ref = json.load(open(RESULTS / spec["ref_file"]))
    for k in spec["ref_path"]:
        ref = ref[k]
    sanity = {}
    for a in ARMS4:
        got = np.array(res[a]["post_react"])
        exp = np.array(ref[a]["post_react"])
        sanity[a] = {"max_abs_diff": float(np.abs(got - exp).max()),
                     "match": bool(np.allclose(got, exp, rtol=0,
                                               atol=1e-12))}
    assert all(v["match"] for v in sanity.values()), \
        f"{name}: instrumented run does not reproduce the published raws"
    print(f"[{name}] gross sanity vs published: all match", flush=True)

    gross_gamma = paired(res["A1-monolith-erm"]["post_react"],
                         res["A9-oracle-pinned"]["post_react"])
    tiers_out = {}
    for b in TIERS:
        tb = str(b)
        g_net = paired(res["A1-monolith-erm"]["tiers"][tb]["post_react_net"],
                       res["A9-oracle-pinned"]["tiers"][tb]
                       ["post_react_net"])
        g_net_ao = paired(
            res["A1-monolith-erm"]["tiers"][tb]["post_react_net_armonly"],
            res["A9-oracle-pinned"]["tiers"][tb]["post_react_net_armonly"])
        a1a6_net = paired(
            res["A1-monolith-erm"]["tiers"][tb]["post_react_net"],
            res["A6-risp-inv"]["tiers"][tb]["post_react_net"])
        _, p_a6a1 = welch(res["A6-risp-inv"]["tiers"][tb]["post_react_net"],
                          res["A1-monolith-erm"]["tiers"][tb]
                          ["post_react_net"])
        tiers_out[tb] = {
            "gamma_net_bothpay": g_net,
            "gamma_net_armonly_sensitivity": g_net_ao,
            "gamma_net_ge_gross": bool(g_net["mean"] >= gross_gamma["mean"]),
            "A1_minus_A6_net_bothpay": a1a6_net,
            "A6_below_A1_net_direction": bool(
                np.mean(res["A6-risp-inv"]["tiers"][tb]["post_react_net"])
                < np.mean(res["A1-monolith-erm"]["tiers"][tb]
                          ["post_react_net"])),
            "welch_p_A6_vs_A1_net": float(p_a6a1),
            "post_react_net_means": {
                a: float(np.mean(res[a]["tiers"][tb]["post_react_net"]))
                for a in ARMS4}}
        print(f"[{name}] {b}bps G_net={g_net['mean']:+.5f}"
              f"+-{g_net['ci95']:.5f} sig={g_net['positive_significant']} "
              f"ge_gross={tiers_out[tb]['gamma_net_ge_gross']} "
              f"A6<A1net={tiers_out[tb]['A6_below_A1_net_direction']} "
              f"p={p_a6a1:.3g}", flush=True)
    return {"window": spec["window"], "dd_thresh": spec["dd_thresh"],
            "seeding": f"np.random.default_rng({spec['seed_mult']}*s+"
                       f"{spec['seed_add']}) per arm",
            "convention": ("both-pay adjudicating at 25 bps; arm-only "
                           "sensitivity; turnover=0.5*sum|dz|*2 sides; "
                           "tiers exact rescalings of one 25bps run"),
            "sanity_vs_published_gross": sanity,
            "gamma_gross": gross_gamma,
            "mean_turnover_arm": {
                a: float(np.mean(res[a]["mean_turnover_arm"]))
                for a in ARMS4},
            "tiers": tiers_out}


def main():
    out = {"prereg": "Addendum N2, spec commit 7add739", "cells": {}}
    for name, spec in CELLS.items():
        out["cells"][name] = run_cell(name, spec)
    with open(RESULTS / "e_prewar_costs.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("[saved] results/e_prewar_costs.json", flush=True)


if __name__ == "__main__":
    main()
