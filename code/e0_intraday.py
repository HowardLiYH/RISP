"""
E0-intraday: the pre-registered structure-gate retest on richer data.

Roadmap item 2 (NEXT_STEPS_AND_REVIEW.tex §2.2): re-run the E0 gate where it
might pass, using data already on disk. Two upgrade axes, fixed BEFORE any
result is inspected:

  Frequency: 1D (anchor) -> 4H (6x bars, same 3.2y span) -> 1H (15k bars,
  1.7y span, SOL-limited).

  Feature inventory: the daily E0 used close-only features (mom5, mom20,
  vol20, magap50, const). The rich inventory adds, all causal via shift(1)
  and cross-sectionally standardized per bar:
    mom100        long momentum
    rev1          last-bar reversal
    pk20          Parkinson (high-low range) volatility, 20 bars
    volz50        log-volume z-score, 50 bars
    xsrank20      cross-sectional rank of mom20 (uniform in [-1, 1])

  Labelers: L1 (vol-percentile band x trend) and L2 (causal 2-state filter
  x trend), each in two window conventions:
    b (bar-native):  the daily window counts reinterpreted in bars
                     (20/50/252 bars) -> faster regimes, more episodes.
    w (wall-clock):  windows scaled by bars-per-day (x6 at 4H, x24 at 1H)
                     -> daily-comparable regimes, more bars per episode.
  At 1D the conventions coincide; 1D runs L1/L2 once each (rich features),
  isolating the feature axis against the archived close-only daily gate.

  Gate protocol: unchanged from e0() in run_experiments.py — walk-forward
  regime-conditioned ridge (refit every 60 bars, min 30 obs per regime,
  lambda=10) vs 10 block-shuffled-label controls vs pooled, scored by
  decision regret (top-k, k=2, w_max=0.25), evaluated on the second half.

  PASS criterion (same as the paper): z_vs_shuffled > 2 with gap_pct > 0
  in at least one (frequency, labeler) cell, with the pooled model not
  matching the conditioned one. All cells are reported either way.

Output: ../results/e0_intraday.json
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import regret
from run_experiments import block_shuffle, welch_vec
from realdata import CRYPTO_TICKERS, GAUSE_DATA, label_L1, label_L2, standardize

RESULTS = Path(__file__).resolve().parent / ".." / "results"

BARS_PER_DAY = {"1D": 1, "4H": 6, "1H": 24}


def load_ohlcv_panel(freq: str):
    """Aligned OHLCV panels: dict field -> DataFrame[t, ticker]."""
    per_field = {f: {} for f in ("open", "high", "low", "close", "volume")}
    gause_dir = Path(__file__).resolve().parents[2] / "GAUSE" / "data"
    for tk in CRYPTO_TICKERS:
        f = GAUSE_DATA / "bybit" / f"{tk}_{freq}.csv"
        if not f.exists():
            f = gause_dir / "bybit" / f"{tk}_{freq}.csv"
        df = (pd.read_csv(f, parse_dates=["timestamp"])
              .set_index("timestamp"))
        for f in per_field:
            per_field[f][tk] = df[f]
    fields = {f: pd.DataFrame(d) for f, d in per_field.items()}
    ok = fields["close"].dropna().index
    for f in fields:
        fields[f] = fields[f].loc[ok].dropna()
        ok = fields[f].index
    return {f: v.loc[ok] for f, v in fields.items()}


def build_xy_rich(fields):
    """X[t] (n x d), y[t] (n): rich causal cross-sectional features."""
    close, high, low, vol = (fields["close"], fields["high"],
                             fields["low"], fields["volume"])
    lp = np.log(close)
    r1 = lp.diff()
    pk = (np.log(high / low) ** 2 / (4 * np.log(2)))  # Parkinson variance
    lv = np.log1p(vol)
    mom20 = lp.shift(1) - lp.shift(21)
    feats = {
        "mom5": lp.shift(1) - lp.shift(6),
        "mom20": mom20,
        "mom100": lp.shift(1) - lp.shift(101),
        "rev1": -r1.shift(1),
        "vol20": r1.rolling(20).std().shift(1),
        "pk20": np.sqrt(pk.rolling(20).mean()).shift(1),
        "volz50": ((lv - lv.rolling(50).mean()) /
                   (lv.rolling(50).std() + 1e-12)).shift(1),
        "magap50": lp.shift(1) - lp.rolling(50).mean().shift(1),
        "xsrank20": mom20.rank(axis=1, pct=True) * 2 - 1,
    }
    y = r1
    Xs, ys, index = [], [], []
    for t in range(len(close)):
        row_ok = all(np.isfinite(v.iloc[t]).all() for v in feats.values()) \
            and np.isfinite(y.iloc[t]).all()
        if not row_ok:
            continue
        F = np.column_stack(
            [standardize(v.iloc[t].values) for v in feats.values()]
            + [np.ones(close.shape[1])])
        Xs.append(F)
        ys.append(y.iloc[t].values)
        index.append(t)
    return np.array(Xs), np.array(ys), np.array(index)


def gate(X, Y, lab, k=2, w_max=0.25, refit=60, lam=10.0, n_shuffle=10):
    """The e0() protocol, verbatim in structure."""
    T, n = len(X), X.shape[1]
    split = T // 2
    d = X.shape[2]

    def regimewise_regret(labels):
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
            r = labels[t]
            w = models.get(r)
            yh = X[t] @ w if w is not None else np.zeros(n)
            regs[t - split] = regret(yh, Y[t], k, w_max)
        return regs

    lab = np.nan_to_num(lab, nan=0).astype(int)
    rng = np.random.default_rng(42)
    real_reg = regimewise_regret(lab)
    sh_means = [regimewise_regret(block_shuffle(lab, rng)).mean()
                for _ in range(n_shuffle)]
    pooled_reg = regimewise_regret(np.zeros(T, dtype=int))
    _, p = welch_vec(real_reg, sh_means)
    return {
        "real_mean_regret": float(real_reg.mean()),
        "shuffled_mean_regret": float(np.mean(sh_means)),
        "shuffled_sd": float(np.std(sh_means)),
        "pooled_mean_regret": float(pooled_reg.mean()),
        "gap_pct": float(100 * (np.mean(sh_means) - real_reg.mean())
                         / (np.mean(sh_means) + 1e-12)),
        "z_vs_shuffled": float((np.mean(sh_means) - real_reg.mean())
                               / (np.std(sh_means) + 1e-12)),
        "cond_vs_pooled_pct": float(100 * (pooled_reg.mean() - real_reg.mean())
                                    / (pooled_reg.mean() + 1e-12)),
        "p_vs_shuffled": float(p),
        "n_bars_eval": int(T - split),
        "regime_counts": {int(r): int((lab == r).sum())
                          for r in set(lab.tolist())},
    }


def labelers_for(close_panel, scale):
    """Bar-native and wall-clock labeler variants (coincide at scale=1)."""
    out = {"L1b": label_L1(close_panel),
           "L2b": label_L2(close_panel)}
    if scale > 1:
        out["L1w"] = label_L1(close_panel, vol_win=20 * scale,
                              trend_win=50 * scale,
                              vol_pct_win=252 * scale)
        out["L2w"] = label_L2(close_panel, trend_win=50 * scale)
    return out


def episode_count(lab):
    """Number of contiguous same-label blocks (episode inventory)."""
    lab = np.asarray(lab)
    lab = lab[np.isfinite(lab)]
    return int(1 + (np.diff(lab) != 0).sum()) if len(lab) else 0


def main():
    out = {"protocol": "see module docstring; pre-registered before results"}
    t0 = time.time()
    for freq in ("1D", "4H", "1H"):
        fields = load_ohlcv_panel(freq)
        X, Y, idx = build_xy_rich(fields)
        scale = BARS_PER_DAY[freq]
        cells = {}
        for lname, lab_full in labelers_for(fields["close"], scale).items():
            lab = lab_full[idx]
            cell = gate(X, Y, lab)
            cell["n_episodes"] = episode_count(lab)
            cells[lname] = cell
            print(f"[{(time.time()-t0)/60:5.1f}m] {freq} {lname}: "
                  f"gap={cell['gap_pct']:+.2f}% z={cell['z_vs_shuffled']:+.2f} "
                  f"cond-vs-pooled={cell['cond_vs_pooled_pct']:+.2f}% "
                  f"episodes={cell['n_episodes']}", flush=True)
        out[freq] = {"n_bars": int(len(X)), "n_features": int(X.shape[2]),
                     "span": [str(fields['close'].index[0]),
                              str(fields['close'].index[-1])],
                     "cells": cells}
    f = RESULTS / "e0_intraday.json"
    with open(f, "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"[saved] {f.resolve()}")


if __name__ == "__main__":
    main()
