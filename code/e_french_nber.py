"""
French 49-industry battery, L-NBER labeler (NBER-recession-anchored, no
free threshold). OSF-lodged forward test.

Pre-registered in ../osf_package/PREREG_NBER_FRENCH49.md, lodged at
osf.io/nsx4e 2026-07-15 22:47 ET BEFORE NBER dates were joined to any
panel. Design identical to PREREG_FRENCH49 (pre-registration A) in every
respect except the labeler; verdict conventions per addendum F (weak and
strong sign-rule forms both scored).

Labeler L-NBER (4 regimes): NBER recession indicator x 50-day trend sign
of the equal-weight log-price index (trend causal via t-1, identical
construction to label_L3's trend). No free threshold anywhere.
  PRIMARY (causal): recession state as knowable at day t -- recession = 1
  from the NBER start-announcement date through the end-announcement date
  (inclusive), per episode.
  SECONDARY (robustness, disclosed as non-causal): calendar recession
  months themselves (peak month through trough month, inclusive).

Announcement dates verified 2026-07-15 from
https://www.nber.org/research/business-cycle-dating/business-cycle-dating-committee-announcements
(fetched via web; all four pairs match the registration's expected values).

Outputs: ../results/e_french49_nber_gate.json,
         ../results/e_french49_nber_dissoc.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, run_arm, welch, holm
from run_experiments import summarize, PROBE
from realdata import BlockLibrary, StitchedMarket, RealMarket
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      gate50, dormancy_diag, ARMS, PAIRS, K_SEL, W_MAX,
                      RESULTS)

COST_BPS = 25.0  # lodged net overlay (both-pay convention, run_arm default)

# ---------------------------------------------------------------------------
# NBER dates. Calendar peak/trough months from NBER business cycle dates;
# announcement dates VERIFIED 2026-07-15 from nber.org (see module docstring).
# ---------------------------------------------------------------------------
NBER_EPISODES = [
    # (calendar peak month, calendar trough month,
    #  start announced,       end announced)
    ("1990-07", "1991-03", "1991-04-25", "1992-12-22"),
    ("2001-03", "2001-11", "2001-11-26", "2003-07-17"),
    ("2007-12", "2009-06", "2008-12-01", "2010-09-20"),
    ("2020-02", "2020-04", "2020-06-08", "2021-07-19"),
]
NBER_SOURCE = ("https://www.nber.org/research/business-cycle-dating/"
               "business-cycle-dating-committee-announcements")


def recession_indicator(dates: pd.DatetimeIndex, variant: str) -> np.ndarray:
    """1 where the recession state is on, per variant.

    'announced' (PRIMARY, causal): on from start-announcement date through
      end-announcement date, inclusive of both endpoints.
    'calendar' (SECONDARY, non-causal): on from the first day of the peak
      month through the last day of the trough month, inclusive.
    """
    rec = np.zeros(len(dates), dtype=int)
    for peak, trough, ann_start, ann_end in NBER_EPISODES:
        if variant == "announced":
            lo = pd.Timestamp(ann_start)
            hi = pd.Timestamp(ann_end)
        elif variant == "calendar":
            lo = pd.Timestamp(peak + "-01")
            hi = (pd.Timestamp(trough + "-01")
                  + pd.offsets.MonthEnd(0))
        else:
            raise ValueError(variant)
        rec[(dates >= lo) & (dates <= hi)] = 1
    return rec


def label_LNBER(px: pd.DataFrame, variant: str, trend_win=50) -> np.ndarray:
    """NBER recession state x 50-day trend sign. Trend causal via t-1,
    identical construction to label_L3's trend. 4 regimes:
    0 expansion-up, 1 expansion-down, 2 recession-up, 3 recession-down."""
    lp = np.log(px).mean(axis=1)
    trend = (lp.shift(1) - lp.shift(trend_win + 1)).fillna(0.0)
    up = (trend > 0).astype(int)
    rec = recession_indicator(px.index, variant)
    return (rec * 2 + (1 - up.values)).astype(int)


def run_dissoc(X, Y, idx, lab, cfg, seeds, tag):
    """Both schedule designs for one labeler variant. Conventions of
    pre-registration A / e_french_L3.py: 20 seeds, arms 1311*s+17 (wf) and
    1733*s+29 (stitched), schedules 5000+s, K=2, hard, probe 15,
    min_dormancy 90, min_len=8; cost overlay at 25 bps (accounting only,
    trajectories unchanged)."""
    out = {}
    for design in ("walkforward", "stitched"):
        res = {a: {"overall": [], "post_react": [],
                   "overall_net": [], "post_react_net": [],
                   "post_react_net_armonly": [],
                   "mean_turnover": []} for a in ARMS}
        t0 = time.time()
        deviation_notes = []
        if design == "walkforward":
            mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
            sched = mkt.schedule()
            diag = dormancy_diag(sched)
            print(f"[{tag}/wf] dormancy diag: {diag}", flush=True)
            for s in range(seeds):
                for a in ARMS:
                    arm = ARM_FACTORIES[a](cfg, np.random.default_rng(
                        1311 * s + 17), 2, "hard")
                    m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                                min_dormancy=90, cost_bps=COST_BPS)
                    res[a]["overall"].append(m["overall"])
                    res[a]["post_react"].append(m["post_react"])
                    res[a]["overall_net"].append(m["cost"]["overall_net"])
                    res[a]["post_react_net"].append(
                        m["cost"]["post_react_net"])
                    res[a]["post_react_net_armonly"].append(
                        m["cost"]["post_react_net_armonly"])
                    res[a]["mean_turnover"].append(
                        m["cost"]["mean_turnover_arm"])
                if s == 0:
                    print(f"  seed0 {time.time()-t0:.0f}s "
                          f"n_react={m['n_react']} T={sched.T}", flush=True)
        else:
            lib = BlockLibrary(X, Y, lab.astype(float), np.arange(len(idx)),
                               min_len=8)
            counts = lib.counts()
            # Registered: rare = least-frequent RECESSION cell (r in {2,3}).
            rec_pool = {r: c for r, c in counts.items()
                        if r >= 2 and c > 0}
            if rec_pool:
                rare = min(rec_pool, key=rec_pool.get)
                if len(rec_pool) < 2:
                    deviation_notes.append(
                        "DEVIATION NOTE: only one recession cell has any "
                        "block of min_len=8; 'least-frequent recession "
                        "cell' selects it by default.")
            else:
                rare = min({r: c for r, c in counts.items() if c > 0},
                           key=lambda r: counts[r])
                deviation_notes.append(
                    "LOUD DEVIATION: NO recession cell has any block of "
                    "min_len=8; fell back to the least-frequent nonempty "
                    "cell overall. The registered stitched design could "
                    "not be run as specified.")
            others = [r for r in range(4) if r != rare and counts[r] > 0]
            diag = {"block_counts": counts, "rare": rare,
                    "deviation_notes": deviation_notes}
            print(f"[{tag}/st] blocks={counts} rare(recession)={rare} "
                  f"{deviation_notes}", flush=True)
            for s in range(seeds):
                rng = np.random.default_rng(5000 + s)
                seq = []
                for cyc in range(16):
                    for r in rng.permutation(others):
                        seq.append((int(r), int(rng.integers(25, 50))))
                    if cyc % 3 == 2:
                        seq.append((int(rare), int(rng.integers(15, 30))))
                mkt = StitchedMarket(lib, rng)
                sched = mkt.materialize(seq)
                for a in ARMS:
                    arm = ARM_FACTORIES[a](cfg, np.random.default_rng(
                        1733 * s + 29), 2, "hard")
                    m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                                min_dormancy=90, cost_bps=COST_BPS)
                    res[a]["overall"].append(m["overall"])
                    res[a]["post_react"].append(m["post_react"])
                    res[a]["overall_net"].append(m["cost"]["overall_net"])
                    res[a]["post_react_net"].append(
                        m["cost"]["post_react_net"])
                    res[a]["post_react_net_armonly"].append(
                        m["cost"]["post_react_net_armonly"])
                    res[a]["mean_turnover"].append(
                        m["cost"]["mean_turnover_arm"])
        pv, pv_net = {}, {}
        for a, b in PAIRS:
            _, p = welch(res[a]["post_react"], res[b]["post_react"])
            pv[f"{a} vs {b}"] = p
            _, pn = welch(res[a]["post_react_net"], res[b]["post_react_net"])
            pv_net[f"{a} vs {b}"] = pn

        def gamma_of(key):
            d = (np.array(res["A1-monolith-erm"][key])
                 - np.array(res["A9-oracle-pinned"][key]))
            ci = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            return {"mean": float(d.mean()), "ci95": float(ci),
                    "positive_significant": bool(d.mean() - ci > 0),
                    "negative_significant": bool(d.mean() + ci < 0)}

        gamma = gamma_of("post_react")
        gamma_net = gamma_of("post_react_net")
        out[design] = {
            "diag": diag,
            "post_react": summarize({a: res[a]["post_react"]
                                     for a in ARMS}),
            "overall": summarize({a: res[a]["overall"] for a in ARMS}),
            "post_react_net25": summarize({a: res[a]["post_react_net"]
                                           for a in ARMS}),
            "overall_net25": summarize({a: res[a]["overall_net"]
                                        for a in ARMS}),
            "mean_turnover": {a: float(np.mean(res[a]["mean_turnover"]))
                              for a in ARMS},
            "welch_p": pv, "holm_p": holm(pv),
            "welch_p_net25": pv_net, "holm_p_net25": holm(pv_net),
            "gate2_forgetting_deficit": gamma,
            "gate2_forgetting_deficit_net25": gamma_net,
            "cost_bps": COST_BPS,
            "raw": res}
        print(f"[{tag}/{design}] Γ={gamma['mean']:.5f}±{gamma['ci95']:.5f} "
              f"sig+={gamma['positive_significant']} "
              f"Γ_net={gamma_net['mean']:.5f}±{gamma_net['ci95']:.5f}; "
              f"min raw p={min(pv.values()):.4g} "
              f"({(time.time()-t0)/60:.1f} min)", flush=True)
    return out


def sign_rule_verdicts(block):
    """Addendum-F conventions. 'Ordering' = A6 significantly below A1
    (Holm<0.05 on the registered A6-vs-A1 pair, means in that direction);
    'inversion' = the same pair significant the other way. Weak form:
    ordering iff Γ̂ significantly positive. Strong directional form:
    sig-positive→ordering, sig-negative→inversion, n.s.→flat."""
    g = block["gate2_forgetting_deficit"]
    key = "A6-risp-inv vs A1-monolith-erm"
    hp = block["holm_p"][key]
    m6 = block["post_react"]["A6-risp-inv"]["mean"]
    m1 = block["post_react"]["A1-monolith-erm"]["mean"]
    ordering = bool(hp < 0.05 and m6 < m1)
    inversion = bool(hp < 0.05 and m6 > m1)
    full_ordering = all(
        block["holm_p"][k] < 0.05 and
        block["post_react"][a]["mean"] < block["post_react"][b]["mean"]
        for k, (a, b) in [
            ("A6-risp-inv vs A5-risp-erm", ("A6-risp-inv", "A5-risp-erm")),
            ("A6-risp-inv vs A1-monolith-erm",
             ("A6-risp-inv", "A1-monolith-erm")),
            ("A5-risp-erm vs A1-monolith-erm",
             ("A5-risp-erm", "A1-monolith-erm"))])
    sig_pos, sig_neg = g["positive_significant"], g["negative_significant"]
    weak_hit = (sig_pos and ordering) or (not sig_pos and not ordering)
    if sig_pos:
        strong_hit = ordering
    elif sig_neg:
        strong_hit = inversion
    else:
        strong_hit = not ordering and not inversion
    return {"gamma": g, "A6_vs_A1_holm_p": float(hp),
            "ordering_significant": ordering,
            "inversion_significant": inversion,
            "full_ordering_A6_A5_A1": bool(full_ordering),
            "gamma_sig_positive": bool(sig_pos),
            "gamma_sig_negative": bool(sig_neg),
            "weak_form_hit": bool(weak_hit),
            "strong_form_hit": bool(strong_hit)}


def main(seeds=20):
    t_all = time.time()
    ret, dropped = load_french_vw()
    print(f"panel: {ret.shape[0]} days x {ret.shape[1]} industries "
          f"(dropped {dropped})", flush=True)
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)

    labs = {}
    counts = {}
    for variant, key in (("announced", "primary_announcement_lagged"),
                         ("calendar", "secondary_calendar")):
        full = label_LNBER(px, variant)
        labs[key] = np.nan_to_num(full[idx].astype(float),
                                  nan=0).astype(int)
        counts[key] = {int(r): int((labs[key] == r).sum())
                       for r in sorted(set(labs[key].tolist()))}
        print(f"L-NBER[{variant}] regime counts: {counts[key]}", flush=True)

    meta = {
        "prereg": "osf_package/PREREG_NBER_FRENCH49.md (osf.io/nsx4e, "
                  "lodged 2026-07-15 22:47 ET)",
        "labeler": "L-NBER: NBER recession state x 50-day trend sign of the "
                   "equal-weight log-price index (trend causal via t-1, "
                   "label_L3 construction); no free threshold",
        "regimes": {"0": "expansion-up", "1": "expansion-down",
                    "2": "recession-up", "3": "recession-down"},
        "primary_variant": "announcement-lagged (causal): recession=1 from "
                           "start-announcement date through end-announcement "
                           "date, both endpoints inclusive",
        "secondary_variant": "calendar recession months (peak month through "
                             "trough month, inclusive); disclosed as "
                             "non-causal robustness",
        "nber_episodes": [
            {"calendar_peak": p, "calendar_trough": t,
             "start_announced": a, "end_announced": e}
            for p, t, a, e in NBER_EPISODES],
        "announcement_dates_verified": {
            "date_verified": "2026-07-15", "source": NBER_SOURCE,
            "note": "all four pairs match the registration's expected "
                    "values exactly"},
        "regime_counts": counts,
        "seeds": seeds, "K": 2, "memory": "hard", "probe": PROBE,
        "min_dormancy": 90, "k_sel": K_SEL, "w_max": W_MAX,
        "cost_bps_overlay": COST_BPS,
    }

    # ---- Gate 1, primary first ----
    gate_out = {"meta": meta}
    for key in ("primary_announcement_lagged", "secondary_calendar"):
        print(f"[gate] {key}", flush=True)
        gate_out[key] = gate50(X, Y, labs[key])
        print(f"  {key}: gap={gate_out[key]['gap_pct']:+.2f}% "
              f"z={gate_out[key]['z_vs_shuffled']:+.2f} "
              f"p={gate_out[key]['p_one_sided']:.4g} "
              f"PASS={gate_out[key]['PASS']}", flush=True)
        with open(RESULTS / "e_french49_nber_gate.json", "w") as fh:
            json.dump(gate_out, fh, indent=1, default=float)

    # ---- Dissociation ----
    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    dis_out = {"meta": meta}
    # PRIMARY first; PN1-PN4 scored against it before the calendar run.
    dis_out["primary_announcement_lagged"] = run_dissoc(
        X, Y, idx, labs["primary_announcement_lagged"], cfg, seeds,
        "NBER-ann")
    prim_wf = dis_out["primary_announcement_lagged"]["walkforward"]
    prim_st = dis_out["primary_announcement_lagged"]["stitched"]
    sr_wf = sign_rule_verdicts(prim_wf)
    sr_st = sign_rule_verdicts(prim_st)
    scoring = {
        "scored_against": "PRIMARY (announcement-lagged) variant; "
                          "walk-forward is the headline cell, stitched is "
                          "the schedule-resampling secondary; gross is the "
                          "registered battery, net-25bps the lodged overlay",
        "PN1_H_SIGN": {
            "registered": "the sign of Γ̂ under L-NBER predicts the "
                          "dissociation outcome direction (ordering iff Γ̂ "
                          "significantly positive); weak and strong forms "
                          "both reported per addendum F",
            "walkforward": sr_wf, "stitched": sr_st,
            "refutation_clause": "Γ̂ significantly positive with no "
                                 "ordering/inversion, or Γ̂ ≈ 0 with a "
                                 "significant ordering, under the primary "
                                 "variant",
        },
        "PN2_gamma_positive": {
            "registered": "Γ̂ > 0 under L-NBER (~45%)",
            "walkforward": prim_wf["gate2_forgetting_deficit"],
            "stitched": prim_st["gate2_forgetting_deficit"],
        },
        "PN3_fragility_discriminator": {
            "registered": "positive deficit under L-NBER (no threshold) -> "
                          "granularity/window reading of L3 fragility; "
                          "null -> artifact reading gains, said at headline "
                          "prominence",
            "branch": ("granularity/window"
                       if prim_wf["gate2_forgetting_deficit"]
                       ["positive_significant"] else "artifact"),
        },
        "PN4": "all outcomes reported; one labeler, two causality variants, "
               "family-wise accounting disclosed; no selective emphasis",
    }
    dis_out["scoring_PN1_PN4"] = scoring
    with open(RESULTS / "e_french49_nber_dissoc.json", "w") as fh:
        json.dump(dis_out, fh, indent=1, default=float)
    print(f"[scoring] PN1 weak wf={sr_wf['weak_form_hit']} "
          f"strong wf={sr_wf['strong_form_hit']} | "
          f"PN2 sig+={scoring['PN2_gamma_positive']['walkforward']['positive_significant']} | "
          f"PN3 branch={scoring['PN3_fragility_discriminator']['branch']}",
          flush=True)

    # SECONDARY (calendar) robustness, run after scoring.
    dis_out["secondary_calendar"] = run_dissoc(
        X, Y, idx, labs["secondary_calendar"], cfg, seeds, "NBER-cal")
    dis_out["scoring_PN1_PN4"]["secondary_calendar_sign_rule"] = {
        "walkforward": sign_rule_verdicts(
            dis_out["secondary_calendar"]["walkforward"]),
        "stitched": sign_rule_verdicts(
            dis_out["secondary_calendar"]["stitched"]),
        "note": "robustness only; PN1-PN4 were scored against the primary "
                "variant before this ran"}
    with open(RESULTS / "e_french49_nber_dissoc.json", "w") as fh:
        json.dump(dis_out, fh, indent=1, default=float)
    print(f"NBER BATTERY COMPLETE in {(time.time()-t_all)/60:.1f} min",
          flush=True)


if __name__ == "__main__":
    main()
