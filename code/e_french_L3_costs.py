"""PREREG D3: transaction-cost battery on the French L3 walk-forward.

Pre-registered in ../PREREG_FRENCH49.md (pre-registration D, D3) with the
cost convention lodged at the end of addendum E: both the arm and the
oracle benchmark pay costs (net regret = net-of-cost oracle utility minus
net-of-cost arm utility; turnover = 0.5*sum|z_t - z_{t-1}|*2 sides); the
arm-only-pays variant is reported as sensitivity.

Parts:
  A. L3 walk-forward {A1, A9, A5, A6}, 20 seeds, cost_bps in {25, 50, 100}.
     Costs are pure accounting (never fed back to the arm), so one run at
     25 bps records the turnover series and the other tiers are exact
     linear rescalings -- no re-simulation needed.
  B. L1 walk-forward {A1, A6} at 25 bps (inversion-side check), mirroring
     e_french.py's walkforward block (seeding 911*s+13).
  C. Gate-1 cost slice: the L3 and L1 real-vs-pooled regret series net of
     costs at 25 bps (real/pooled/oracle each pay their own turnover).

Output: ../results/e_french49_L3_costs.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import (ARM_FACTORIES, run_arm, welch, holm, regret, solve_topk)
from run_experiments import summarize, PROBE
from realdata import RealMarket, label_L1
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      dormancy_diag, K_SEL, W_MAX, RESULTS)
from e_french_L3 import label_L3

TIERS = [25.0, 50.0, 100.0]
ARMS_A = ["A1-monolith-erm", "A9-oracle-pinned", "A5-risp-erm",
          "A6-risp-inv"]
PAIRS_A = [("A6-risp-inv", "A5-risp-erm"),
           ("A6-risp-inv", "A1-monolith-erm"),
           ("A5-risp-erm", "A1-monolith-erm"),
           ("A6-risp-inv", "A9-oracle-pinned")]


def tier_metrics(daily, cost, bps):
    """Exact net metrics at any bps from one instrumented run."""
    c = bps / 1e4
    ta, to = cost["turnover_arm"], cost["turnover_oracle"]
    pm, sm, half = cost["eval_probe_mask"], cost["eval_steady_mask"], \
        cost["half"]
    net_both = daily + c * (ta - to)
    net_arm = daily + c * ta
    return {
        "overall_net": float(net_both[half:].mean()),
        "post_react_net": float(net_both[pm].mean()) if pm.any()
        else float("nan"),
        "steady_net": float(net_both[sm].mean()),
        "overall_net_armonly": float(net_arm[half:].mean()),
        "post_react_net_armonly": float(net_arm[pm].mean()) if pm.any()
        else float("nan"),
        "steady_net_armonly": float(net_arm[sm].mean()),
    }


def paired(res_a, res_b):
    d = np.array(res_a) - np.array(res_b)
    return {"mean": float(d.mean()),
            "ci95": float(1.96 * d.std(ddof=1) / np.sqrt(len(d))),
            "positive_significant": bool(
                d.mean() - 1.96 * d.std(ddof=1) / np.sqrt(len(d)) > 0)}


def run_battery(X, Y, lab, arms, seeds, seed_fn, cfg):
    """One walk-forward battery, instrumented at 25 bps; returns per-seed
    gross metrics + per-tier net metrics (exact rescalings)."""
    factories = dict(ARM_FACTORIES)
    mkt = RealMarket(X, Y, lab, np.arange(len(X)))
    sched = mkt.schedule()
    diag = dormancy_diag(sched)
    res = {a: {"overall": [], "post_react": [],
               "mean_turnover_arm": [], "mean_turnover_oracle": [],
               "tiers": {str(b): {k: [] for k in (
                   "overall_net", "post_react_net", "steady_net",
                   "overall_net_armonly", "post_react_net_armonly",
                   "steady_net_armonly")} for b in TIERS}}
           for a in arms}
    t0 = time.time()
    for s in range(seeds):
        for a in arms:
            arm = factories[a](cfg, np.random.default_rng(seed_fn(s)),
                               2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=90,
                        cost_bps=25.0)
            res[a]["overall"].append(m["overall"])
            res[a]["post_react"].append(m["post_react"])
            res[a]["mean_turnover_arm"].append(
                m["cost"]["mean_turnover_arm"])
            res[a]["mean_turnover_oracle"].append(
                m["cost"]["mean_turnover_oracle"])
            for b in TIERS:
                tm = tier_metrics(m["daily"], m["cost"], b)
                for k, v in tm.items():
                    res[a]["tiers"][str(b)][k].append(v)
        print(f"  seed {s} done ({time.time()-t0:.0f}s)", flush=True)
    return res, diag


def regret_series_cost(X, Y, labels, refit=60, lam=10.0):
    """e_french.regret_series + turnover instrumentation (self and oracle)."""
    T, n, d = len(X), X.shape[1], X.shape[2]
    split = T // 2
    regs = np.zeros(T - split)
    turn = np.zeros(T - split)
    turn_o = np.zeros(T - split)
    z_prev = np.zeros(n)
    z_prev_o = np.zeros(n)
    models = {}
    for t in range(split, T):
        if (t - split) % refit == 0:
            models = {}
            for r in set(labels[:t].tolist()):
                m_idx = np.where(labels[:t] == r)[0]
                if len(m_idx) < 30:
                    continue
                Xtr = np.vstack([X[i] for i in m_idx])
                ytr = np.concatenate([Y[i] for i in m_idx])
                A = Xtr.T @ Xtr + lam * np.eye(d)
                models[r] = np.linalg.solve(A, Xtr.T @ ytr)
        w = models.get(labels[t])
        yh = X[t] @ w if w is not None else np.zeros(n)
        regs[t - split] = regret(yh, Y[t], K_SEL, W_MAX)
        z = solve_topk(yh, K_SEL, W_MAX)
        z_o = solve_topk(Y[t], K_SEL, W_MAX)
        turn[t - split] = np.abs(z - z_prev).sum()
        turn_o[t - split] = np.abs(z_o - z_prev_o).sum()
        z_prev, z_prev_o = z, z_o
    return regs, turn, turn_o


def gate_cost_slice(X, Y, labs, bps=25.0):
    """Real-vs-pooled gate arms net of costs (both-pay + arm-only)."""
    c = bps / 1e4
    pooled_regs, pooled_turn, orc_turn = regret_series_cost(
        X, Y, np.zeros(len(X), dtype=int))
    out = {}
    for lname, lab in labs.items():
        real_regs, real_turn, orc_turn2 = regret_series_cost(X, Y, lab)
        assert np.allclose(orc_turn, orc_turn2)
        real_net = real_regs + c * (real_turn - orc_turn)
        pooled_net = pooled_regs + c * (pooled_turn - orc_turn)
        out[lname] = {
            "bps": bps,
            "real_mean_regret_gross": float(real_regs.mean()),
            "pooled_mean_regret_gross": float(pooled_regs.mean()),
            "cond_vs_pooled_pct_gross": float(
                100 * (pooled_regs.mean() - real_regs.mean())
                / (pooled_regs.mean() + 1e-12)),
            "real_mean_regret_net": float(real_net.mean()),
            "pooled_mean_regret_net": float(pooled_net.mean()),
            "cond_vs_pooled_pct_net": float(
                100 * (pooled_net.mean() - real_net.mean())
                / (pooled_net.mean() + 1e-12)),
            "real_mean_regret_net_armonly": float(
                (real_regs + c * real_turn).mean()),
            "pooled_mean_regret_net_armonly": float(
                (pooled_regs + c * pooled_turn).mean()),
            "mean_turnover_real": float(real_turn.mean()),
            "mean_turnover_pooled": float(pooled_turn.mean()),
            "mean_turnover_oracle": float(orc_turn.mean()),
        }
        print(f"[D3/gate/{lname}] cond-vs-pooled gross "
              f"{out[lname]['cond_vs_pooled_pct_gross']:+.3f}% -> net "
              f"{out[lname]['cond_vs_pooled_pct_net']:+.3f}%", flush=True)
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
    out = {"config": {"seeds": seeds, "tiers_bps": TIERS, "K": 2,
                      "memory": "hard", "probe": PROBE, "min_dormancy": 90,
                      "convention": "both arm and oracle pay their own "
                      "turnover (net regret = net oracle - net arm); "
                      "turnover = 0.5*sum|dz|*2 sides; arm-only-pays "
                      "recorded as sensitivity (PREREG addendum E)"}}

    # ---- Part A: L3 tiers ----
    print("[D3/A] L3 walk-forward cost tiers", flush=True)
    resA, diagA = run_battery(X, Y, lab3, ARMS_A, seeds,
                              lambda s: 1311 * s + 17, cfg)
    A = {"diag": diagA,
         "gross_post_react": summarize(
             {a: resA[a]["post_react"] for a in ARMS_A}),
         "gross_overall": summarize({a: resA[a]["overall"]
                                     for a in ARMS_A}),
         "mean_turnover_arm": {a: float(np.mean(
             resA[a]["mean_turnover_arm"])) for a in ARMS_A},
         "mean_turnover_oracle": float(np.mean(
             resA[ARMS_A[0]]["mean_turnover_oracle"])),
         "tiers": {}}
    for b in TIERS:
        tb = str(b)
        tier = {}
        for variant, key in (("both_pay", "post_react_net"),
                             ("arm_only", "post_react_net_armonly")):
            xs = {a: resA[a]["tiers"][tb][key] for a in ARMS_A}
            pv = {}
            for p1, p2 in PAIRS_A:
                _, p = welch(xs[p1], xs[p2])
                pv[f"{p1} vs {p2}"] = p
            gamma = paired(xs["A1-monolith-erm"], xs["A9-oracle-pinned"])
            means = {a: float(np.mean(xs[a])) for a in ARMS_A}
            order = sorted(means, key=means.get)
            tier[variant] = {
                "post_react_net": summarize(xs),
                "overall_net": summarize(
                    {a: resA[a]["tiers"][tb][
                        "overall_net" if variant == "both_pay"
                        else "overall_net_armonly"] for a in ARMS_A}),
                "gamma_forget_net": gamma,
                "ordering_by_mean": order,
                "welch_p": pv, "holm_p": holm(pv)}
        A["tiers"][tb] = tier
        g = tier["both_pay"]["gamma_forget_net"]
        print(f"[D3/A] {b:.0f}bps Γ_net={g['mean']:+.5f}±{g['ci95']:.5f} "
              f"sig={g['positive_significant']} "
              f"order={tier['both_pay']['ordering_by_mean']}", flush=True)
    A["raw"] = resA
    out["L3_tiers"] = A

    # ---- Part B: L1 inversion-side check at 25 bps ----
    print("[D3/B] L1 walk-forward {A1, A6} @25bps", flush=True)
    resB, diagB = run_battery(X, Y, lab1, ["A1-monolith-erm", "A6-risp-inv"],
                              seeds, lambda s: 911 * s + 13, cfg)
    B = {"diag": diagB,
         "gross_post_react": summarize({a: resB[a]["post_react"]
                                        for a in resB}),
         "tiers": {}}
    for b in [25.0]:
        tb = str(b)
        for variant, key in (("both_pay", "post_react_net"),
                             ("arm_only", "post_react_net_armonly")):
            xs = {a: resB[a]["tiers"][tb][key] for a in resB}
            _, p = welch(xs["A6-risp-inv"], xs["A1-monolith-erm"])
            B["tiers"].setdefault(tb, {})[variant] = {
                "post_react_net": summarize(xs),
                "A6_minus_A1_paired": paired(xs["A6-risp-inv"],
                                             xs["A1-monolith-erm"]),
                "welch_p_A6_vs_A1": float(p)}
    B["raw"] = resB
    out["L1_25bps"] = B

    # ---- Part C: gate-1 cost slice ----
    print("[D3/C] gate real-vs-pooled net of 25bps", flush=True)
    out["gate_cost_slice_25bps"] = gate_cost_slice(
        X, Y, {"L3": lab3, "L1": lab1}, bps=25.0)

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items()
                    if k not in ("turnover_arm", "turnover_oracle",
                                 "eval_probe_mask", "eval_steady_mask")}
        return o

    with open(RESULTS / "e_french49_L3_costs.json", "w") as fh:
        json.dump(strip(out), fh, indent=1, default=float)
    print("D3 COST BATTERY COMPLETE", flush=True)


if __name__ == "__main__":
    main()
