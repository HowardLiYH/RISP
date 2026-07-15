"""
E0-intraday confirmation pass.

Pre-registered BEFORE the full screen finished (2026-07-14): any cell of
e0_intraday.json with z_vs_shuffled > 2, gap_pct > 0, and
cond_vs_pooled_pct > 0 is re-tested with n_shuffle=50 (screen used 10).
Confirmation criteria, fixed here:
  - z_vs_shuffled > 2 with 50 shuffles, AND
  - one-sided p (t, 49 dof) < 0.005  [Bonferroni-safe against the 10
    screened cells], AND
  - split-half stability: positive gap on BOTH halves of the eval window
    (each half scored against its own 50-shuffle control distribution).
Cells that pass the screen but fail confirmation are reported as
screen-only (not gate passes). Output: ../results/e0_intraday_confirm.json
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import regret
from run_experiments import block_shuffle
from e0_intraday import (BARS_PER_DAY, load_ohlcv_panel, build_xy_rich,
                         labelers_for, episode_count)

RESULTS = Path(__file__).resolve().parent / ".." / "results"
N_SHUFFLE = 50


def regret_series(X, Y, labels, k=2, w_max=0.25, refit=60, lam=10.0):
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
        regs[t - split] = regret(yh, Y[t], k, w_max)
    return regs


def confirm_cell(X, Y, lab):
    from scipy import stats
    lab = np.nan_to_num(lab, nan=0).astype(int)
    rng = np.random.default_rng(4242)   # fresh seed, disjoint from screen
    real = regret_series(X, Y, lab)
    sh = np.array([regret_series(X, Y, block_shuffle(lab, rng))
                   for _ in range(N_SHUFFLE)])          # (S, T_eval)
    sh_means = sh.mean(axis=1)
    z = (sh_means.mean() - real.mean()) / (sh_means.std() + 1e-12)
    t_stat, p_two = stats.ttest_1samp(sh_means, real.mean())
    p_one = p_two / 2 if sh_means.mean() > real.mean() else 1 - p_two / 2
    half = len(real) // 2
    halves = {}
    for name, sl in (("first_half", slice(0, half)),
                     ("second_half", slice(half, None))):
        rh, shh = real[sl].mean(), sh[:, sl].mean(axis=1)
        halves[name] = {
            "gap_pct": float(100 * (shh.mean() - rh) / (shh.mean() + 1e-12)),
            "z": float((shh.mean() - rh) / (shh.std() + 1e-12)),
        }
    passed = bool(z > 2 and p_one < 0.005
                  and halves["first_half"]["gap_pct"] > 0
                  and halves["second_half"]["gap_pct"] > 0)
    return {
        "real_mean_regret": float(real.mean()),
        "shuffled_mean_regret": float(sh_means.mean()),
        "gap_pct": float(100 * (sh_means.mean() - real.mean())
                         / (sh_means.mean() + 1e-12)),
        "z_vs_shuffled": float(z),
        "p_one_sided": float(p_one),
        "n_shuffle": N_SHUFFLE,
        "split_half": halves,
        "CONFIRMED": passed,
    }


def main():
    screen = json.load(open(RESULTS / "e0_intraday.json"))
    todo = []
    for freq in ("1D", "4H", "1H"):
        for lname, cell in screen.get(freq, {}).get("cells", {}).items():
            if (cell["z_vs_shuffled"] > 2 and cell["gap_pct"] > 0
                    and cell["cond_vs_pooled_pct"] > 0):
                todo.append((freq, lname))
    print("cells passing screen:", todo, flush=True)
    out = {"screen_passes": [f"{f}/{l}" for f, l in todo]}
    t0 = time.time()
    for freq, lname in todo:
        fields = load_ohlcv_panel(freq)
        X, Y, idx = build_xy_rich(fields)
        lab = labelers_for(fields["close"], BARS_PER_DAY[freq])[lname][idx]
        res = confirm_cell(X, Y, lab)
        res["n_episodes"] = episode_count(lab)
        out[f"{freq}/{lname}"] = res
        print(f"[{(time.time()-t0)/60:5.1f}m] {freq} {lname}: "
              f"gap={res['gap_pct']:+.2f}% z={res['z_vs_shuffled']:+.2f} "
              f"p={res['p_one_sided']:.4f} halves="
              f"({res['split_half']['first_half']['gap_pct']:+.2f}%,"
              f"{res['split_half']['second_half']['gap_pct']:+.2f}%) "
              f"CONFIRMED={res['CONFIRMED']}", flush=True)
    f = RESULTS / "e0_intraday_confirm.json"
    with open(f, "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"[saved] {f.resolve()}")


if __name__ == "__main__":
    main()
