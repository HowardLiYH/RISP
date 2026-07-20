"""
E-R regional battery, region 1 of the lodged fixed order: JAPAN.

Registered: E-R (PRE-REGISTRATION E, lodged 2026-07-15, commit 5c96c35)
operationalized by Addendum L (lodged 2026-07-20, commit dfd9fe7, pushed
ALONE before any run touched the Japanese data). Region-specific sign
prediction restated from E-R: "Japan's crisis-cell dormancy 1990-2012 is
SHORT (crisis frequent) -> Gamma_Japan ~ 0 or negative expected."

Data: Ken French Data Library, Japan 25 ME x BE/ME portfolios, Average
Value Weighted Returns -- Daily (data/french_intl/, vendored, sha256 in
Addendum L). Window 1990-07-02 .. 2025-12-31.

Battery: byte-identical to e_french_prewar.py conventions — L3@15%
primary + {10,12,20%} sweep, gate50 structure screen, walk-forward
dissociation arms {A1,A5,A6,A9}, 20 seeds (1311*s+17; sweep 2117*s+41),
K=2, hard memory, probe 15, min_dormancy 90, k=5 of 25, w_max=0.2 (E-R).

Outputs (never overwrites; stages skip if their output exists):
  ../results/e_japan_L3_inventory.json
  ../results/e_japan_L3_gate.json
  ../results/e_japan_L3_dissoc.json
  ../results/e_japan_L3_sweep.json
"""
from __future__ import annotations
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e_french import (build_xy_returns, price_panel, gate50, dormancy_diag,
                      RESULTS)
from e_french_L3 import label_L3
from e_french_prewar import (crisis_inventory, run_battery, cell_record,
                             ARMS4, PAIRS4)

CSV_JP = (Path(__file__).resolve().parent / ".." / "data" / "french_intl"
          / "Japan_25_Portfolios_ME_BE-ME_Daily.csv")
WINDOW_JP = ("1990-07-02", "2025-12-31")
K_SEL, W_MAX = 5, 0.2                      # as lodged in E-R: k=5 of 25
SEEDS = 20


def out_path(name):
    return RESULTS / f"e_japan_{name}.json"


def save_new(name, obj):
    p = out_path(name)
    assert not p.exists(), f"refusing to overwrite {p}"
    with open(p, "w") as fh:
        json.dump(obj, fh, indent=1, default=float)
    print(f"[saved] {p.resolve()}", flush=True)


def load_japan_vw():
    """Value-weighted daily RETURN panel (decimal), Japan 25 ME x BE/ME.

    Parses the FIRST data block of the French-library file (the
    'Average Value Weighted Returns -- Daily' section), per Addendum L.
    """
    lines = CSV_JP.read_text().splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.lstrip().startswith(",SMALL LoBM"))
    end = next(i for i in range(start + 1, len(lines))
               if not lines[i][:8].strip().isdigit())
    df = pd.read_csv(io.StringIO("\n".join([lines[start]] +
                                           lines[start + 1:end])),
                     skipinitialspace=True)
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"].astype(str).str.strip(),
                                format="%Y%m%d")
    df = df.set_index("date").loc[WINDOW_JP[0]:WINDOW_JP[1]]
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.replace([-99.99, -999.0], np.nan) / 100.0
    dropped = [c for c in df.columns if df[c].isna().any()]
    df = df.drop(columns=dropped)
    return df, dropped


_CACHE = {}


def prep():
    if "jp" in _CACHE:
        return _CACHE["jp"]
    ret, dropped = load_japan_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    dates = ret.index[idx]
    print(f"[prep JP {WINDOW_JP[0]}..{WINDOW_JP[1]}] {ret.shape[0]} days x "
          f"{ret.shape[1]} portfolios; dropped({len(dropped)})={dropped}; "
          f"feature days={len(X)}", flush=True)
    _CACHE["jp"] = (ret, dropped, X, Y, idx, px, dates)
    return _CACHE["jp"]


def stage_inventory():
    if out_path("L3_inventory").exists():
        print("[inventory] exists, skip", flush=True)
        return
    ret, dropped, X, Y, idx, px, dates = prep()
    out = {"window": WINDOW_JP, "n_portfolios": int(ret.shape[1]),
           "dropped_portfolios": dropped, "thresholds": {}}
    for thresh in (0.10, 0.12, 0.15, 0.20):
        lab = np.nan_to_num(label_L3(px, dd_thresh=thresh)[idx],
                            nan=0).astype(int)
        counts = {int(r): int((lab == r).sum())
                  for r in sorted(set(lab.tolist()))}
        occ = float(np.mean(lab >= 2))
        runs, clusters = crisis_inventory(lab, dates, px, idx)
        print(f"[inventory {int(thresh*100)}%] counts={counts} "
              f"crisis-union occupancy={occ:.1%} clusters={len(clusters)}",
              flush=True)
        for c in clusters:
            print(f"  {c['start']} .. {c['end']}  n_days={c['n_days']:5d} "
                  f"runs={c['n_runs']:2d} max_dd={c['max_dd']:.1%}",
                  flush=True)
        out["thresholds"][f"{int(thresh*100)}pct"] = {
            "regime_counts": counts, "crisis_union_occupancy": occ,
            "crisis_union_runs": runs, "crisis_clusters_gap60": clusters}
    save_new("L3_inventory", out)


