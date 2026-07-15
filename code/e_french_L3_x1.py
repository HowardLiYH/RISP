"""E-X1 / E-X3 / X6 mechanism probes on the French-49 L3 threshold family.

Pre-registered as E-X1 and E-X3 in PRE-REGISTRATION E of ../PREREG_FRENCH49.md
(written 2026-07-15 BEFORE these runs). X6 = the cell-vs-union Gamma split
(crisis-up / crisis-down / calm cells), riding on the same runs; its red flag
(Gamma carried by calm-cell reactivations) was registered in the session's
experiment-inventor design before execution.

Runs: dd_thresh in {10,12,15,20%}, arms A1-monolith-erm and A9-oracle-pinned
only, 20 seeds, seeding 1311*s+17 exactly as e_french_L3.py (so the 15% cell
is bit-identical to the registered battery), collect_react=True.

CREATED AS A NEW FILE ONLY -- risp.py / e_french*.py / run_experiments.py are
untouched. Analysis choices (event bins, regression spec, fit form, bootstrap
scheme) are fixed in this file before its first execution; no tuning.

Outputs:
  ../results/e_french49_L3_x1.json
  ../paper/figures/figX1_rehearsal.pdf
  ../paper/figures/figX3_halflife.pdf
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
from e_french import (load_french_vw, build_xy_returns, price_panel,
                      K_SEL, W_MAX, RESULTS)
from e_french_L3 import label_L3

FIG = Path(__file__).resolve().parents[1] / "paper" / "figures"
CACHE = Path("/private/tmp/claude-501/-Users-yuhaoli-Desktop-Summer-2026/"
             "8373d741-6b75-408c-ae77-32426f72fcfa/scratchpad")
CACHE.mkdir(parents=True, exist_ok=True)

THRESHES = (0.10, 0.12, 0.15, 0.20)
SEEDS = 20
MIN_DORM = 90
ARM_A, ARM_B = "A1-monolith-erm", "A9-oracle-pinned"
CELL_NAMES = {0: "calm-up", 1: "calm-down", 2: "crisis-up", 3: "crisis-down"}

# calendar crisis-event bins (fixed in advance; evaluation half starts ~2008)
EVENT_BINS = [
    ("2008-GFC",    "2007-07-01", "2009-12-31"),
    ("2010",        "2010-01-01", "2010-12-31"),
    ("2011-12-euro", "2011-01-01", "2012-12-31"),
    ("2015-16",     "2015-01-01", "2016-12-31"),
    ("2018-19",     "2018-01-01", "2019-12-31"),
    ("2020-covid",  "2020-01-01", "2021-12-31"),
    ("2022-23",     "2022-01-01", "2023-12-31"),
    ("2024-25",     "2024-01-01", "2025-12-31"),
]


def map_event(ts):
    import pandas as pd
    for name, lo, hi in EVENT_BINS:
        if pd.Timestamp(lo) <= ts <= pd.Timestamp(hi):
            return name
    return f"other-{ts.year}"


# ---------------------------------------------------------------- covariates

def react_covariates(lab, sched, t_starts, dates):
    """Per reactivation: cell dormancy, union dormancy, rehearsal count/days.

    union = {2,3} (crisis) for crisis-cell reactivations, {0,1} for calm.
    Rehearsal = union activity strictly inside the cell's dormancy interval
    (the cell itself is absent there by construction)."""
    rows = []
    for t0 in t_starts:
        r = int(lab[t0])
        d_cell = int(sched.dormancy[t0])
        union = (2, 3) if r >= 2 else (0, 1)
        in_union = np.isin(lab[:t0], union)
        d_union = int(t0 - np.nonzero(in_union)[0].max())  # cell itself in union
        seg = lab[t0 - d_cell + 1:t0]                      # open dormancy interval
        seg_u = np.isin(seg, union).astype(int)
        reh_days = int(seg_u.sum())
        reh_count = int(((np.diff(np.concatenate([[0], seg_u])) == 1)).sum())
        rows.append({
            "t0": int(t0), "date": str(dates[t0].date()), "cell": r,
            "cell_name": CELL_NAMES[r], "event": map_event(dates[t0]),
            "D_cell": d_cell, "D_union": d_union,
            "R": reh_count, "rehearsal_days": reh_days,
        })
    return rows


# ---------------------------------------------------------------- statistics

def ols_cluster(y, Xmat, clusters, names):
    """OLS with CR1 cluster-robust SEs; p from t(G-1)."""
    from scipy import stats
    y = np.asarray(y, float)
    Xmat = np.asarray(Xmat, float)
    n, k = Xmat.shape
    XtX_inv = np.linalg.pinv(Xmat.T @ Xmat)
    beta = XtX_inv @ Xmat.T @ y
    u = y - Xmat @ beta
    labs = np.unique(clusters)
    G = len(labs)
    meat = np.zeros((k, k))
    for g in labs:
        m = clusters == g
        s = Xmat[m].T @ u[m]
        meat += np.outer(s, s)
    corr = (G / max(G - 1, 1)) * ((n - 1) / max(n - k, 1))
    V = corr * XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(V), 0))
    tv = np.where(se > 0, beta / se, np.nan)
    dof = max(G - 1, 1)
    p = 2 * stats.t.sf(np.abs(tv), dof)
    return {"names": names, "beta": beta.tolist(), "se": se.tolist(),
            "t": tv.tolist(), "p": p.tolist(), "n": int(n),
            "n_clusters": int(G), "dof": int(dof),
            "r2": float(1 - u.var() / y.var()) if y.var() > 0 else float("nan")}


def ols_classical(y, Xmat, names):
    from scipy import stats
    y = np.asarray(y, float)
    Xmat = np.asarray(Xmat, float)
    n, k = Xmat.shape
    XtX_inv = np.linalg.pinv(Xmat.T @ Xmat)
    beta = XtX_inv @ Xmat.T @ y
    u = y - Xmat @ beta
    dof = max(n - k, 1)
    s2 = float(u @ u) / dof
    se = np.sqrt(np.maximum(np.diag(s2 * XtX_inv), 0))
    tv = np.where(se > 0, beta / se, np.nan)
    p = 2 * stats.t.sf(np.abs(tv), dof)
    return {"names": names, "beta": beta.tolist(), "se": se.tolist(),
            "t": tv.tolist(), "p": p.tolist(), "n": int(n), "dof": int(dof),
            "r2": float(1 - u.var() / y.var()) if y.var() > 0 else float("nan")}


def spearman(x, y):
    from scipy import stats
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return {"rho": float("nan"), "p": float("nan"), "n": int(len(x))}
    rho, p = stats.spearmanr(x, y)
    return {"rho": float(rho), "p": float(p), "n": int(len(x))}


# ---------------------------------------------------------------- X3 fitting

def fit_exp(profile):
    """Fit g(j) = A * exp(-ln2 * j / tau) + C. Returns dict or None."""
    from scipy.optimize import curve_fit
    j = np.arange(len(profile), dtype=float)
    g = np.asarray(profile, float)
    ok = np.isfinite(g)
    j, g = j[ok], g[ok]
    if len(g) < 5:
        return None

    def f(x, A, tau, C):
        return A * np.exp(-np.log(2.0) * x / tau) + C
    try:
        A0 = g[0] - g[-3:].mean()
        p0 = [A0 if abs(A0) > 1e-12 else 1e-5, 3.0, g[-3:].mean()]
        popt, _ = curve_fit(f, j, g, p0=p0, maxfev=20000,
                            bounds=([-np.inf, 0.2, -np.inf],
                                    [np.inf, 300.0, np.inf]))
        resid = g - f(j, *popt)
        ss_tot = ((g - g.mean()) ** 2).sum()
        r2 = float(1 - (resid ** 2).sum() / ss_tot) if ss_tot > 0 else float("nan")
        return {"A": float(popt[0]), "tau_half": float(popt[1]),
                "C": float(popt[2]), "r2": r2,
                "censored_at_bound": bool(popt[1] >= 299.0)}
    except Exception:
        return None


def tau_bootstrap(G_seed, n_boot=2000, seed=20260715):
    """Percentile CI for tau via resampling seeds. G_seed: (S, probe)."""
    rng = np.random.default_rng(seed)
    S = G_seed.shape[0]
    taus, n_ok, n_decay = [], 0, 0
    for _ in range(n_boot):
        pick = rng.integers(0, S, S)
        fit = fit_exp(np.nanmean(G_seed[pick], axis=0))
        if fit is not None:
            n_ok += 1
            if fit["A"] > 0 and not fit["censored_at_bound"]:
                taus.append(fit["tau_half"])
                n_decay += 1
    out = {"n_boot": n_boot, "fit_success_frac": n_ok / n_boot,
           "decaying_fit_frac": n_decay / n_boot}
    if len(taus) >= 20:
        out["tau_ci95"] = [float(np.percentile(taus, 2.5)),
                           float(np.percentile(taus, 97.5))]
        out["tau_median_boot"] = float(np.median(taus))
    else:
        out["tau_ci95"] = None
        out["tau_median_boot"] = None
    return out


# ---------------------------------------------------------------- run layer

def run_threshold(thresh, X, Y, px, idx, dates, cfg):
    """20 seeds x {A1, A9}; returns covariates + per-seed matrices."""
    tag = f"x1_{int(round(thresh * 100))}pct"
    cache_f = CACHE / f"{tag}.npz"
    lab = np.nan_to_num(label_L3(px, dd_thresh=thresh)[idx], nan=0).astype(int)
    mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
    sched = mkt.schedule()
    T = sched.T
    half = int(T * 0.5)

    if cache_f.exists():
        z = np.load(cache_f)
        stored = {k: z[k] for k in z.files}
        print(f"[{tag}] loaded cache", flush=True)
    else:
        t0c = time.time()
        A1p, A9p = [], []      # per-seed per-reactivation probe means
        A1o, A9o = [], []      # per-seed aggregate post_react
        Gall, Gcri = [], []    # per-seed gap profiles (all / crisis cells)
        t_starts = None
        for s in range(SEEDS):
            daily = {}
            for aname, sink_p, sink_o in ((ARM_A, A1p, A1o),
                                          (ARM_B, A9p, A9o)):
                arm = ARM_FACTORIES[aname](cfg, np.random.default_rng(
                    1311 * s + 17), 2, "hard")
                m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                            min_dormancy=MIN_DORM, collect_react=True)
                det = m["react_detail"]
                if t_starts is None:
                    t_starts = [d["t_start"] for d in det]
                assert [d["t_start"] for d in det] == t_starts
                sink_p.append([d["mean_probe_regret"] for d in det])
                sink_o.append(m["post_react"])
                daily[aname] = m["daily"]
            # X3: per-seed gap profile, aligned at t0, full-eval windows only
            gap = daily[ARM_A] - daily[ARM_B]
            prof_a = np.full((len(t_starts), PROBE), np.nan)
            for i, tt in enumerate(t_starts):
                if tt < half:
                    continue                     # partial window: exclude
                hi = min(tt + PROBE, T)
                prof_a[i, :hi - tt] = gap[tt:hi]
            cri = np.array([lab[tt] >= 2 for tt in t_starts])
            with np.errstate(invalid="ignore"):
                Gall.append(np.nanmean(prof_a, axis=0))
                Gcri.append(np.nanmean(prof_a[cri], axis=0)
                            if cri.any() else np.full(PROBE, np.nan))
            if s == 0:
                print(f"[{tag}] seed0 {time.time() - t0c:.0f}s "
                      f"n_react_detail={len(t_starts)}", flush=True)
        stored = {"A1p": np.array(A1p), "A9p": np.array(A9p),
                  "A1o": np.array(A1o), "A9o": np.array(A9o),
                  "Gall": np.array(Gall), "Gcri": np.array(Gcri),
                  "t_starts": np.array(t_starts)}
        np.savez_compressed(cache_f, **stored)
        print(f"[{tag}] done in {(time.time() - t0c) / 60:.1f} min", flush=True)

    t_starts = stored["t_starts"].astype(int).tolist()
    cov = react_covariates(lab, sched, t_starts, dates)
    # n_days / regime straight from schedule (matches run_arm's clipping)
    for c in cov:
        lo, hi = max(c["t0"], half), min(c["t0"] + PROBE, T)
        c["n_days"] = int(hi - lo)
        c["full_window"] = bool(c["t0"] >= half)
    gamma_i = stored["A1p"].mean(axis=0) - stored["A9p"].mean(axis=0)
    for c, g, a1, a9 in zip(cov, gamma_i, stored["A1p"].mean(axis=0),
                            stored["A9p"].mean(axis=0)):
        c["gamma_i"] = float(g)
        c["a1_mean"] = float(a1)
        c["a9_mean"] = float(a9)
    d_agg = stored["A1o"] - stored["A9o"]
    gamma_agg = {"mean": float(d_agg.mean()),
                 "ci95": float(1.96 * d_agg.std(ddof=1) / np.sqrt(len(d_agg))),
                 "n_seeds": int(len(d_agg))}
    # probe-overlap dilution diagnostic (E-X1 dormancy-branch check)
    windows = [(max(c["t0"], half), min(c["t0"] + PROBE, T)) for c in cov]
    total = sum(hi - lo for lo, hi in windows)
    uniq = len(set(t for lo, hi in windows for t in range(lo, hi)))
    overlap = {"window_days_total": int(total), "unique_probe_days": int(uniq),
               "overlap_frac": float(1 - uniq / total) if total else None,
               "median_n_days": float(np.median([c["n_days"] for c in cov]))}
    return {"lab": lab, "cov": cov, "stored": stored, "gamma_agg": gamma_agg,
            "overlap": overlap, "T": int(T), "half": int(half)}


# ---------------------------------------------------------------- analysis

def analyse(per_th):
    from itertools import chain
    rows = list(chain.from_iterable(
        [dict(c, thresh=th) for c in per_th[th]["cov"]] for th in per_th))
    out = {}

    # ---- X1 pooled regression: Gamma_i ~ thresh FE + logDcell + logDunion + R
    def build(rows_sel):
        ths = sorted({r["thresh"] for r in rows_sel})
        names = [f"FE_{int(round(t * 100))}pct" for t in ths] + \
                ["log_D_cell", "log_D_union", "R"]
        Xm = np.zeros((len(rows_sel), len(ths) + 3))
        for i, r in enumerate(rows_sel):
            Xm[i, ths.index(r["thresh"])] = 1.0
            Xm[i, len(ths)] = np.log(r["D_cell"])
            Xm[i, len(ths) + 1] = np.log(r["D_union"])
            Xm[i, len(ths) + 2] = r["R"]
        y = np.array([r["gamma_i"] for r in rows_sel])
        cl = np.array([r["event"] for r in rows_sel])
        return y, Xm, cl, names

    def add_std(reg, rows_sel):
        """Standardized slopes (x in SD units) for dominance comparison."""
        sds = {"log_D_cell": np.std([np.log(r["D_cell"]) for r in rows_sel]),
               "log_D_union": np.std([np.log(r["D_union"]) for r in rows_sel]),
               "R": np.std([float(r["R"]) for r in rows_sel])}
        reg["beta_std"] = {k: reg["beta"][reg["names"].index(k)] * sds[k]
                           for k in sds}
        return reg

    y, Xm, cl, names = build(rows)
    out["pooled_all_cells"] = add_std(ols_cluster(y, Xm, cl, names), rows)
    rows_cri = [r for r in rows if r["cell"] >= 2]
    y, Xm, cl, names = build(rows_cri)
    out["pooled_crisis_cells"] = add_std(ols_cluster(y, Xm, cl, names),
                                         rows_cri)

    # ---- Spearman backstops (pooled and per threshold)
    def sp_block(rows_sel):
        g = [r["gamma_i"] for r in rows_sel]
        return {"vs_log_D_cell": spearman([np.log(r["D_cell"])
                                           for r in rows_sel], g),
                "vs_log_D_union": spearman([np.log(r["D_union"])
                                            for r in rows_sel], g),
                "vs_R": spearman([r["R"] for r in rows_sel], g),
                "vs_rehearsal_days": spearman([r["rehearsal_days"]
                                               for r in rows_sel], g)}
    out["spearman_pooled_all"] = sp_block(rows)
    out["spearman_pooled_crisis"] = sp_block(rows_cri)
    out["spearman_per_threshold"] = {
        f"{int(round(th * 100))}pct": sp_block(
            [r for r in rows if r["thresh"] == th]) for th in per_th}

    # ---- within-event contrast: Gamma_(event,thresh) on R, event FE
    def within_event(rows_sel):
        cells = {}
        for r in rows_sel:
            cells.setdefault((r["event"], r["thresh"]), []).append(r)
        ev_rows = [{"event": e, "thresh": t,
                    "gamma": float(np.mean([q["gamma_i"] for q in grp])),
                    "R": float(np.mean([q["R"] for q in grp])),
                    "n_react": len(grp)}
                   for (e, t), grp in sorted(cells.items())]
        events = sorted({r["event"] for r in ev_rows})
        multi = [e for e in events
                 if sum(1 for r in ev_rows if r["event"] == e) >= 2]
        ev_use = [r for r in ev_rows if r["event"] in multi]
        if len(ev_use) <= len(multi) + 1:
            return {"cells": ev_rows,
                    "note": "too few multi-threshold events"}
        Xm = np.zeros((len(ev_use), len(multi) + 1))
        for i, r in enumerate(ev_use):
            Xm[i, multi.index(r["event"])] = 1.0
            Xm[i, -1] = r["R"]
        y = np.array([r["gamma"] for r in ev_use])
        reg = ols_classical(y, Xm, [f"FE_{e}" for e in multi] + ["R"])
        # within-event Spearman on demeaned values
        gd, rd = [], []
        for e in multi:
            grp = [r for r in ev_use if r["event"] == e]
            gm = np.mean([r["gamma"] for r in grp])
            rm = np.mean([r["R"] for r in grp])
            gd += [r["gamma"] - gm for r in grp]
            rd += [r["R"] - rm for r in grp]
        return {"cells": ev_rows, "events_used": multi,
                "n_cells_used": len(ev_use), "ols_event_FE": reg,
                "spearman_demeaned": spearman(rd, gd)}
    out["within_event"] = within_event(rows)
    out["within_event_crisis_only"] = within_event(rows_cri)

    # ---- X6: Gamma split by regime cell
    x6 = {}
    for th in per_th:
        key = f"{int(round(th * 100))}pct"
        sub = [r for r in rows if r["thresh"] == th]
        tot_wsum = sum(r["gamma_i"] * r["n_days"] for r in sub)
        cell_out = {}
        for grp_name, members in (("crisis-up", (2,)), ("crisis-down", (3,)),
                                  ("calm", (0, 1))):
            g = [r for r in sub if r["cell"] in members]
            if not g:
                cell_out[grp_name] = {"n_react": 0}
                continue
            wsum = sum(r["gamma_i"] * r["n_days"] for r in g)
            cell_out[grp_name] = {
                "n_react": len(g),
                "mean_gamma_i": float(np.mean([r["gamma_i"] for r in g])),
                "day_weighted_sum": float(wsum),
                "share_of_day_weighted_total":
                    float(wsum / tot_wsum) if tot_wsum != 0 else None}
        calm_share = cell_out.get("calm", {}).get(
            "share_of_day_weighted_total")
        x6[key] = {"cells": cell_out,
                   "day_weighted_gamma_total": float(tot_wsum),
                   "red_flag_calm_carried": bool(
                       tot_wsum > 0 and calm_share is not None
                       and calm_share > 0.5)}
    out["X6_cell_split"] = x6
    return out, rows


def analyse_x3(per_th):
    out = {}
    for th, d in per_th.items():
        key = f"{int(round(th * 100))}pct"
        block = {}
        for name, mat_key in (("all_cells", "Gall"), ("crisis_cells", "Gcri")):
            G = d["stored"][mat_key]
            prof = np.nanmean(G, axis=0)
            fit = fit_exp(prof)
            boot = tau_bootstrap(G)
            block[name] = {"gap_profile": prof.tolist(),
                           "n_seeds": int(G.shape[0]),
                           "exp_fit": fit, "bootstrap": boot}
        block["n_full_windows_all"] = int(
            sum(1 for c in d["cov"] if c["full_window"]))
        block["n_full_windows_crisis"] = int(
            sum(1 for c in d["cov"] if c["full_window"] and c["cell"] >= 2))
        out[key] = block
    return out


# ---------------------------------------------------------------- verdicts

def verdicts(x1, x3, per_th):
    v = {}
    reg = x1["pooled_all_cells"]
    b = dict(zip(reg["names"], reg["beta"]))
    p = dict(zip(reg["names"], reg["p"]))
    bs = reg["beta_std"]
    sig = {k: p[k] < 0.05 for k in ("log_D_cell", "log_D_union", "R")}
    rehearsal = (b["R"] < 0 and sig["R"]
                 and abs(bs["log_D_union"]) > abs(bs["log_D_cell"]))
    dormancy = (sig["log_D_cell"] and b["log_D_cell"] > 0
                and abs(bs["log_D_cell"]) > abs(bs["log_D_union"])
                and not sig["R"])
    if rehearsal:
        v["E-X1"] = ("REHEARSAL branch (~40% prior): Gamma_i decreasing in R "
                     "and union-dormancy dominates -> E1f attribution revised "
                     "toward rehearsal; threshold fragility becomes mechanism.")
    elif dormancy:
        v["E-X1"] = ("DORMANCY branch (~40% prior): cell-dormancy dominates, "
                     "R ~ 0 -> isolation story stands; 10/12% nulls need the "
                     "probe-overlap check (reported).")
    else:
        v["E-X1"] = ("NEITHER branch (~20% prior): Gamma not cleanly "
                     "localized in identifiable reactivation covariates -> "
                     "artifact warning at headline prominence, as registered.")
    v["E-X1_slopes"] = {k: {"beta": b[k], "p": p[k], "beta_std": bs[k]}
                        for k in ("log_D_cell", "log_D_union", "R")}

    taus = {}
    for key, blk in x3.items():
        fit = blk["all_cells"]["exp_fit"]
        taus[key] = (fit["tau_half"] if fit and fit["A"] > 0 else None)
    t15 = taus.get("15pct")
    t10, t12 = taus.get("10pct"), taus.get("12pct")
    pred = (t15 is not None and t15 >= 10
            and all(t is not None and t <= 5 for t in (t10, t12)))
    flatish = all(
        (x3[k]["all_cells"]["exp_fit"] is None
         or x3[k]["all_cells"]["exp_fit"]["A"] <= 0
         or x3[k]["all_cells"]["exp_fit"]["r2"] < 0.2) for k in x3)
    if pred:
        v["E-X3"] = ("PREDICTED branch (~55% prior): tau(15%) ~ probe window "
                     "while tau(10/12%) <= 5d -- the E6 crossover on real data.")
    elif flatish:
        v["E-X3"] = ("ANTI-BRANCH: profiles flat/parallel -> the deficit is a "
                     "level offset, not a reactivation transient; the "
                     "'forgetting' label is wrong (candidate rename: "
                     "allocation deficit). Reported plainly, as registered.")
    else:
        v["E-X3"] = ("MIXED: neither the tau(theta) crossover pattern nor "
                     "flat profiles; see tau table -- reported without "
                     "adjudication.")
    v["E-X3_tau"] = taus

    flags = {k: blk["red_flag_calm_carried"]
             for k, blk in x1["X6_cell_split"].items()}
    v["X6"] = ("RED FLAG at " + ", ".join(k for k, f in flags.items() if f)
               + ": positive Gamma day-weighted mass carried by calm-cell "
               "reactivations." if any(flags.values())
               else "No red flag: no threshold has positive Gamma carried "
                    "majority by calm-cell reactivations.")
    return v


# ---------------------------------------------------------------- figures

def figures(rows, x3, per_th):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10,
                         "axes.labelsize": 9, "figure.dpi": 150,
                         "axes.spines.top": False,
                         "axes.spines.right": False})
    # categorical palette validated for CVD (blue/orange/green/purple);
    # marker shape = secondary encoding for the low-contrast orange
    PAL = {0.10: ("#5A82C8", "o"), 0.12: ("#E28C3C", "s"),
           0.15: ("#3C915A", "^"), 0.20: ("#7A55B0", "D")}
    rng = np.random.default_rng(7)

    # ---- figX1: Gamma_i vs rehearsal count
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ax.axhline(0, color="#999999", lw=0.8, zorder=0)
    for th in THRESHES:
        col, mk = PAL[th]
        sub = [r for r in rows if r["thresh"] == th]
        for crisis in (True, False):
            g = [r for r in sub if (r["cell"] >= 2) == crisis]
            if not g:
                continue
            xs = np.array([r["R"] for r in g], float) \
                + rng.uniform(-0.15, 0.15, len(g))
            ys = [r["gamma_i"] for r in g]
            ax.scatter(xs, ys, s=26, marker=mk,
                       facecolors=col if crisis else "none",
                       edgecolors=col, linewidths=1.0, alpha=0.85,
                       label=(f"dd>{int(round(th * 100))}%"
                              if crisis else None))
    ax.set_xlabel("rehearsal count $R_i$ (union episodes during cell dormancy)")
    ax.set_ylabel(r"$\Gamma_i$ = A1$-$A9 probe regret (matched)")
    ax.set_title("E-X1: per-reactivation deficit vs rehearsal count\n"
                 "(filled = crisis-cell reactivations, open = calm-cell)",
                 fontsize=9)
    ax.legend(frameon=False, fontsize=8, title="threshold", title_fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "figX1_rehearsal.pdf")
    plt.close(fig)

    # ---- figX3: gap profiles + exponential fits, small multiples
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 4.6), sharex=True)
    for ax, th in zip(axes.ravel(), THRESHES):
        key = f"{int(round(th * 100))}pct"
        col, _ = PAL[th]
        blk = x3[key]["all_cells"]
        prof = np.array(blk["gap_profile"])
        G = per_th[th]["stored"]["Gall"]
        lo = np.nanpercentile(G, 2.5, axis=0)
        hi = np.nanpercentile(G, 97.5, axis=0)
        j = np.arange(len(prof))
        ax.axhline(0, color="#999999", lw=0.8, zorder=0)
        ax.fill_between(j, lo, hi, color=col, alpha=0.15, lw=0)
        ax.plot(j, prof, color=col, lw=2, marker="o", ms=3)
        fit = blk["exp_fit"]
        if fit is not None:
            jj = np.linspace(0, len(prof) - 1, 100)
            ax.plot(jj, fit["A"] * np.exp(-np.log(2) * jj / fit["tau_half"])
                    + fit["C"], color="#444444", lw=1.2, ls="--")
            ci = blk["bootstrap"]["tau_ci95"]
            ci_s = (f" [{ci[0]:.1f}, {ci[1]:.1f}]" if ci else "")
            ax.set_title(f"dd>{int(round(th * 100))}%:  "
                         rf"$\tau_{{1/2}}$={fit['tau_half']:.1f}d{ci_s}"
                         f"  $R^2$={fit['r2']:.2f}", fontsize=8)
        else:
            ax.set_title(f"dd>{int(round(th * 100))}%: no exponential fit",
                         fontsize=9)
    for ax in axes[1]:
        ax.set_xlabel("probe day $j$ after reactivation")
    for ax in axes[:, 0]:
        ax.set_ylabel(r"A1$-$A9 daily regret gap")
    fig.suptitle("E-X3: reactivation gap profile, exponential fit\n"
                 "(seed mean; band = 2.5/97.5% across 20 seeds)", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(FIG / "figX3_halflife.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- main

def main():
    t_all = time.time()
    ret, dropped = load_french_vw()
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    dates = ret.index[idx]
    print(f"panel {X.shape} dropped={dropped}", flush=True)

    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    per_th = {}
    for th in THRESHES:
        per_th[th] = run_threshold(th, X, Y, px, idx, dates, Cfg())
        g = per_th[th]["gamma_agg"]
        print(f"[{int(round(th * 100))}%] n_react_detail="
              f"{len(per_th[th]['cov'])} agg Gamma={g['mean']:+.5f}"
              f"±{g['ci95']:.5f} overlap={per_th[th]['overlap']}", flush=True)

    x1, rows = analyse(per_th)
    x3 = analyse_x3(per_th)
    v = verdicts(x1, x3, per_th)
    figures(rows, x3, per_th)

    out = {
        "config": {
            "thresholds": list(THRESHES), "seeds": SEEDS,
            "seed_formula": "1311*s+17 (as e_french_L3.py; 15pct cell "
                            "bit-identical to the registered battery)",
            "arms": [ARM_A, ARM_B], "probe": PROBE, "min_dormancy": MIN_DORM,
            "K": 2, "memory": "hard", "k_sel": K_SEL, "w_max": W_MAX,
            "event_bins": EVENT_BINS,
            "notes": [
                "Gamma_i = mean over 20 seeds of A1 probe-window regret minus "
                "mean over seeds of A9, matched per reactivation on the "
                "shared deterministic walk-forward schedule.",
                "Union = {crisis-up, crisis-down} for crisis-cell "
                "reactivations, {calm-up, calm-down} for calm-cell ones; "
                "rehearsal = union activity strictly inside the cell's "
                "dormancy interval.",
                "X3 profiles use only reactivations whose full probe window "
                "lies in the evaluated second half; Gamma_i additionally "
                "includes windows clipped at the halfway boundary, exactly "
                "as the registered aggregate post_react does.",
                "Small-n caveat: n per threshold is the handful of >=90d "
                "reactivations on ONE market history; cluster count for "
                "robust SEs is the number of calendar events. No spec was "
                "tuned; all analysis choices were fixed in this file before "
                "its first execution.",
            ]},
        "per_threshold": {
            f"{int(round(th * 100))}pct": {
                "n_react_detail": len(per_th[th]["cov"]),
                "gamma_agg_seedCI": per_th[th]["gamma_agg"],
                "overlap_diagnostic": per_th[th]["overlap"],
                "T": per_th[th]["T"], "half": per_th[th]["half"],
                "reactivations": per_th[th]["cov"],
            } for th in THRESHES},
        "X1": x1, "X3": x3, "verdicts": v,
    }
    with open(RESULTS / "e_french49_L3_x1.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(json.dumps(v, indent=1))
    print(f"X1/X3/X6 COMPLETE in {(time.time() - t_all) / 60:.1f} min",
          flush=True)


if __name__ == "__main__":
    main()
