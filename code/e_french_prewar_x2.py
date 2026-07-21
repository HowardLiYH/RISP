"""
E-X2 era extension: the granularity-window map on the WITHHELD era
1926-07-01..1989-12-31 (36 complete industries, E-F conventions).

Lodged by the Addendum L supplement (2026-07-20, commit 1155f3c) BEFORE
any X2 output (modern or prewar) had been read. Byte-identical to
e_french_L3_x2.py except the window; island clause anchored at the era's
own paying threshold (10%, per Addendum F).

Output: ../results/e_french49_prewar_L3_x2.json
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e_french
from e_french import build_xy_returns, price_panel, RESULTS
import e_french_L3_x2 as x2
from e_french_L3_x2 import (THRESHOLDS, HYSTERESIS, TIER1_SEEDS, TIER2_SEEDS,
                            ARMS2, ARMS4, label_L3_hyst, run_cell,
                            ckpt_load, ckpt_save)
from e_french_prewar import PAIRS4
from risp import welch, holm
from run_experiments import summarize

WINDOW_ERA = ("1926-07-01", "1989-12-31")
ANCHOR_PCT = 10          # era's own paying threshold (Addendum F)


CKPT = "x2_prewar_ckpt.json"


def main():
    ck = ckpt_load(CKPT)
    e_french.WINDOW = WINDOW_ERA
    ret, dropped = e_french.load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    print(f"[x2-prewar] {ret.shape[0]} days x {ret.shape[1]} industries "
          f"(dropped {len(dropped)})", flush=True)

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
            ckpt_save(CKPT, ck)
            print(f"[t1pw {key}] occ={occ:.1%} n_react={n_react} "
                  f"G={gamma['mean']:+.5f}+-{gamma['ci95']:.5f} "
                  f"ci>0={gamma['ci_gt_0']} ci<0={gamma['ci_lt_0']} "
                  f"({(time.time()-t0)/60:.1f} min)", flush=True)

    adjudication = {}
    any_window, window_includes_anchor = False, False
    positives = set()
    for h in HYSTERESIS:
        flags = [bool(tier1[f"th{round(th*100)}_h{round(h*100)}"]
                      ["gamma_A1_minus_A9"]["ci_gt_0"])
                 for th in THRESHOLDS]
        for th, f in zip(THRESHOLDS, flags):
            if f:
                positives.add((round(th * 100), round(h * 100)))
        best, cur, runs = 0, 0, []
        start = None
        for i, f in enumerate(flags):
            if f:
                cur += 1
                if start is None:
                    start = i
            else:
                if start is not None:
                    runs.append((start, i - 1))
                start, cur = None, 0
            best = max(best, cur)
        if start is not None:
            runs.append((start, len(flags) - 1))
        for a, b in runs:
            if (b - a + 1) >= 3 and any(
                    round(THRESHOLDS[i] * 100) == ANCHOR_PCT
                    for i in range(a, b + 1)):
                window_includes_anchor = True
        adjudication[f"h{round(h*100)}"] = {
            "positive_thresholds_pct": [round(th * 100) for th, f
                                        in zip(THRESHOLDS, flags) if f],
            "longest_contiguous_run": best,
            "window_here": bool(best >= 3)}
        any_window = any_window or best >= 3
    island = positives == {(ANCHOR_PCT, 0)}
    verdict = ("window" if any_window
               else ("island" if island else "ambiguous"))

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
        ckpt_save(CKPT, ck)
        print(f"[t2pw {key}] G={gamma['mean']:+.5f}+-{gamma['ci95']:.5f} "
              f"A6<A5<A1={tier2[key]['ordering']['A6<A5<A1']} "
              f"minHolm={min(hp.values()):.3g}", flush=True)

    out = {"prereg": ("E-X2 era extension, Addendum L supplement "
                      "(commit 1155f3c), lodged before any X2 output "
                      "was read"),
           "window": WINDOW_ERA, "anchor_pct": ANCHOR_PCT,
           "config": {"thresholds_pct": [round(t * 100) for t in THRESHOLDS],
                      "hysteresis_pp": [round(h * 100) for h in HYSTERESIS],
                      "tier1_seeds": TIER1_SEEDS, "tier2_seeds": TIER2_SEEDS,
                      "seeding": "1311*s+17"},
           "tier1": tier1,
           "adjudication_per_hysteresis": adjudication,
           "positive_cells_theta_h_pct": sorted(positives),
           "PX2e_window_includes_anchor_10": bool(window_includes_anchor),
           "verdict": verdict,
           "tier2": tier2}
    with open(RESULTS / "e_french49_prewar_L3_x2.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"[x2-prewar] VERDICT: {verdict}; PX2e(anchor-in-window)="
          f"{window_includes_anchor}; positives={sorted(positives)}",
          flush=True)
    print("[saved] results/e_french49_prewar_L3_x2.json", flush=True)


if __name__ == "__main__":
    main()
