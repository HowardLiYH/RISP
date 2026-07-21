"""
E-X2: the granularity-window map (lodged in PRE-REGISTRATION E, 2026-07-15,
commit 5c96c35, BEFORE any run; still unrun until today).

Lodged terms, verbatim: "thresholds 8-22% x1pp x hysteresis exit bands
{0,2,4,6pp}; tier 1 = A1/A9 Gamma at 10 seeds, tier 2 = +A5/A6 at 20 seeds
where tier-1 CI excludes 0. Window criterion fixed now: Gamma CI>0 in >=3
contiguous thresholds at some hysteresis level = window (granularity
reading vindicated); only 15+-0 positive = island (artifact reading wins,
E1f demotes to one-specification-one-history); between = ambiguous,
reported without adjudication."

Operational details declared here (the register left them open):
- Substrate: the French-49 domestic panel, primary window 1990-2025 (the
  window whose 15% cell the map is ABOUT).
- Hysteresis labeler: causal two-threshold state machine on the same t-1
  drawdown series as label_L3 — enter crisis when dd > theta, exit when
  dd <= theta - h. At h=0 this reproduces label_L3 exactly (verified by
  assertion below), so cell (15%, 0) is the registered primary re-read.
- Seeding: the battery convention np.random.default_rng(1311*s+17) per
  arm, s in 0..seeds-1 — identical to the D8 10-seed primary re-read, so
  cell (15%, 0) must reproduce D8's +0.001100+-0.000255 exactly.
- K=2, hard memory, probe 15, min_dormancy 90, k=5, w_max=0.2 throughout.
- "CI excludes 0" (tier-1 -> tier-2 trigger) = paired A1-A9 95% CI
  excludes 0 in EITHER direction; the lodged window criterion consumes
  "Gamma CI>0" (positive side) only.

Output: ../results/e_french49_L3_x2.json
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
from realdata import RealMarket
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      dormancy_diag, K_SEL, W_MAX, RESULTS)
from e_french_L3 import label_L3
from e_french_prewar import PAIRS4

THRESHOLDS = [round(t / 100.0, 2) for t in range(8, 23)]   # 8..22%
HYSTERESIS = [0.00, 0.02, 0.04, 0.06]
TIER1_SEEDS, TIER2_SEEDS = 10, 20
ARMS2 = ["A1-monolith-erm", "A9-oracle-pinned"]
ARMS4 = ["A1-monolith-erm", "A5-risp-erm", "A6-risp-inv", "A9-oracle-pinned"]


def label_L3_hyst(px, theta, h, trend_win=50):
    """Two-threshold drawdown regime x trend sign; causal (t-1 inputs).
    Enter crisis: dd > theta. Exit crisis: dd <= theta - h."""
    lp = np.log(px).mean(axis=1)
    runmax = lp.cummax().shift(1)
    dd = (1.0 - np.exp(lp.shift(1) - runmax)).values
    trend = (lp.shift(1) - lp.shift(trend_win + 1)).fillna(0.0).values
    crisis = np.zeros(len(dd), dtype=int)
    state = 0
    exit_level = theta - h
    for t in range(len(dd)):
        d = dd[t]
        if not np.isfinite(d):
            crisis[t] = state
            continue
        if state == 0 and d > theta:
            state = 1
        elif state == 1 and d <= exit_level:
            state = 0
        crisis[t] = state
    up = (trend > 0).astype(int)
    return crisis * 2 + (1 - up)


def run_cell(X, Y, lab, arms, seeds):
    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    mkt = RealMarket(X, Y, lab, np.arange(len(X)))
    sched = mkt.schedule()
    diag = dormancy_diag(sched)
    res = {a: {"overall": [], "post_react": []} for a in arms}
    n_react = 0
    for s in range(seeds):
        for a in arms:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(1311 * s + 17),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=90)
            res[a]["overall"].append(m["overall"])
            res[a]["post_react"].append(m["post_react"])
            n_react = m["n_react"]
    d_fg = (np.array(res["A1-monolith-erm"]["post_react"])
            - np.array(res["A9-oracle-pinned"]["post_react"]))
    se = d_fg.std(ddof=1) / np.sqrt(len(d_fg))
    gamma = {"mean": float(d_fg.mean()), "ci95": float(1.96 * se),
             "ci_gt_0": bool(d_fg.mean() - 1.96 * se > 0),
             "ci_lt_0": bool(d_fg.mean() + 1.96 * se < 0)}
    return res, diag, n_react, gamma


CKPT_DIR = Path("/private/tmp/claude-501/-Users-yuhaoli-Desktop-Summer-2026"
                "/8373d741-6b75-408c-ae77-32426f72fcfa/scratchpad")


def ckpt_load(name):
    """Per-cell checkpoint cache (pure caching: each cell is independently
    seeded and deterministic, so resume changes no statistic)."""
    p = CKPT_DIR / name
    if p.exists():
        ck = json.load(open(p))
        print(f"[ckpt] resuming: tier1 {len(ck['tier1'])}, "
              f"tier2 {len(ck['tier2'])} cells", flush=True)
        return ck
    return {"tier1": {}, "tier2": {}}


def ckpt_save(name, ck):
    p = CKPT_DIR / name
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w") as fh:
        json.dump(ck, fh, default=float)
    tmp.replace(p)


def main():
    ck = ckpt_load("x2_modern_ckpt.json")
    ret, dropped = load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)

    # h=0 must reproduce label_L3 exactly (same 15% primary labels)
    for th in (0.10, 0.15, 0.20):
        a = np.nan_to_num(label_L3_hyst(px, th, 0.0)[idx], nan=0).astype(int)
        b = np.nan_to_num(label_L3(px, dd_thresh=th)[idx], nan=0).astype(int)
        assert (a == b).all(), f"h=0 labeler mismatch at theta={th}"
    print("[x2] h=0 reproduces label_L3 at 10/15/20% — verified", flush=True)

    tier1 = {}
    t0 = time.time()
    for h in HYSTERESIS:
        for th in THRESHOLDS:
            key = f"th{round(th*100)}_h{round(h*100)}"
            if key in ck["tier1"]:
                tier1[key] = ck["tier1"][key]
                continue
            lab = np.nan_to_num(label_L3_hyst(px, th, h)[idx],
                                nan=0).astype(int)
            occ = float(np.mean(lab >= 2))
            res, diag, n_react, gamma = run_cell(X, Y, lab, ARMS2,
                                                 TIER1_SEEDS)
            tier1[key] = {"theta": th, "hysteresis": h,
                          "crisis_union_occupancy": occ,
                          "n_react": n_react, "diag": diag,
                          "gamma_A1_minus_A9": gamma,
                          "post_react": summarize(
                              {a: res[a]["post_react"] for a in res})}
            ck["tier1"][key] = tier1[key]
            ckpt_save("x2_modern_ckpt.json", ck)
            print(f"[tier1 {key}] occ={occ:.1%} n_react={n_react} "
                  f"G={gamma['mean']:+.5f}+-{gamma['ci95']:.5f} "
                  f"ci>0={gamma['ci_gt_0']} ci<0={gamma['ci_lt_0']} "
                  f"({(time.time()-t0)/60:.1f} min)", flush=True)

    # lodged window criterion, per hysteresis level
    adjudication = {}
    any_window = False
    positives = set()
    for h in HYSTERESIS:
        flags = [bool(tier1[f"th{round(th*100)}_h{round(h*100)}"]
                      ["gamma_A1_minus_A9"]["ci_gt_0"])
                 for th in THRESHOLDS]
        for th, f in zip(THRESHOLDS, flags):
            if f:
                positives.add((round(th * 100), round(h * 100)))
        best, cur = 0, 0
        for f in flags:
            cur = cur + 1 if f else 0
            best = max(best, cur)
        adjudication[f"h{round(h*100)}"] = {
            "positive_thresholds_pct": [round(th * 100) for th, f
                                        in zip(THRESHOLDS, flags) if f],
            "longest_contiguous_run": best,
            "window_here": bool(best >= 3)}
        any_window = any_window or best >= 3
    island = positives == {(15, 0)}
    verdict = ("window" if any_window
               else ("island" if island else "ambiguous"))

    # tier 2: +A5/A6 at 20 seeds wherever tier-1 CI excludes 0
    tier2 = {}
    for key, cell in tier1.items():
        g = cell["gamma_A1_minus_A9"]
        if not (g["ci_gt_0"] or g["ci_lt_0"]):
            continue
        if key in ck["tier2"]:
            tier2[key] = ck["tier2"][key]
            continue
        lab = np.nan_to_num(label_L3_hyst(px, cell["theta"],
                                          cell["hysteresis"])[idx],
                            nan=0).astype(int)
        res, diag, n_react, gamma = run_cell(X, Y, lab, ARMS4, TIER2_SEEDS)
        pv = {}
        for a, b in PAIRS4:
            _, p = welch(res[a]["post_react"], res[b]["post_react"])
            pv[f"{a} vs {b}"] = p
        hp = holm(pv)
        a1 = float(np.mean(res["A1-monolith-erm"]["post_react"]))
        a5 = float(np.mean(res["A5-risp-erm"]["post_react"]))
        a6 = float(np.mean(res["A6-risp-inv"]["post_react"]))
        tier2[key] = {"theta": cell["theta"],
                      "hysteresis": cell["hysteresis"],
                      "seeds": TIER2_SEEDS, "n_react": n_react,
                      "gamma_A1_minus_A9": gamma,
                      "post_react": summarize(
                          {a: res[a]["post_react"] for a in res}),
                      "welch_p": pv, "holm_p": hp,
                      "ordering": {"A1": a1, "A5": a5, "A6": a6,
                                   "A6<A5<A1": bool(a6 < a5 < a1)}}
        ck["tier2"][key] = tier2[key]
        ckpt_save("x2_modern_ckpt.json", ck)
        print(f"[tier2 {key}] G={gamma['mean']:+.5f}+-{gamma['ci95']:.5f} "
              f"A6<A5<A1={tier2[key]['ordering']['A6<A5<A1']} "
              f"minHolm={min(hp.values()):.3g}", flush=True)

    out = {"prereg": ("E-X2, PRE-REGISTRATION E (commit 5c96c35, "
                      "2026-07-15), run 2026-07-20"),
           "config": {"thresholds_pct": [round(t * 100) for t in THRESHOLDS],
                      "hysteresis_pp": [round(h * 100) for h in HYSTERESIS],
                      "tier1_seeds": TIER1_SEEDS, "tier2_seeds": TIER2_SEEDS,
                      "seeding": "1311*s+17", "K": 2, "memory": "hard",
                      "probe": PROBE, "min_dormancy": 90,
                      "k": K_SEL, "w_max": W_MAX,
                      "window": ["1990-01-01", "2025-12-31"]},
           "tier1": tier1,
           "lodged_criterion": ("Gamma CI>0 in >=3 contiguous thresholds "
                                "at some hysteresis level = window; only "
                                "15+-0 positive = island; between = "
                                "ambiguous"),
           "adjudication_per_hysteresis": adjudication,
           "positive_cells_theta_h_pct": sorted(positives),
           "verdict": verdict,
           "tier2": tier2}
    with open(RESULTS / "e_french49_L3_x2.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"[x2] VERDICT: {verdict}; positives={sorted(positives)}",
          flush=True)
    print("[saved] results/e_french49_L3_x2.json", flush=True)


if __name__ == "__main__":
    main()