def stage_gate():
    if out_path("L3_gate").exists():
        print("[gate] exists, skip", flush=True)
        return
    ret, dropped, X, Y, idx, px, dates = prep()
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
    print("[gate] JP L3@15%, 50 shuffles (structure screen per Addendum F "
          "demotion)", flush=True)
    g = gate50(X, Y, lab)
    g["window"] = WINDOW_JP
    g["dropped_portfolios"] = dropped
    print(f"JP L3 gate: gap={g['gap_pct']:+.2f}% z={g['z_vs_shuffled']:+.2f} "
          f"p={g['p_one_sided']:.4g} cond_vs_pooled="
          f"{g['cond_vs_pooled_pct']:+.2f}% PASS={g['PASS']}", flush=True)
    save_new("L3_gate", g)


def stage_dissoc():
    if out_path("L3_dissoc").exists():
        print("[dissoc] exists, skip", flush=True)
        return
    ret, dropped, X, Y, idx, px, dates = prep()
    lab = np.nan_to_num(label_L3(px)[idx], nan=0).astype(int)
    print("[dissoc] JP walk-forward, arms {A1,A5,A6,A9}, 20 seeds "
          "(1311*s+17)", flush=True)
    res, diag, n_react, secs = run_battery(X, Y, lab, ARMS4, 1311, 17,
                                           seeds=SEEDS)
    rec = cell_record(res, diag, n_react, PAIRS4, extra={
        "window": WINDOW_JP, "dd_thresh": 0.15,
        "seeding": "np.random.default_rng(1311*s+17) per arm",
        "pairs_family": "4 computable of the pre-registered 6",
        "prereg": "E-R (commit 5c96c35) + Addendum L (commit dfd9fe7)",
        "region_prediction": "Gamma_Japan ~ 0 or negative (E-R verbatim)",
        "config": {"seeds": SEEDS, "K": 2, "memory": "hard", "probe": 15,
                   "min_dormancy": 90, "k": K_SEL, "w_max": W_MAX}})
    g = rec["gate2_forgetting_deficit"]
    print(f"[dissoc JP] Gamma={g['mean']:.5f}+-{g['ci95']:.5f} "
          f"pos_sig={g['positive_significant']} "
          f"neg_sig={g['negative_significant']} "
          f"ordering={rec['ordering']} sign_rule={rec['sign_rule']} "
          f"({secs/60:.1f} min)", flush=True)
    save_new("L3_dissoc", {"walkforward": rec})


def stage_sweep():
    if out_path("L3_sweep").exists():
        print("[sweep] exists, skip", flush=True)
        return
    ret, dropped, X, Y, idx, px, dates = prep()
    out = {}
    for thresh in (0.10, 0.12, 0.20):
        lab = np.nan_to_num(label_L3(px, dd_thresh=thresh)[idx],
                            nan=0).astype(int)
        counts = {int(r): int((lab == r).sum())
                  for r in sorted(set(lab.tolist()))}
        print(f"[sweep JP {int(thresh*100)}%] counts={counts}", flush=True)
        res, diag, n_react, secs = run_battery(X, Y, lab, ARMS4, 2117, 41,
                                               seeds=SEEDS)
        rec = cell_record(res, diag, n_react, PAIRS4, extra={
            "window": WINDOW_JP, "dd_thresh": thresh,
            "regime_counts": counts,
            "seeding": "np.random.default_rng(2117*s+41) per arm",
            "pairs_family": "4 computable of the pre-registered 6"})
        g = rec["gate2_forgetting_deficit"]
        print(f"[sweep JP {int(thresh*100)}%] Gamma={g['mean']:.5f}"
              f"+-{g['ci95']:.5f} ordering={rec['ordering']} "
              f"sign_rule={rec['sign_rule']} ({secs/60:.1f} min)",
              flush=True)
        out[f"{int(thresh*100)}pct"] = rec
    save_new("L3_sweep", out)


STAGES = {"inventory": stage_inventory, "gate": stage_gate,
          "dissoc": stage_dissoc, "sweep": stage_sweep}


def main():
    import e_french
    assert (e_french.K_SEL, e_french.W_MAX) == (K_SEL, W_MAX), \
        "gate50/regret_series K_SEL/W_MAX desynchronized from E-R terms"
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for n in (list(STAGES) if which == "all" else [which]):
        STAGES[n]()
    print("E-R JAPAN BATTERY: requested stages complete", flush=True)


if __name__ == "__main__":
    main()
