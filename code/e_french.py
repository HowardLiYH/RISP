"""
French 49-industry battery: two gates + ten-arm dissociation.

Design and predictions pre-registered in ../PREREG_FRENCH49.md BEFORE this
script was first run. Protocol mirrors the paper's E0/E1s/E1r exactly;
differences fixed in advance: 50 shuffle controls from the start (no
screen/confirm two-step), two-cell labeler family only, k=5/w_max=0.2 for
the ~49-asset cross-section, primary window 1990-2025.

Outputs: ../results/e_french49_gate.json, ../results/e_french49_dissoc.json
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import ARM_FACTORIES, run_arm, welch, holm, regret
from run_experiments import summarize, block_shuffle, PROBE
from realdata import (label_L1, label_L2, standardize, BlockLibrary,
                      StitchedMarket, RealMarket)

RESULTS = Path(__file__).resolve().parent / ".." / "results"
CSV = (Path(__file__).resolve().parent / ".." / "data" / "french"
       / "49_Industry_Portfolios_Daily.csv")

K_SEL, W_MAX = 5, 0.2          # top-k of ~49, budget-feasible
WINDOW = ("1990-01-01", "2025-12-31")
N_SHUFFLE = 50

ARMS = ["A1-monolith-erm", "A2-router", "A3-recentperf", "A4-randomfixed",
        "A5-risp-erm", "A6-risp-inv", "A7-monolith-inv",
        "A8a-hedge-fixed", "A8b-hedge-learn", "A9-oracle-pinned"]
PAIRS = [("A6-risp-inv", "A5-risp-erm"),
         ("A6-risp-inv", "A1-monolith-erm"),
         ("A5-risp-erm", "A2-router"),
         ("A5-risp-erm", "A1-monolith-erm"),
         ("A6-risp-inv", "A8b-hedge-learn"),
         ("A6-risp-inv", "A9-oracle-pinned")]


def load_french_vw():
    """Value-weighted daily panel of RETURNS (decimal), 1990-2025."""
    lines = CSV.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(",Agric"))
    end = next(i for i in range(start + 1, len(lines))
               if not lines[i][:8].strip().isdigit())
    import io
    df = pd.read_csv(io.StringIO("\n".join([lines[start]] +
                                           lines[start + 1:end])))
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date").loc[WINDOW[0]:WINDOW[1]]
    df = df.replace([-99.99, -999.0], np.nan) / 100.0
    dropped = [c for c in df.columns if df[c].isna().any()]
    df = df.drop(columns=dropped)
    return df, dropped


def build_xy_returns(ret: pd.DataFrame):
    """8 causal features from returns only (see PREREG); y = day-t return."""
    lp = np.log1p(ret).cumsum()
    r1 = lp.diff()
    mom20 = lp.shift(1) - lp.shift(21)
    feats = {
        "mom5": lp.shift(1) - lp.shift(6),
        "mom20": mom20,
        "mom100": lp.shift(1) - lp.shift(101),
        "rev1": -r1.shift(1),
        "vol20": r1.rolling(20).std().shift(1),
        "magap50": lp.shift(1) - lp.rolling(50).mean().shift(1),
        "xsrank20": mom20.rank(axis=1, pct=True) * 2 - 1,
    }
    y = r1
    Xs, ys, index = [], [], []
    for t in range(len(ret)):
        ok = all(np.isfinite(v.iloc[t]).all() for v in feats.values()) \
            and np.isfinite(y.iloc[t]).all()
        if not ok:
            continue
        F = np.column_stack(
            [standardize(v.iloc[t].values) for v in feats.values()]
            + [np.ones(ret.shape[1])])
        Xs.append(F)
        ys.append(y.iloc[t].values)
        index.append(t)
    return np.array(Xs), np.array(ys), np.array(index)


def price_panel(ret):
    return np.exp(np.log1p(ret).cumsum())


def regret_series(X, Y, labels, refit=60, lam=10.0):
    T, n, d = len(X), X.shape[1], X.shape[2]
    split = T // 2
    regs = np.zeros(T - split)
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
    return regs


def gate50(X, Y, lab):
    from scipy import stats
    lab = np.nan_to_num(lab, nan=0).astype(int)
    rng = np.random.default_rng(42)
    t0 = time.time()
    real = regret_series(X, Y, lab)
    sh = np.array([regret_series(X, Y, block_shuffle(lab, rng))
                   for _ in range(N_SHUFFLE)])
    pooled = regret_series(X, Y, np.zeros(len(X), dtype=int))
    sh_means = sh.mean(axis=1)
    z = (sh_means.mean() - real.mean()) / (sh_means.std() + 1e-12)
    t_stat, p_two = stats.ttest_1samp(sh_means, real.mean())
    p_one = p_two / 2 if sh_means.mean() > real.mean() else 1 - p_two / 2
    half = len(real) // 2
    halves = {}
    for name, sl in (("first_half", slice(0, half)),
                     ("second_half", slice(half, None))):
        rh, shh = real[sl].mean(), sh[:, sl].mean(axis=1)
        halves[name] = {"gap_pct": float(100 * (shh.mean() - rh)
                                         / (shh.mean() + 1e-12)),
                        "z": float((shh.mean() - rh) / (shh.std() + 1e-12))}
    passed = bool(z > 2 and p_one < 0.005
                  and pooled.mean() > real.mean()
                  and halves["first_half"]["gap_pct"] > 0
                  and halves["second_half"]["gap_pct"] > 0)
    print(f"    gate done in {(time.time()-t0)/60:.1f} min", flush=True)
    return {"real_mean_regret": float(real.mean()),
            "shuffled_mean_regret": float(sh_means.mean()),
            "pooled_mean_regret": float(pooled.mean()),
            "gap_pct": float(100 * (sh_means.mean() - real.mean())
                             / (sh_means.mean() + 1e-12)),
            "cond_vs_pooled_pct": float(100 * (pooled.mean() - real.mean())
                                        / (pooled.mean() + 1e-12)),
            "z_vs_shuffled": float(z), "p_one_sided": float(p_one),
            "n_shuffle": N_SHUFFLE, "split_half": halves,
            "regime_counts": {int(r): int((lab == r).sum())
                              for r in set(lab.tolist())},
            "PASS": passed}


def dormancy_diag(sched):
    """Distribution of dormancy at reactivations per regime."""
    out = {}
    for r in sorted(set(sched.regimes.tolist())):
        ds = [int(d) for t, d in enumerate(sched.dormancy)
              if sched.block_start[t] and sched.regimes[t] == r and d > 0]
        if ds:
            out[int(r)] = {"n_react": len(ds), "median": float(np.median(ds)),
                           "max": int(max(ds)),
                           "n_ge90": int(sum(d >= 90 for d in ds))}
    return out


def main():
    ret, dropped = load_french_vw()
    print(f"panel: {ret.shape[0]} days x {ret.shape[1]} industries "
          f"(dropped {dropped})", flush=True)
    X, Y, idx = build_xy_returns(ret)
    px = price_panel(ret)
    labs = {"L1": np.nan_to_num(label_L1(px)[idx], nan=0).astype(int),
            "L2": np.nan_to_num(label_L2(px)[idx], nan=0).astype(int)}

    # ---- Gate 1 ----
    gate_out = {}
    for lname, lab in labs.items():
        print(f"[gate] {lname}", flush=True)
        gate_out[lname] = gate50(X, Y, lab)
        print(f"  {lname}: gap={gate_out[lname]['gap_pct']:+.2f}% "
              f"z={gate_out[lname]['z_vs_shuffled']:+.2f} "
              f"p={gate_out[lname]['p_one_sided']:.4g} "
              f"PASS={gate_out[lname]['PASS']}", flush=True)
    with open(RESULTS / "e_french49_gate.json", "w") as fh:
        json.dump(gate_out, fh, indent=1, default=float)

    # ---- Dissociation ----
    class Cfg:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], K_SEL, W_MAX, 4

    cfg = Cfg()
    dis_out = {}
    for design in ("walkforward", "stitched"):
        # walk-forward uses the labeler with the better gate z (pre-reg: the
        # gate family is 2 cells; the dissociation runs on the stronger cell,
        # reported with the other as robustness if it also passed)
        lname = max(labs, key=lambda l: gate_out[l]["z_vs_shuffled"])
        lab = labs[lname]
        res = {a: {"overall": [], "post_react": []} for a in ARMS}
        t0 = time.time()
        if design == "walkforward":
            mkt = RealMarket(X, Y, lab, np.arange(len(idx)))
            sched = mkt.schedule()
            diag = dormancy_diag(sched)
            print(f"[dissoc/wf] labeler={lname} dormancy diag: {diag}",
                  flush=True)
            for s in range(20):
                for a in ARMS:
                    arm = ARM_FACTORIES[a](cfg, np.random.default_rng(
                        911 * s + 13), 2, "hard")
                    m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                                min_dormancy=90)
                    res[a]["overall"].append(m["overall"])
                    res[a]["post_react"].append(m["post_react"])
                if s == 0:
                    print(f"  seed0 in {time.time()-t0:.0f}s "
                          f"n_react={m['n_react']} T={sched.T}", flush=True)
        else:
            lib = BlockLibrary(X, Y, lab.astype(float), np.arange(len(idx)),
                               min_len=8)
            counts = lib.counts()
            rare = min(counts, key=counts.get)
            others = [r for r in range(4) if r != rare and counts[r] > 0]
            diag = {"block_counts": counts, "rare": rare}
            print(f"[dissoc/st] blocks={counts} rare={rare}", flush=True)
            for s in range(20):
                rng = np.random.default_rng(4000 + s)
                seq = []
                for cyc in range(16):
                    for r in rng.permutation(others):
                        seq.append((int(r), int(rng.integers(25, 50))))
                    if cyc % 3 == 2:
                        seq.append((rare, int(rng.integers(15, 30))))
                mkt = StitchedMarket(lib, rng)
                sched = mkt.materialize(seq)
                for a in ARMS:
                    arm = ARM_FACTORIES[a](cfg, np.random.default_rng(
                        733 * s + 7), 2, "hard")
                    m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                                min_dormancy=90)
                    res[a]["overall"].append(m["overall"])
                    res[a]["post_react"].append(m["post_react"])
        pv = {}
        for a, b in PAIRS:
            _, p = welch(res[a]["post_react"], res[b]["post_react"])
            pv[f"{a} vs {b}"] = p
        # Gate 2: paired per-seed A1 - A9
        d_fg = (np.array(res["A1-monolith-erm"]["post_react"])
                - np.array(res["A9-oracle-pinned"]["post_react"]))
        gamma = {"mean": float(d_fg.mean()),
                 "ci95": float(1.96 * d_fg.std(ddof=1) / np.sqrt(len(d_fg))),
                 "positive_significant": bool(
                     d_fg.mean() - 1.96 * d_fg.std(ddof=1)
                     / np.sqrt(len(d_fg)) > 0)}
        dis_out[design] = {
            "labeler": lname, "diag": diag,
            "post_react": summarize({a: res[a]["post_react"] for a in ARMS}),
            "overall": summarize({a: res[a]["overall"] for a in ARMS}),
            "welch_p": pv, "holm_p": holm(pv),
            "gate2_forgetting_deficit": gamma,
            "raw": res}
        print(f"[dissoc/{design}] gate2 Γ={gamma['mean']:.5f}"
              f"±{gamma['ci95']:.5f} sig={gamma['positive_significant']}; "
              f"min raw p={min(pv.values()):.4f} "
              f"({(time.time()-t0)/60:.1f} min)", flush=True)
    with open(RESULTS / "e_french49_dissoc.json", "w") as fh:
        json.dump(dis_out, fh, indent=1, default=float)
    print("FRENCH BATTERY COMPLETE", flush=True)


if __name__ == "__main__":
    main()
