"""
E-F withheld-era battery: French 49 industries, 1926-07-01 .. 1989-12-31.

Pre-registered as E-F in ../PREREG_FRENCH49.md (PRE-REGISTRATION E, written
2026-07-15 BEFORE this script was first run). Byte-identical L3 protocol to
e_french_L3.py except the window: same features, same gate-1 criteria with
50 shuffles, same gate 2, same ten arms / 6-pair Welch+Holm family, same
seeding (1311*s+17 walk-forward; 2117*s+41 sweep), K=2, hard memory,
probe 15, min_dormancy 90, k=5, w_max=0.2, dd_thresh=0.15 primary with the
{10,12,20%} sweep, plus the registered 1926-57 / 1958-89 sub-era split.
Inherits the lodged Gamma-sign hypothesis (sign(Gamma) prices the pool:
Gamma>0 <-> dissociation ordering, Gamma<0 <-> inversion, Gamma~0 <-> flat);
every cell run here is scored for AND against that rule.

Zero new researcher degrees of freedom: every constant above is frozen from
the 1990-2025 scripts; only WINDOW differs.

Outputs (NEVER overwrites; stages skip if their output already exists):
  ../results/e_french49_prewar_L3_inventory.json
  ../results/e_french49_prewar_L3_gate.json
  ../results/e_french49_prewar_L3_dissoc.json
  ../results/e_french49_prewar_L3_sweep.json
  ../results/e_french49_prewar_L3_subera.json
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e_french
from risp import ARM_FACTORIES, run_arm, welch, holm
from run_experiments import summarize, PROBE
from realdata import RealMarket
from e_french import (build_xy_returns, price_panel, gate50, dormancy_diag,
                      ARMS, PAIRS, K_SEL, W_MAX, RESULTS)
from e_french_L3 import label_L3

WINDOW_ERA = ("1926-07-01", "1989-12-31")
SUB_ERAS = {"1926-1957": ("1926-07-01", "1957-12-31"),
            "1958-1989": ("1958-01-01", "1989-12-31")}
SEEDS = 20
MIN_DORM = 90
ARMS4 = ["A1-monolith-erm", "A5-risp-erm", "A6-risp-inv", "A9-oracle-pinned"]
# computable subset of the pre-registered 6-pair family when only 4 arms run
PAIRS4 = [p for p in PAIRS if p[0] in ARMS4 and p[1] in ARMS4]


def out_path(name):
    return RESULTS / f"e_french49_prewar_{name}.json"


def save_new(name, obj):
    p = out_path(name)
    assert not p.exists(), f"refusing to overwrite {p}"
    with open(p, "w") as fh:
        json.dump(obj, fh, indent=1, default=float)
    print(f"[saved] {p.resolve()}", flush=True)


_CACHE = {}


def prep(window):
    """Load + featurize a window. Identical pipeline to e_french_L3.main;
    the window is applied via the e_french.WINDOW module constant."""
    if window in _CACHE:
        return _CACHE[window]
    e_french.WINDOW = window
    ret, dropped = e_french.load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    dates = ret.index[idx]
    print(f"[prep {window[0]}..{window[1]}] {ret.shape[0]} days x "
          f"{ret.shape[1]} industries; dropped({len(dropped)})="
      f"{dropped}; feature days={len(X)}", flush=True)
    _CACHE[window] = (ret, dropped, X, Y, idx, px, dates)
    return _CACHE[window]


def crisis_inventory(lab, dates, px, idx, gap_merge=60):
    """Contiguous crisis-union (label>=2) runs + clusters (runs separated by
    <= gap_merge trading days merged, readability only)."""
    lp = np.log(px).mean(axis=1)
    dd = (1.0 - np.exp(lp.shift(1) - lp.cummax().shift(1))).values[idx]
    runs, t = [], 0
    while t < len(lab):
        if lab[t] >= 2:
            t1 = t
            while t1 + 1 < len(lab) and lab[t1 + 1] >= 2:
                t1 += 1
            runs.append({"start": str(dates[t].date()),
                         "end": str(dates[t1].date()),
                         "n_days": int(t1 - t + 1),
                         "max_dd": float(np.nanmax(dd[t:t1 + 1])),
                         "t0": int(t), "t1": int(t1)})
            t = t1 + 1
        else:
            t += 1
    clusters = []
    for r in runs:
        if clusters and r["t0"] - clusters[-1]["t1"] <= gap_merge:
            c = clusters[-1]
            c["t1"], c["end"] = r["t1"], r["end"]
            c["n_days"] += r["n_days"]
            c["n_runs"] += 1
            c["max_dd"] = max(c["max_dd"], r["max_dd"])
        else:
            clusters.append({**r, "n_runs": 1})
    return runs, clusters


def run_battery(X, Y, lab, arms, seed_mult, seed_add, seeds=SEEDS):
    """Walk-forward battery, byte-identical to e_french_L3.py walkforward
    (arm factory rng = default_rng(seed_mult*s+seed_add), K=2, hard)."""
    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    mkt = RealMarket(X, Y, lab, np.arange(len(X)))
    sched = mkt.schedule()
    diag = dormancy_diag(sched)
    res = {a: {"overall": [], "post_react": []} for a in arms}
    t0 = time.time()
    n_react = 0
    for s in range(seeds):
        for a in arms:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(
                seed_mult * s + seed_add), 2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM)
            res[a]["overall"].append(m["overall"])
            res[a]["post_react"].append(m["post_react"])
        if s == 0:
            n_react = m["n_react"]
            print(f"  seed0 {time.time() - t0:.0f}s n_react={n_react} "
                  f"T={sched.T}", flush=True)
    return res, diag, n_react, time.time() - t0


def eval_cell(res, pairs):
    """Gamma (paired A1-A9), Welch/Holm family, ordering, and the lodged
    Gamma-sign-rule verdict for one cell."""
    pv = {}
    for a, b in pairs:
        _, p = welch(res[a]["post_react"], res[b]["post_react"])
        pv[f"{a} vs {b}"] = p
    hp = holm(pv)
    d = (np.array(res["A1-monolith-erm"]["post_react"])
         - np.array(res["A9-oracle-pinned"]["post_react"]))
    se = d.std(ddof=1) / np.sqrt(len(d))
    gamma = {"mean": float(d.mean()), "ci95": float(1.96 * se),
             "positive_significant": bool(d.mean() - 1.96 * se > 0),
             "negative_significant": bool(d.mean() + 1.96 * se < 0)}
    a1 = float(np.mean(res["A1-monolith-erm"]["post_react"]))
    a5 = float(np.mean(res["A5-risp-erm"]["post_react"]))
    a6 = float(np.mean(res["A6-risp-inv"]["post_react"]))
    ordering = {"A1": a1, "A5": a5, "A6": a6,
                "A6<A5<A1": bool(a6 < a5 < a1)}
    if gamma["positive_significant"]:
        gcat = "positive"
    elif gamma["negative_significant"]:
        gcat = "negative"
    else:
        gcat = "zero"
    key = "A6-risp-inv vs A1-monolith-erm"
    p_a6a1 = hp.get(key)
    if p_a6a1 is not None and p_a6a1 < 0.05:
        ocat = "dissociation" if a6 < a1 else "inversion"
    else:
        ocat = "flat"
    expected = {"positive": "dissociation", "negative": "inversion",
                "zero": "flat"}[gcat]
    sign_rule = {"gamma_category": gcat, "ordering_category": ocat,
                 "holm_p_A6_vs_A1": p_a6a1,
                 "rule_predicts": expected,
                 "consistent": bool(expected == ocat)}
    return pv, hp, gamma, ordering, sign_rule


def cell_record(res, diag, n_react, pairs, extra=None):
    pv, hp, gamma, ordering, sr = eval_cell(res, pairs)
    rec = {"diag": diag, "n_react_evaluated": n_react,
           "post_react": summarize({a: res[a]["post_react"] for a in res}),
           "overall": summarize({a: res[a]["overall"] for a in res}),
           "welch_p": pv, "holm_p": hp,
           "gate2_forgetting_deficit": gamma,
           "ordering": ordering, "sign_rule": sr, "raw": res}
    if extra:
        rec.update(extra)
    return rec


# ---------------------------------------------------------------- stages ---

def stage_inventory():
    if out_path("L3_inventory").exists():
        print("[inventory] exists, skip", flush=True)
        return
    ret, dropped, X, Y, idx, px, dates = prep(WINDOW_ERA)
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
    counts = {int(r): int((lab == r).sum())
              for r in sorted(set(lab.tolist()))}
    print(f"L3@15% regime counts: {counts}", flush=True)
    runs, clusters = crisis_inventory(lab, dates, px, idx)
    print(f"crisis-union runs: {len(runs)}; clusters (gap<=60 td): "
          f"{len(clusters)}", flush=True)
    for c in clusters:
        print(f"  {c['start']} .. {c['end']}  n_days={c['n_days']:5d} "
              f"runs={c['n_runs']:2d} max_dd={c['max_dd']:.1%}", flush=True)
    save_new("L3_inventory", {
        "window": WINDOW_ERA, "dd_thresh": 0.15,
        "n_industries": int(ret.shape[1]), "dropped_industries": dropped,
        "regime_counts": counts,
        "crisis_union_runs": runs, "crisis_clusters_gap60": clusters})


def stage_gate():
    if out_path("L3_gate").exists():
        print("[gate] exists, skip", flush=True)
        return
    ret, dropped, X, Y, idx, px, dates = prep(WINDOW_ERA)
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
    print("[gate] L3@15%, 50 shuffles", flush=True)
    g = gate50(X, Y, lab)
    g["window"] = WINDOW_ERA
    g["dropped_industries"] = dropped
    print(f"prewar L3 gate: gap={g['gap_pct']:+.2f}% "
          f"z={g['z_vs_shuffled']:+.2f} p={g['p_one_sided']:.4g} "
          f"cond_vs_pooled={g['cond_vs_pooled_pct']:+.2f}% "
          f"PASS={g['PASS']}", flush=True)
    save_new("L3_gate", g)


def stage_dissoc():
    if out_path("L3_dissoc").exists():
        print("[dissoc] exists, skip", flush=True)
        return
    ret, dropped, X, Y, idx, px, dates = prep(WINDOW_ERA)
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
    print("[dissoc] walk-forward, 10 arms, 20 seeds (1311*s+17)", flush=True)
    res, diag, n_react, secs = run_battery(X, Y, lab, ARMS, 1311, 17)
    rec = cell_record(res, diag, n_react, PAIRS, extra={
        "window": WINDOW_ERA, "dd_thresh": 0.15,
        "seeding": "np.random.default_rng(1311*s+17) per arm",
        "config": {"seeds": SEEDS, "K": 2, "memory": "hard", "probe": PROBE,
                   "min_dormancy": MIN_DORM, "k": K_SEL, "w_max": W_MAX}})
    g = rec["gate2_forgetting_deficit"]
    print(f"[dissoc] Gamma={g['mean']:.5f}+-{g['ci95']:.5f} "
          f"pos_sig={g['positive_significant']} "
          f"neg_sig={g['negative_significant']} "
          f"ordering A6<A5<A1={rec['ordering']['A6<A5<A1']} "
          f"min raw p={min(rec['welch_p'].values()):.3g} "
          f"sign_rule={rec['sign_rule']} ({secs/60:.1f} min)", flush=True)
    save_new("L3_dissoc", {"walkforward": rec})


def stage_sweep():
    if out_path("L3_sweep").exists():
        print("[sweep] exists, skip", flush=True)
        return
    ret, dropped, X, Y, idx, px, dates = prep(WINDOW_ERA)
    out = {}
    for thresh in (0.10, 0.12, 0.20):
        lab = np.nan_to_num(label_L3(px, dd_thresh=thresh)[idx],
                            nan=0).astype(int)
        counts = {int(r): int((lab == r).sum())
                  for r in sorted(set(lab.tolist()))}
        print(f"[sweep {int(thresh*100)}%] counts={counts}", flush=True)
        res, diag, n_react, secs = run_battery(X, Y, lab, ARMS4, 2117, 41)
        rec = cell_record(res, diag, n_react, PAIRS4, extra={
            "window": WINDOW_ERA, "dd_thresh": thresh,
            "regime_counts": counts,
            "seeding": "np.random.default_rng(2117*s+41) per arm",
            "pairs_family": "4 computable of the pre-registered 6"})
        g = rec["gate2_forgetting_deficit"]
        print(f"[sweep {int(thresh*100)}%] Gamma={g['mean']:.5f}"
              f"+-{g['ci95']:.5f} ordering={rec['ordering']} "
              f"sign_rule={rec['sign_rule']} ({secs/60:.1f} min)",
              flush=True)
        out[f"{int(thresh*100)}pct"] = rec
    save_new("L3_sweep", out)


def stage_subera():
    if out_path("L3_subera").exists():
        print("[subera] exists, skip", flush=True)
        return
    out = {}
    for name, win in SUB_ERAS.items():
        ret, dropped, X, Y, idx, px, dates = prep(win)
        lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
        counts = {int(r): int((lab == r).sum())
                  for r in sorted(set(lab.tolist()))}
        runs, clusters = crisis_inventory(lab, dates, px, idx)
        print(f"[subera {name}] counts={counts} "
              f"crisis clusters={len(clusters)}", flush=True)
        res, diag, n_react, secs = run_battery(X, Y, lab, ARMS4, 1311, 17)
        rec = cell_record(res, diag, n_react, PAIRS4, extra={
            "window": win, "dd_thresh": 0.15,
            "n_industries": int(ret.shape[1]),
            "dropped_industries": dropped, "regime_counts": counts,
            "crisis_clusters_gap60": clusters,
            "seeding": "np.random.default_rng(1311*s+17) per arm",
            "pairs_family": "4 computable of the pre-registered 6"})
        g = rec["gate2_forgetting_deficit"]
        print(f"[subera {name}] Gamma={g['mean']:.5f}+-{g['ci95']:.5f} "
              f"ordering={rec['ordering']} sign_rule={rec['sign_rule']} "
              f"({secs/60:.1f} min)", flush=True)
        out[name] = rec
    save_new("L3_subera", out)


STAGES = {"inventory": stage_inventory, "gate": stage_gate,
          "dissoc": stage_dissoc, "sweep": stage_sweep,
          "subera": stage_subera}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(STAGES) if which == "all" else [which]
    for n in names:
        STAGES[n]()
    print("E-F PREWAR BATTERY: requested stages complete", flush=True)


if __name__ == "__main__":
    main()
