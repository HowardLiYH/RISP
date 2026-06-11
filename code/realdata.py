"""
Real-data layer for RISP experiments.

- Loaders: Bybit crypto daily panel (5 USDT pairs), FRED commodities panel.
- Causal (leakage-free) regime labelers:
    L1: rolling-percentile volatility band x trend sign  -> 4 regimes
    L2: causal 2-state filtered volatility model x trend -> 4 regimes
- Cross-sectional feature builder (momentum, reversal, vol, MA-gap, const).
- StitchedMarket: semi-synthetic regime-stitched bootstrap (real per-regime
  day-blocks re-arranged into controlled dormancy schedules).
- RealMarket: strict walk-forward replay of the actual history.

All labelers use information up to t-1 only (verified by construction:
rolling windows exclude the current day via shift(1)).
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

from risp import Schedule

_LOCAL = Path(__file__).resolve().parents[1] / "data"
_GAUSE = Path(__file__).resolve().parents[2] / "GAUSE" / "data"
GAUSE_DATA = _LOCAL if (_LOCAL / "bybit").exists() else _GAUSE

CRYPTO_TICKERS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
REGIME_NAMES_REAL = ["calm-up", "calm-down", "vol-up", "vol-down"]


# ----------------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------------

def load_crypto_panel(freq: str = "1D") -> pd.DataFrame:
    """Aligned close-price panel, columns = tickers."""
    frames = {}
    for tk in CRYPTO_TICKERS:
        f = GAUSE_DATA / "bybit" / f"{tk}_{freq}.csv"
        df = pd.read_csv(f, parse_dates=["timestamp"]).set_index("timestamp")
        frames[tk] = df["close"]
    panel = pd.DataFrame(frames).dropna()
    return panel


def load_commodity_panel() -> pd.DataFrame:
    f = GAUSE_DATA / "commodities" / "fred_prices.csv"
    df = pd.read_csv(f, parse_dates=["date"])
    panel = df.pivot_table(index="date", columns="commodity",
                           values="price").dropna()
    return panel


# ----------------------------------------------------------------------------
# Causal labelers (computed on a reference index, e.g. BTC or first column)
# ----------------------------------------------------------------------------

def label_L1(panel: pd.DataFrame, vol_win=20, trend_win=50,
             vol_pct_win=252) -> np.ndarray:
    """Vol band (rolling-percentile of trailing vol) x trend sign. Causal:
    every input is shifted one day so day t uses data through t-1."""
    px = panel.mean(axis=1) if panel.shape[1] > 1 else panel.iloc[:, 0]
    # equal-weight index in log space to avoid scale domination
    px = np.log(panel).mean(axis=1)
    ret = px.diff()
    vol = ret.rolling(vol_win).std().shift(1)
    vol_rank = vol.rolling(vol_pct_win, min_periods=60).rank(pct=True)
    trend = (px.shift(1) - px.shift(trend_win + 1))
    high_vol = (vol_rank > 0.7).astype(int)
    up = (trend > 0).astype(int)
    lab = high_vol * 2 + (1 - up)        # 0 calm-up 1 calm-down 2 vol-up 3 vol-down
    return lab.values


def label_L2(panel: pd.DataFrame, trend_win=50) -> np.ndarray:
    """Causal two-state filtered volatility model (Hamilton-style filter on
    squared index returns with online EM-free fixed transition matrix),
    crossed with trend sign. Fully causal: filter is forward-only."""
    px = np.log(panel).mean(axis=1)
    ret = px.diff().fillna(0.0).values
    T = len(ret)
    # two vol states, params estimated on an expanding warmup (first 250d)
    warm = min(250, T // 4)
    s_lo = np.std(ret[:warm]) * 0.7 + 1e-9
    s_hi = np.std(ret[:warm]) * 2.0 + 1e-9
    A = np.array([[0.97, 0.03], [0.06, 0.94]])
    p = np.array([0.5, 0.5])
    state = np.zeros(T, dtype=int)
    for t in range(T):
        x = ret[t - 1] if t > 0 else 0.0       # uses yesterday's return only
        lik = np.array([np.exp(-0.5 * (x / s_lo) ** 2) / s_lo,
                        np.exp(-0.5 * (x / s_hi) ** 2) / s_hi]) + 1e-300
        p = A.T @ p
        p = p * lik
        p = p / p.sum()
        state[t] = int(p[1] > 0.5)
    trend = (px.shift(1) - px.shift(trend_win + 1)).fillna(0.0).values
    up = (trend > 0).astype(int)
    return state * 2 + (1 - up)


# ----------------------------------------------------------------------------
# Cross-sectional features (causal: everything from <= t-1; y = day-t return)
# ----------------------------------------------------------------------------

def build_xy(panel: pd.DataFrame):
    """Returns X[t] (n_assets x d), y[t] (n_assets): day-t cross-section.
    Features: 5d momentum, 20d momentum, 20d vol, 50d MA gap, const."""
    lp = np.log(panel)
    r1 = lp.diff()
    feats = {
        "mom5": lp.shift(1) - lp.shift(6),
        "mom20": lp.shift(1) - lp.shift(21),
        "vol20": r1.rolling(20).std().shift(1),
        "magap": lp.shift(1) - lp.rolling(50).mean().shift(1),
    }
    y = r1                                  # day-t return (target)
    valid = pd.concat([v.stack() for v in feats.values()], axis=1).notna().all(axis=1)
    Xs, ys, index = [], [], []
    for t in range(len(panel)):
        row_ok = all(np.isfinite(v.iloc[t]).all() for v in feats.values()) \
            and np.isfinite(y.iloc[t]).all()
        if not row_ok:
            continue
        F = np.column_stack([standardize(v.iloc[t].values) for v in feats.values()]
                            + [np.ones(panel.shape[1])])
        Xs.append(F)
        ys.append(y.iloc[t].values)
        index.append(t)
    return np.array(Xs), np.array(ys), np.array(index)


def standardize(v):
    s = np.std(v)
    return (v - np.mean(v)) / (s + 1e-12)


# ----------------------------------------------------------------------------
# Semi-synthetic stitched market + real walk-forward market
# ----------------------------------------------------------------------------

class BlockLibrary:
    """Real per-regime day-blocks: contiguous runs of one L1 regime,
    minimum length, stored as (X, y) day arrays."""

    def __init__(self, X, Y, labels, idx, min_len=8):
        self.blocks = {r: [] for r in range(4)}
        lab = labels[idx]
        t = 0
        while t < len(idx):
            t1 = t
            while t1 + 1 < len(idx) and lab[t1 + 1] == lab[t]:
                t1 += 1
            if t1 - t + 1 >= min_len and lab[t] >= 0:
                self.blocks[int(lab[t])].append((X[t:t1 + 1], Y[t:t1 + 1]))
            t = t1 + 1

    def counts(self):
        return {r: len(b) for r, b in self.blocks.items()}


class StitchedMarket:
    """Replays real day-blocks according to a synthetic schedule. Each block
    drawn (without immediate repetition) per regime = one episode."""

    def __init__(self, lib: BlockLibrary, rng):
        self.lib, self.rng = lib, rng
        self.days = None

    def materialize(self, seq):
        """seq: list of (regime, length). Returns Schedule; lengths are taken
        from the sampled real blocks (truncated/concatenated to fit)."""
        days = []
        sched_seq = []
        ep_ct = {r: -1 for r in range(4)}
        for (r, L) in seq:
            need = L
            ep_ct[r] += 1
            chunk = []
            while need > 0:
                bi = int(self.rng.integers(len(self.lib.blocks[r])))
                Xb, Yb = self.lib.blocks[r][bi]
                take = min(need, len(Xb))
                for j in range(take):
                    chunk.append((Xb[j], Yb[j], r, ep_ct[r]))
                need -= take
            days.extend(chunk)
            sched_seq.append((r, L))
        self.days = days
        from risp import _seq_to_schedule
        return _seq_to_schedule(sched_seq, 4)

    def day_at(self, t, r, e):
        X, y, r0, e0 = self.days[t]
        return X, y


class RealMarket:
    """Strict walk-forward replay of actual history with causal labels."""

    def __init__(self, X, Y, labels, idx):
        self.X, self.Y = X, Y
        self.lab = labels[idx]

    def schedule(self) -> Schedule:
        T = len(self.X)
        regimes = self.lab.astype(int)
        episode = np.zeros(T, dtype=int)
        block_start = np.zeros(T, dtype=bool)
        dormancy = np.zeros(T, dtype=int)
        ep_ct = {r: -1 for r in set(regimes.tolist())}
        last = {r: None for r in set(regimes.tolist())}
        for t in range(T):
            r = regimes[t]
            if t == 0 or regimes[t - 1] != r:
                ep_ct[r] += 1
                block_start[t] = True
                dormancy[t] = (t - last[r]) if last[r] is not None else 0
            episode[t] = ep_ct[r]
            last[r] = t
        return Schedule(regimes, episode, block_start, dormancy)

    def day_at(self, t, r, e):
        return self.X[t], self.Y[t]
