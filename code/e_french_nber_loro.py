"""
Leave-one-reactivation-out (LORO) + era-blocked analysis for the E-NBER
primary (announcement-lagged) walk-forward deficit -- the robustness
supplement owed to the register (see meta.disclosed_omissions in
results/e_french49_nber_dissoc.json and PREREG_FRENCH49.md addendum G).

Reviewer objection addressed: is the NBER walk-forward forgetting deficit
Gamma = post_react(A1-monolith-erm) - post_react(A9-oracle-pinned)
carried by a single reactivation event (e.g. 2008 or 2020)?

Protocol: identical analysis pattern to e_french_L3_loro.py. Reruns ONLY
the four relevant walk-forward arms with EXACTLY the same config and
seeding as e_french_nber.py's walk-forward loop (rng 1311*s+17 per arm,
20 seeds, K=2, hard memory, probe=15, min_dormancy=90, k=5, w_max=0.2),
under the L-NBER labeler's PRIMARY announcement-lagged variant (verified
dates imported read-only from e_french_nber.py). The only addition is
collect_react=True, which is purely observational; the cost overlay is
omitted because it is accounting-only (trajectories unchanged, per
risp.run_arm) and the sanity target is the gross post_react. A hard
sanity check asserts the recomputed aggregate post_react per seed matches
results/e_french49_nber_dissoc.json primary_announcement_lagged
walkforward raw values exactly, proving the instrumentation changed
nothing.

No tuning, no selection: every qualifying reactivation is reported, and
the exclusions fixed in this file before it was first run are the ones
named in the follow-up assignment: drop-2020, drop-2008/09 (plus the
drop-2008..2010 span, since the announcement-lagged recession window runs
to 2010-09-20), and drop-2001 if any 2001 reactivation is present; plus
per-decade era blocks for both A1-A9 and A1-A6.

Output: ../results/e_french49_nber_loro.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, run_arm
from run_experiments import PROBE
from realdata import RealMarket
from e_french import load_french_vw, build_xy_returns, price_panel, \
    K_SEL, W_MAX, RESULTS
from e_french_nber import label_LNBER, NBER_EPISODES, NBER_SOURCE

SEEDS = 20
MIN_DORM = 90
LORO_ARMS = ["A1-monolith-erm", "A5-risp-erm", "A6-risp-inv",
             "A9-oracle-pinned"]
CONTRASTS = {"A1_minus_A9": ("A1-monolith-erm", "A9-oracle-pinned"),
             "A1_minus_A6": ("A1-monolith-erm", "A6-risp-inv")}


def mean_ci(xs):
    xs = np.asarray(xs, dtype=float)
    m = float(xs.mean())
    h = float(1.96 * xs.std(ddof=1) / np.sqrt(len(xs))) if len(xs) > 1 else 0.0
    return m, h


def main():
    ret, dropped = load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    dates = ret.index[idx]                      # calendar date of market day t
    px = price_panel(ret)
    # PRIMARY announcement-lagged variant, identical construction to
    # e_french_nber.main (nan_to_num is a no-op on the int labels; kept
    # verbatim for exactness).
    lab = np.nan_to_num(label_LNBER(px, "announced")[idx].astype(float),
                        nan=0).astype(int)

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
    sched = mkt.schedule()
    T = sched.T
    half = int(T * 0.5)

    # ---- fixed reactivation geometry (identical for all arms/seeds) ----
    react_all = sched.reactivation_days(MIN_DORM)
    windows = []                                # (t0, lo, hi) clipped windows
    for t0 in react_all:
        lo, hi = max(int(t0), half), min(int(t0) + PROBE, T)
        if hi > lo:
            windows.append((int(t0), lo, hi))
    n_react = len(windows)
    masks = np.zeros((n_react, T), dtype=bool)
    for i, (t0, lo, hi) in enumerate(windows):
        masks[i, lo:hi] = True
    overlap_days = int((masks.sum(axis=0) > 1).sum())

    REGIME_NAMES = {0: "expansion-up", 1: "expansion-down",
                    2: "recession-up", 3: "recession-down"}
    inventory = []
    for i, (t0, lo, hi) in enumerate(windows):
        inventory.append({
            "i": i, "t_start": t0,
            "date": str(dates[t0].date()),
            "year": int(dates[t0].year),
            "era": f"{dates[t0].year // 10 * 10}s",
            "regime": int(sched.regimes[t0]),
            "regime_name": REGIME_NAMES[int(sched.regimes[t0])],
            "dormancy": int(sched.dormancy[t0]),
            "n_probe_days_counted": int(hi - lo),
        })
    print(f"T={T} half={half} qualifying reactivations (window intersects "
          f"second half): {n_react}; overlap days={overlap_days}", flush=True)
    for r in inventory:
        print(f"  #{r['i']:2d} {r['date']} regime={r['regime']} "
              f"({r['regime_name']}) dormancy={r['dormancy']:4d}d "
              f"days={r['n_probe_days_counted']}", flush=True)

    # ---- rerun the four arms, identical seeding to e_french_nber.py ----
    daily_probe = {a: np.zeros((SEEDS, T)) for a in LORO_ARMS}  # daily regret
    agg_post = {a: [] for a in LORO_ARMS}
    detail_reg = {a: np.zeros((SEEDS, n_react)) for a in LORO_ARMS}
    t0c = time.time()
    for s in range(SEEDS):
        for a in LORO_ARMS:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(1311 * s + 17),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM, collect_react=True)
            agg_post[a].append(m["post_react"])
            daily_probe[a][s] = m["daily"]
            det = {d["t_start"]: d["mean_probe_regret"]
                   for d in m["react_detail"]}
            assert set(det) == {w[0] for w in windows}
            for i, (tt, lo, hi) in enumerate(windows):
                detail_reg[a][s, i] = det[tt]
        print(f"seed {s} done ({time.time()-t0c:.0f}s)", flush=True)

    # ---- sanity check vs the published headline file ----
    ref = json.load(open(RESULTS / "e_french49_nber_dissoc.json"))
    wf = ref["primary_announcement_lagged"]["walkforward"]
    sanity = {}
    for a in LORO_ARMS:
        got = np.array(agg_post[a])
        exp = np.array(wf["raw"][a]["post_react"])
        sanity[a] = {"max_abs_diff": float(np.abs(got - exp).max()),
                     "match": bool(np.allclose(got, exp, rtol=0, atol=1e-12))}
        print(f"sanity {a}: max|diff|={sanity[a]['max_abs_diff']:.3e} "
              f"match={sanity[a]['match']}", flush=True)
    assert all(v["match"] for v in sanity.values()), \
        "instrumented rerun does not reproduce the headline file"

    # ---- helper: contrast deficit over an arbitrary subset of windows ----
    def deficit(contrast, keep):
        """Mean +/- CI over seeds of mean-daily-regret difference over the
        union of the kept probe windows (day-level, matches post_react)."""
        a, b = CONTRASTS[contrast]
        if not any(keep):
            return {"mean": None, "ci95": None, "n_react": 0}
        mask = masks[np.array(keep)].any(axis=0)
        d = daily_probe[a][:, mask].mean(axis=1) \
            - daily_probe[b][:, mask].mean(axis=1)
        m, h = mean_ci(d)
        return {"mean": m, "ci95": h, "n_react": int(sum(keep)),
                "n_days": int(mask.sum()),
                "positive_significant": bool(m - h > 0),
                "negative_significant": bool(m + h < 0)}

    all_keep = [True] * n_react
    years_present = sorted({r["year"] for r in inventory})
    out = {"config": {"seeds": SEEDS, "K": 2, "memory": "hard",
                      "probe": PROBE, "min_dormancy": MIN_DORM,
                      "k": K_SEL, "w_max": W_MAX,
                      "labeler": "L-NBER primary announcement-lagged "
                                 "(causal), imported from e_french_nber."
                                 "label_LNBER; no free threshold",
                      "nber_episodes": [
                          {"calendar_peak": p, "calendar_trough": t,
                           "start_announced": a, "end_announced": e}
                          for p, t, a, e in NBER_EPISODES],
                      "nber_source": NBER_SOURCE,
                      "seeding": "np.random.default_rng(1311*s+17) per arm",
                      "arms": LORO_ARMS,
                      "note": "cost overlay omitted: accounting-only in "
                              "risp.run_arm (trajectories unchanged); "
                              "sanity target is the gross post_react"},
           "owed_to": "results/e_french49_nber_dissoc.json "
                      "meta.disclosed_omissions; PREREG_FRENCH49.md "
                      "addendum G",
           "sanity_vs_headline": sanity,
           "n_qualifying_reactivations": n_react,
           "overlap_days": overlap_days,
           "years_present": years_present,
           "reactivation_inventory": inventory,
           "contrasts": {}}

    for cname in CONTRASTS:
        a, b = CONTRASTS[cname]
        # per-reactivation Gamma_i averaged over seeds
        per_react = []
        for i, r in enumerate(inventory):
            g = detail_reg[a][:, i] - detail_reg[b][:, i]
            m, h = mean_ci(g)
            per_react.append({**{k: r[k] for k in
                                 ("i", "date", "year", "era", "regime",
                                  "regime_name", "dormancy",
                                  "n_probe_days_counted")},
                              "gamma_i_mean": m, "gamma_i_ci95": h})
        full = deficit(cname, all_keep)
        # LORO: drop one reactivation at a time
        loro = []
        for i in range(n_react):
            keep = [j != i for j in range(n_react)]
            d = deficit(cname, keep)
            loro.append({"dropped_i": i, "dropped_date": inventory[i]["date"],
                         **d})
        loro_means = [l["mean"] for l in loro]

        # calendar-year exclusions named in the follow-up assignment
        def drop_years(years):
            keep = [r["year"] not in years for r in inventory]
            return deficit(cname, keep)
        exclusions = {
            "drop_2020": drop_years({2020}),
            "drop_2008_2009": drop_years({2008, 2009}),
            "drop_2008_2010": drop_years({2008, 2009, 2010}),
        }
        if 2001 in years_present:
            exclusions["drop_2001"] = drop_years({2001})
        else:
            exclusions["drop_2001"] = {
                "mean": None, "ci95": None, "n_react": None,
                "note": "no 2001 reactivation qualifies (window must "
                        "intersect the evaluated second half); exclusion "
                        "vacuous"}
        # era-blocked: deficit WITHIN each decade
        eras = {}
        for era in sorted({r["era"] for r in inventory}):
            keep = [r["era"] == era for r in inventory]
            eras[era] = deficit(cname, keep)
        out["contrasts"][cname] = {
            "full": full,
            "per_reactivation_gamma": per_react,
            "loro": loro,
            "loro_min": min(loro, key=lambda l: l["mean"]),
            "loro_max": max(loro, key=lambda l: l["mean"]),
            "calendar_exclusions": exclusions,
            "era_blocked": eras,
        }
        print(f"\n[{cname}] full={full['mean']:.5f}±{full['ci95']:.5f} "
              f"(n_react={full['n_react']})", flush=True)
        print(f"  LORO min={min(loro_means):.5f} "
              f"(drop {out['contrasts'][cname]['loro_min']['dropped_date']}) "
              f"max={max(loro_means):.5f} "
              f"(drop {out['contrasts'][cname]['loro_max']['dropped_date']})",
              flush=True)
        for k, v in exclusions.items():
            if v["mean"] is None:
                print(f"  {k}: {v.get('note', 'empty')}", flush=True)
            else:
                print(f"  {k}: {v['mean']:.5f}±{v['ci95']:.5f} "
                      f"(n_react={v['n_react']}) "
                      f"sig+={v['positive_significant']}", flush=True)
        for era, v in eras.items():
            print(f"  era {era}: {v['mean']:.5f}±{v['ci95']:.5f} "
                  f"(n_react={v['n_react']}) "
                  f"sig+={v['positive_significant']}", flush=True)

    with open(RESULTS / "e_french49_nber_loro.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("\nNBER LORO ANALYSIS COMPLETE ->",
          RESULTS / "e_french49_nber_loro.json", flush=True)


if __name__ == "__main__":
    main()
