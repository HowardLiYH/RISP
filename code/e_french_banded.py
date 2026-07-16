"""PREREG H: banded-monolith (turnover-discipline control) on French-49.

Pre-registered in ../PREREG_FRENCH49.md (PRE-REGISTRATION H) BEFORE this
script was first run. Arm A1b = A1-monolith-erm with a no-trade band on the
SERVED book only (update only if >= b+1 names would change); training
identical to A1 (risp.BandedMonolithArm, additive).

Battery: French-49 L3@15% walk-forward AND L1 walk-forward -- the two cells
where the net claims live -- arms {A1, A1b1, A1b2, A9, A6}, 20 seeds,
gross and net-25bps (run_arm cost_bps=25; both-pay is the lodged convention,
arm-only recorded as sensitivity). Conventions mirror e_french_L3.py /
e_french.py exactly, including the per-cell seeding those scripts (and the
D3 cost battery) use: L3 walk-forward 1311*s+17, L1 walk-forward 911*s+13.
Mirroring the D3 seeding makes the A1/A9/A6 (L3) and A1/A6 (L1) rows exact
reproductions of e_french49_L3_costs.json -- a built-in regression proof.

Output: ../results/e_french49_banded.json
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
from realdata import RealMarket, label_L1
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      dormancy_diag, K_SEL, W_MAX, RESULTS)
from e_french_L3 import label_L3

ARMS = ["A1-monolith-erm", "A1b1-banded", "A1b2-banded",
        "A9-oracle-pinned", "A6-risp-inv"]
PAIRS = [("A1b1-banded", "A1-monolith-erm"),
         ("A1b2-banded", "A1-monolith-erm"),
         ("A6-risp-inv", "A1b1-banded"),
         ("A6-risp-inv", "A1b2-banded"),
         ("A6-risp-inv", "A1-monolith-erm"),
         ("A1b1-banded", "A9-oracle-pinned"),
         ("A1b2-banded", "A9-oracle-pinned")]
NET_KEYS = ("overall_net", "post_react_net", "steady_net",
            "overall_net_armonly", "post_react_net_armonly",
            "steady_net_armonly")


def paired(res_a, res_b):
    d = np.array(res_a) - np.array(res_b)
    return {"mean": float(d.mean()),
            "ci95": float(1.96 * d.std(ddof=1) / np.sqrt(len(d))),
            "positive_significant": bool(
                d.mean() - 1.96 * d.std(ddof=1) / np.sqrt(len(d)) > 0)}


def run_cell(name, X, Y, lab, seeds, seed_fn, cfg):
    factories = {**ARM_FACTORIES, **EXTRA_ARM_FACTORIES}
    mkt = RealMarket(X, Y, lab, np.arange(len(X)))
    sched = mkt.schedule()
    diag = dormancy_diag(sched)
    print(f"[{name}] dormancy diag: {diag}", flush=True)
    res = {a: {"overall": [], "post_react": [],
               "mean_turnover_arm": [], "mean_turnover_oracle": [],
               "rebalance_frac": [],
               **{k: [] for k in NET_KEYS}} for a in ARMS}
    t0 = time.time()
    for s in range(seeds):
        for a in ARMS:
            arm = factories[a](cfg, np.random.default_rng(seed_fn(s)),
                               2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=90,
                        cost_bps=25.0)
            res[a]["overall"].append(m["overall"])
            res[a]["post_react"].append(m["post_react"])
            res[a]["mean_turnover_arm"].append(m["cost"]["mean_turnover_arm"])
            res[a]["mean_turnover_oracle"].append(
                m["cost"]["mean_turnover_oracle"])
            res[a]["rebalance_frac"].append(
                float(getattr(arm, "n_rebalances", np.nan))
                / max(1, getattr(arm, "n_days", 1))
                if hasattr(arm, "n_rebalances") else float("nan"))
            for k in NET_KEYS:
                res[a][k].append(m["cost"][k])
        print(f"  [{name}] seed {s} done ({time.time()-t0:.0f}s)", flush=True)

    out = {"diag": diag,
           "gross_post_react": summarize({a: res[a]["post_react"]
                                          for a in ARMS}),
           "gross_overall": summarize({a: res[a]["overall"] for a in ARMS}),
           "net25_post_react": summarize({a: res[a]["post_react_net"]
                                          for a in ARMS}),
           "net25_overall": summarize({a: res[a]["overall_net"]
                                       for a in ARMS}),
           "net25_post_react_armonly": summarize(
               {a: res[a]["post_react_net_armonly"] for a in ARMS}),
           "mean_turnover_arm": {a: float(np.mean(
               res[a]["mean_turnover_arm"])) for a in ARMS},
           "mean_turnover_oracle": float(np.mean(
               res[ARMS[0]]["mean_turnover_oracle"])),
           "turnover_drop_vs_A1_pct": {
               a: float(100.0 * (1.0
                                 - np.mean(res[a]["mean_turnover_arm"])
                                 / np.mean(res["A1-monolith-erm"]
                                           ["mean_turnover_arm"])))
               for a in ARMS},
           "rebalance_frac": {a: float(np.nanmean(res[a]["rebalance_frac"]))
                              for a in ("A1b1-banded", "A1b2-banded")}}
    for metric, key in (("gross", "post_react"),
                        ("net25_bothpay", "post_react_net"),
                        ("net25_armonly", "post_react_net_armonly")):
        pv = {}
        for a, b in PAIRS:
            _, p = welch(res[a][key], res[b][key])
            pv[f"{a} vs {b}"] = p
        out[f"welch_p_{metric}"] = pv
        out[f"holm_p_{metric}"] = holm(pv)
    # paired per-seed contrasts used by the PH scoring
    out["paired"] = {
        "gamma_gross_A1_minus_A9": paired(res["A1-monolith-erm"]["post_react"],
                                          res["A9-oracle-pinned"]["post_react"]),
        "gamma_net_A1_minus_A9": paired(res["A1-monolith-erm"]["post_react_net"],
                                        res["A9-oracle-pinned"]["post_react_net"]),
        "gamma_net_A1b1_minus_A9": paired(res["A1b1-banded"]["post_react_net"],
                                          res["A9-oracle-pinned"]["post_react_net"]),
        "gamma_net_A1b2_minus_A9": paired(res["A1b2-banded"]["post_react_net"],
                                          res["A9-oracle-pinned"]["post_react_net"]),
        "net_A1_minus_A6": paired(res["A1-monolith-erm"]["post_react_net"],
                                  res["A6-risp-inv"]["post_react_net"]),
        "net_A1b1_minus_A6": paired(res["A1b1-banded"]["post_react_net"],
                                    res["A6-risp-inv"]["post_react_net"]),
        "net_A1b2_minus_A6": paired(res["A1b2-banded"]["post_react_net"],
                                    res["A6-risp-inv"]["post_react_net"]),
        "net_overall_A1_minus_A6": paired(res["A1-monolith-erm"]["overall_net"],
                                          res["A6-risp-inv"]["overall_net"]),
        "net_overall_A1b1_minus_A6": paired(res["A1b1-banded"]["overall_net"],
                                            res["A6-risp-inv"]["overall_net"]),
        "net_overall_A1b2_minus_A6": paired(res["A1b2-banded"]["overall_net"],
                                            res["A6-risp-inv"]["overall_net"]),
    }
    out["raw"] = res
    return out


def main(seeds=20):
    ret, dropped = load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    lab3 = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
    lab1 = np.nan_to_num(label_L1(px)[idx], nan=0).astype(int)

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    out = {"config": {
        "seeds": seeds, "arms": ARMS, "K": 2, "memory": "hard",
        "probe": PROBE, "min_dormancy": 90, "cost_bps": 25.0,
        "seeding": {"L3_walkforward": "1311*s+17 (mirrors e_french_L3.py "
                                      "and D3 cost battery part A)",
                    "L1_walkforward": "911*s+13 (mirrors e_french.py "
                                      "walkforward and D3 part B)"},
        "convention": "both arm and oracle pay their own turnover (net "
                      "regret = net oracle - net arm); turnover = "
                      "0.5*sum|dz|*2 sides; arm-only-pays recorded as "
                      "sensitivity (PREREG addendum E). Band: served book "
                      "updates only if >= b+1 names would change; training "
                      "identical to A1 (PREREG H)."}}
    print("[H/L3] L3@15% walk-forward", flush=True)
    out["L3_walkforward"] = run_cell("L3", X, Y, lab3, seeds,
                                     lambda s: 1311 * s + 17, cfg)
    print("[H/L1] L1 walk-forward", flush=True)
    out["L1_walkforward"] = run_cell("L1", X, Y, lab1, seeds,
                                     lambda s: 911 * s + 13, cfg)
    with open(RESULTS / "e_french49_banded.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("PREREG-H BANDED BATTERY COMPLETE", flush=True)


if __name__ == "__main__":
    main()
