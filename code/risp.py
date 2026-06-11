"""
RISP: Regime-Invariant Specialist Pools for decision-focused learning
under regime-switching non-stationarity.

Core module: synthetic market, decision layer (cardinality portfolio + SPO
regret + SPO+ subgradient), capacity-bounded specialists (hard LRU / soft
interference), allocation arms A1-A9, run loop, and metrics.

All randomness is seeded. Every experiment writes JSON consumed by the papers.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field


# ============================================================================
# Decision layer: cardinality-constrained long-only portfolio, linear utility
#   Z = { z in [0, w_max]^n : sum z <= W_budget, ||z||_0 <= k }
#   F(z, y) = y^T z.  Exact argmax: w_max on the k largest positive coords
#   (budget assumed >= k * w_max so the cardinality constraint binds).
# ============================================================================

def solve_topk(y_hat: np.ndarray, k: int, w_max: float) -> np.ndarray:
    """Exact solution of max_z y_hat^T z over Z. O(n log n)."""
    n = y_hat.shape[0]
    z = np.zeros(n)
    idx = np.argsort(-y_hat)[:k]
    pos = idx[y_hat[idx] > 0.0]
    z[pos] = w_max
    return z


def regret(y_hat: np.ndarray, y: np.ndarray, k: int, w_max: float) -> float:
    """Decision regret rho(y_hat; y) = F(z*(y), y) - F(z(y_hat), y) >= 0."""
    z_star = solve_topk(y, k, w_max)
    z_hat = solve_topk(y_hat, k, w_max)
    return float(y @ z_star - y @ z_hat)


def spo_plus_loss_grad(w: np.ndarray, X: np.ndarray, y: np.ndarray,
                       k: int, w_max: float):
    """SPO+ loss and subgradient for the linear predictor y_hat = X w.

    Cast as minimization with cost c = -y, c_hat = -X w.
    l_SPO+(c_hat, c) = max_z (c - 2 c_hat)^T z + 2 c_hat^T z*(c) - c^T z*(c)
    d l / d c_hat = 2 (z*(c) - z*(2 c_hat - c));  d c_hat / d w = -X.
    """
    y_hat = X @ w
    z_star = solve_topk(y, k, w_max)            # argmin c^T z = argmax y^T z
    # z*(2 c_hat - c) = argmin (2 c_hat - c)^T z = argmax (2 y_hat - y)^T z
    z_alt = solve_topk(2.0 * y_hat - y, k, w_max)
    # loss value (for monitoring / variance penalty)
    loss = float((2.0 * y_hat - y) @ z_alt - 2.0 * y_hat @ z_star + y @ z_star)
    grad_chat = 2.0 * (z_star - z_alt)
    grad_w = -X.T @ grad_chat
    return loss, grad_w


# ============================================================================
# Synthetic regime-switching market with episode heterogeneity
# ============================================================================
# Regimes r = 0..R-1.  In regime r, episode e (the e-th occurrence of r):
#   asset i features x = [x1, x2, x_sp, 1]
#   y_i = theta_r . (x1, x2) + gamma_{r,e} * x_sp + b_r + eps
# theta_r: invariant decision-relevant loading (stable across episodes of r,
#          distinct across regimes -> cross-regime interference is real).
# gamma_{r,e}: spurious loading redrawn each episode, sd = HET * gamma_scale
#          (the episode "weather": ERM loads on it, invariance should not).

R_DEFAULT = 4
REGIME_NAMES = ["trend", "range", "highvol", "crisis"]


@dataclass
class SynthConfig:
    n_assets: int = 20
    d: int = 20                     # x1,x2 invariant; x3 spurious; 16 distractors; const
    k: int = 4
    w_max: float = 0.25
    R: int = R_DEFAULT
    noise: float = 0.02
    het: float = 1.0                # episode heterogeneity scale (E4 sweep)
    gamma_scale: float = 0.012
    theta_scale: float = 0.012     # |theta_r| ~ realistic daily alpha scale
    vol_mult: tuple = (1.0, 0.75, 2.0, 3.0)  # per-regime noise multiplier
    snr_mult: float = 1.0           # audit sweep: scales signal vs noise


class SyntheticMarket:
    def __init__(self, cfg: SynthConfig, seed: int):
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        c = cfg
        # invariant regime structure: theta_r distinct across regimes
        # (well-separated directions -> cross-regime interference is real)
        self.theta = np.zeros((c.R, 2))
        for r in range(c.R):
            self.theta[r] = c.theta_scale * c.snr_mult * np.array(
                [np.cos(2 * np.pi * r / c.R + 0.4),
                 np.sin(2 * np.pi * r / c.R + 0.4)])
        self.b = self.rng.normal(0.0, 0.001, size=c.R)
        self.gamma = {}             # (r, e) -> spurious loading

    def gamma_for(self, r: int, e: int) -> float:
        if (r, e) not in self.gamma:
            self.gamma[(r, e)] = self.rng.normal(
                0.0, self.cfg.het * self.cfg.gamma_scale * self.cfg.snr_mult)
        return self.gamma[(r, e)]

    def day_at(self, t: int, r: int, e: int):
        return self.day(r, e)

    def day(self, r: int, e: int):
        """One day's (X, y) in regime r, episode e."""
        c = self.cfg
        X = np.ones((c.n_assets, c.d))
        X[:, :c.d - 1] = self.rng.normal(0, 1, (c.n_assets, c.d - 1))
        g = self.gamma_for(r, e)
        mean = X[:, :2] @ self.theta[r] + g * X[:, 2] + self.b[r]
        y = mean + self.rng.normal(0, c.noise * c.vol_mult[r], c.n_assets)
        return X, y


# ----------------------------------------------------------------------------
# Regime schedules with controlled dormancy and marked reactivations
# ----------------------------------------------------------------------------

@dataclass
class Schedule:
    regimes: np.ndarray          # day -> regime id
    episode: np.ndarray          # day -> episode index of that regime
    block_start: np.ndarray      # day -> bool, first day of a block
    dormancy: np.ndarray         # day -> dormancy length preceding this block
                                 #         (only meaningful on block_start)
    T: int = 0

    def __post_init__(self):
        self.T = len(self.regimes)

    def reactivation_days(self, min_dormancy: int):
        """Days that begin a block whose regime was dormant >= min_dormancy."""
        out = []
        for t in range(self.T):
            if self.block_start[t] and self.dormancy[t] >= min_dormancy:
                out.append(t)
        return out


def make_schedule(rng: np.random.Generator, R: int = R_DEFAULT,
                  n_cycles: int = 18, block_len=(25, 60),
                  crisis_every: int = 4, crisis_len=(15, 30)) -> Schedule:
    """Common regimes (0,1,2) alternate in blocks; crisis (R-1) appears only
    every `crisis_every` cycles -> long dormancy, recurring reactivations."""
    seq = []
    cyc = 0
    common = [0, 1, 2] if R >= 4 else list(range(R - 1))
    while cyc < n_cycles:
        order = rng.permutation(common)
        for r in order:
            L = int(rng.integers(block_len[0], block_len[1] + 1))
            seq.append((int(r), L))
        cyc += 1
        if cyc % crisis_every == 0:
            L = int(rng.integers(crisis_len[0], crisis_len[1] + 1))
            seq.append((R - 1, L))
    return _seq_to_schedule(seq, R)


def make_dormancy_schedule(rng: np.random.Generator, D: int,
                           R: int = R_DEFAULT, n_react: int = 8,
                           block_len=(25, 60), crisis_len: int = 20) -> Schedule:
    """E3: focal regime R-1 reactivates every ~D days of dormancy exactly."""
    seq = []
    common = [0, 1, 2] if R >= 4 else list(range(R - 1))
    # initial training occurrences of focal regime
    for r in [R - 1, 0, R - 1, 1, R - 1, 2]:
        L = crisis_len if r == R - 1 else int(rng.integers(*block_len))
        seq.append((int(r), L))
    for _ in range(n_react):
        filler = 0
        while filler < D:
            r = int(rng.choice(common))
            L = int(rng.integers(block_len[0], block_len[1] + 1))
            seq.append((r, L))
            filler += L
        seq.append((R - 1, crisis_len))
    return _seq_to_schedule(seq, R)


def _seq_to_schedule(seq, R) -> Schedule:
    T = sum(L for _, L in seq)
    regimes = np.zeros(T, dtype=int)
    episode = np.zeros(T, dtype=int)
    block_start = np.zeros(T, dtype=bool)
    dormancy = np.zeros(T, dtype=int)
    ep_count = {r: -1 for r in range(R)}
    last_seen = {r: None for r in range(R)}
    t = 0
    for r, L in seq:
        ep_count[r] += 1
        block_start[t] = True
        dormancy[t] = (t - last_seen[r]) if last_seen[r] is not None else 0
        regimes[t:t + L] = r
        episode[t:t + L] = ep_count[r]
        last_seen[r] = t + L - 1
        t += L
    return Schedule(regimes, episode, block_start, dormancy)


# ============================================================================
# Capacity-bounded specialist with episode-aware training
# ============================================================================

@dataclass
class Head:
    w: np.ndarray
    last_used: int = 0
    strength: float = 1.0          # soft-interference knowledge multiplier


class Specialist:
    """Linear per-regime heads under capacity K with hard-LRU or soft-
    interference memory; trains with ERM or invariance (Var_e + beta E_e)
    objective on an episode buffer (SPO+ surrogate)."""

    def __init__(self, d: int, K: int, k: int, w_max: float, rng,
                 mode: str = "erm", memory: str = "hard",
                 beta: float = 1.0, lr: float = 0.08, rho_int: float = 0.06,
                 buf_episodes: int = 6, buf_days: int = 40):
        self.d, self.K, self.k, self.w_max = d, K, k, w_max
        self.rng = rng
        self.mode, self.memory = mode, memory
        self.beta, self.lr, self.rho_int = beta, lr, rho_int
        self.heads: dict[int, Head] = {}
        self.buf: dict[int, dict[int, list]] = {}   # regime -> episode -> [(X,y)]
        self.buf_episodes, self.buf_days = buf_episodes, buf_days
        self.t = 0

    # ---- memory bookkeeping ----
    def _touch(self, r: int):
        """Hard model: LRU eviction (head + buffer) at capacity.
        Soft model: no eviction; every foreign update decays all other
        held heads at a rate scaling with capacity overflow
        (GAUSE-style graded interference)."""
        self.t += 1
        if r not in self.heads:
            if self.memory == "hard" and len(self.heads) >= self.K:
                lru = min(self.heads, key=lambda q: self.heads[q].last_used)
                del self.heads[lru]
                self.buf.pop(lru, None)
            self.heads[r] = Head(w=np.zeros(self.d))
            self.buf[r] = {}
        self.heads[r].last_used = self.t
        if self.memory == "soft":
            overflow = max(1.0, len(self.heads) / self.K)
            rho_eff = min(0.5, self.rho_int * overflow)
            for q, h in self.heads.items():
                if q != r:
                    h.strength *= (1.0 - rho_eff)
                    h.w *= (1.0 - rho_eff)
            self.heads[r].strength = 1.0

    def holds(self, r: int) -> bool:
        return r in self.heads

    def predict(self, X: np.ndarray, r: int) -> np.ndarray:
        if r in self.heads:
            return X @ self.heads[r].w
        return 1e-6 * self.rng.normal(size=X.shape[0])   # uninformed

    # ---- learning ----
    def store(self, X, y, r: int, e: int):
        ep = self.buf.setdefault(r, {}).setdefault(e, [])
        ep.append((X, y))
        if len(ep) > self.buf_days:
            ep.pop(0)
        eps = self.buf[r]
        while len(eps) > self.buf_episodes:
            del eps[min(eps.keys())]

    def learn(self, X, y, r: int, e: int, n_steps: int = 2):
        """One observation: store, touch memory, take SGD steps on the
        regime-r objective over the episode buffer."""
        self._touch(r)
        self.store(X, y, r, e)
        h = self.heads[r]
        eps = self.buf[r]
        for _ in range(n_steps):
            if self.mode == "erm" or len(eps) < 2:
                # plain ERM on pooled buffer
                keys = list(eps.keys())
                ekey = keys[int(self.rng.integers(len(keys)))]
                Xb, yb = ep_sample(eps[ekey], self.rng)
                _, g = spo_plus_loss_grad(h.w, Xb, yb, self.k, self.w_max)
                h.w -= self.lr * g / max(1, Xb.shape[0])
            else:
                # invariance: Var_e[lbar_e] + beta * E_e[lbar_e]
                losses, grads = [], []
                for ekey in eps:
                    Xb, yb = ep_sample(eps[ekey], self.rng)
                    l, g = spo_plus_loss_grad(h.w, Xb, yb, self.k, self.w_max)
                    losses.append(l / max(1, Xb.shape[0]))
                    grads.append(g / max(1, Xb.shape[0]))
                E = len(losses)
                lbar = float(np.mean(losses))
                g_tot = np.zeros(self.d)
                for l, g in zip(losses, grads):
                    g_tot += (2.0 * (l - lbar) + self.beta) * g / E
                h.w -= self.lr * g_tot


def ep_sample(ep_list, rng, m: int = 8):
    """Sample a minibatch of days from one episode's stored data."""
    take = min(m, len(ep_list))
    sel = rng.choice(len(ep_list), size=take, replace=False)
    Xs = np.vstack([ep_list[i][0] for i in sel])
    ys = np.concatenate([ep_list[i][1] for i in sel])
    return Xs, ys


# ============================================================================
# Arms.  Interface: decide(X, r) -> y_hat used for the served decision;
#                   observe(X, y, r, e, served_regret) -> internal updates.
# ============================================================================

class ArmBase:
    name = "base"

    def decide(self, X, r):
        raise NotImplementedError

    def observe(self, X, y, r, e, served_regret):
        raise NotImplementedError


class MonolithArm(ArmBase):
    """A1 / A7: one capacity-K learner that always learns the active regime
    (the canonical reward-driven allocation: capacity follows activity)."""

    def __init__(self, cfg, rng, mode="erm", memory="hard", beta=1.0, K=2):
        self.s = Specialist(cfg.d, K, cfg.k, cfg.w_max, rng,
                            mode=mode, memory=memory, beta=beta)
        self.name = f"monolith-{mode}"

    def decide(self, X, r):
        return self.s.predict(X, r)

    def observe(self, X, y, r, e, served_regret):
        self.s.learn(X, y, r, e)


class RouterArm(ArmBase):
    """A2: Mixture-of-Experts with a gate trained on realized regret.
    The gate routes each regime to one expert; routed expert learns.
    Dormant regimes emit no gate gradient (Observation 1)."""
    name = "moe-router"

    def __init__(self, cfg, rng, N=4, K=2, mode="erm", memory="hard",
                 beta=1.0, eps=0.10, gate_lr=0.25):
        self.rng = rng
        self.R = cfg.R
        self.experts = [Specialist(cfg.d, K, cfg.k, cfg.w_max,
                                   np.random.default_rng(rng.integers(2**31)),
                                   mode=mode, memory=memory, beta=beta)
                        for _ in range(N)]
        self.G = np.zeros((cfg.R, N))
        self.eps, self.gate_lr = eps, gate_lr
        self.base = {}            # running regret baseline per regime

    def _route(self, r, explore=True):
        if explore and self.rng.random() < self.eps:
            return int(self.rng.integers(len(self.experts)))
        return int(np.argmax(self.G[r]))

    def decide(self, X, r):
        return self.experts[self._route(r, explore=False)].predict(X, r)

    def observe(self, X, y, r, e, served_regret):
        j = self._route(r, explore=True)
        ex = self.experts[j]
        rg = regret(ex.predict(X, r), y, ex.k, ex.w_max)
        b = self.base.get(r, rg)
        self.base[r] = 0.95 * b + 0.05 * rg
        self.G[r, j] += self.gate_lr * (b - rg)      # reward-driven gate
        ex.learn(X, y, r, e)


class RecentPerfArm(ArmBase):
    """A3: recent-performance capital allocator (industry baseline).
    Capital share = softmax of trailing performance; the served decision is
    the top-capital specialist's; every specialist trains on the ACTIVE
    regime with probability equal to its capital share (capital = training/
    recalibration intensity), so starved specialists drift into the active
    regime and dormant expertise erodes at the capital-floor rate."""
    name = "recent-perf"

    def __init__(self, cfg, rng, N=4, K=2, mode="erm", memory="hard",
                 beta=1.0, lookback=60, temp=0.02):
        self.rng = rng
        self.specs = [Specialist(cfg.d, K, cfg.k, cfg.w_max,
                                 np.random.default_rng(rng.integers(2**31)),
                                 mode=mode, memory=memory, beta=beta)
                      for _ in range(N)]
        self.hist = [[] for _ in range(N)]
        self.lookback, self.temp = lookback, temp
        self.k, self.w_max = cfg.k, cfg.w_max

    def _weights(self):
        perf = []
        for h in self.hist:
            perf.append(-np.mean(h[-self.lookback:]) if h else 0.0)
        perf = np.array(perf)
        wts = np.exp((perf - perf.max()) / self.temp)
        return wts / wts.sum()

    def decide(self, X, r):
        v = self._weights()
        return self.specs[int(np.argmax(v))].predict(X, r)

    def observe(self, X, y, r, e, served_regret):
        v = self._weights()
        for i, sp in enumerate(self.specs):
            rg = regret(sp.predict(X, r), y, self.k, self.w_max)
            self.hist[i].append(rg)
            if self.rng.random() < v[i]:
                sp.learn(X, y, r, e)


class FixedNicheArm(ArmBase):
    """A4: random fixed reward-independent niches (coverage gaps possible).
    With oracle=True: hand-pinned one-per-regime assignment (skyline)."""
    name = "random-fixed"

    def __init__(self, cfg, rng, N=4, K=2, mode="erm", memory="hard",
                 beta=1.0, oracle=False):
        self.rng = rng
        self.R = cfg.R
        self.specs = [Specialist(cfg.d, K, cfg.k, cfg.w_max,
                                 np.random.default_rng(rng.integers(2**31)),
                                 mode=mode, memory=memory, beta=beta)
                      for _ in range(N)]
        self.owner = {}
        if oracle:
            self.name = f"oracle-pinned-{mode}"
            for r in range(cfg.R):
                self.owner[r] = r % N
        else:
            # each specialist draws K niches at random; owner = first claimer
            for i in range(N):
                for r in self.rng.choice(cfg.R, size=min(K, cfg.R),
                                         replace=False):
                    self.owner.setdefault(int(r), i)

    def decide(self, X, r):
        if r in self.owner:
            return self.specs[self.owner[r]].predict(X, r)
        return 1e-6 * self.rng.normal(size=X.shape[0])

    def observe(self, X, y, r, e, served_regret):
        if r in self.owner:
            self.specs[self.owner[r]].learn(X, y, r, e)


class RISPArm(ArmBase):
    """A5 (mode=erm) / A6 (mode=inv): batched winner-take-all competition with
    EG affinity update; pin once converged; owner-only training thereafter."""

    def __init__(self, cfg, rng, N=4, K=2, mode="inv", memory="hard",
                 beta=1.0, Wc=20, eta=0.6, lam=0.3, pin_thresh=0.95,
                 pin=True):
        self.rng = rng
        self.R = cfg.R
        self.N = N
        self.k, self.w_max = cfg.k, cfg.w_max
        self.specs = [Specialist(cfg.d, K, cfg.k, cfg.w_max,
                                 np.random.default_rng(rng.integers(2**31)),
                                 mode=mode, memory=memory, beta=beta)
                      for _ in range(N)]
        self.alpha = np.full((N, cfg.R), 1.0 / cfg.R)
        self.Wc, self.eta, self.lam = Wc, eta, lam
        self.pin_thresh, self.pin_enabled = pin_thresh, pin
        self.pinned: dict[int, int] = {}
        self.win_quality = np.zeros(N)
        self.win_days = 0
        self.win_regime = None
        self.win_data: list = []
        self.name = f"risp-{mode}" + ("" if pin else "-nopin")

    def _owner(self, r):
        if r in self.pinned:
            return self.pinned[r]
        return int(np.argmax(self.alpha[:, r]))

    def decide(self, X, r):
        return self.specs[self._owner(r)].predict(X, r)

    def _close_window(self):
        if self.win_days == 0 or self.win_regime is None:
            return
        r = self.win_regime
        score = -self.win_quality / self.win_days \
            + self.lam * (self.alpha[:, r] - 1.0 / self.R)
        i_star = int(np.argmax(score))
        # EG / Hedge update on the winner's affinity row
        a = self.alpha[i_star].copy()
        a[r] *= np.exp(self.eta)
        self.alpha[i_star] = a / a.sum()
        # winner trains on the window's data
        for (X, y, e) in self.win_data:
            self.specs[i_star].learn(X, y, r, e, n_steps=1)
        # pinning
        if self.pin_enabled and r not in self.pinned \
                and self.alpha[i_star, r] >= self.pin_thresh:
            self.pinned[r] = i_star
        self.win_quality = np.zeros(self.N)
        self.win_days = 0
        self.win_data = []

    def observe(self, X, y, r, e, served_regret):
        if r in self.pinned:
            self.specs[self.pinned[r]].learn(X, y, r, e)
            return
        if self.win_regime is not None and r != self.win_regime:
            self._close_window()
        self.win_regime = r
        for i, sp in enumerate(self.specs):
            self.win_quality[i] += regret(sp.predict(X, r), y,
                                          self.k, self.w_max)
        self.win_data.append((X, y, e))
        self.win_days += 1
        if self.win_days >= self.Wc:
            self._close_window()


class HedgeFixedArm(ArmBase):
    """A8a: Hedge / exponential weights over FIXED strategies (no learning).
    The adaptive online-learning baseline over static experts."""
    name = "hedge-fixed"

    def __init__(self, cfg, rng, eta=0.10):
        self.k, self.w_max = cfg.k, cfg.w_max
        self.d = cfg.d
        # fixed linear strategies: +/- each feature direction
        dirs = []
        for j in range(cfg.d - 1):
            v = np.zeros(cfg.d); v[j] = 1.0; dirs.append(v.copy())
            v = np.zeros(cfg.d); v[j] = -1.0; dirs.append(v)
        self.strats = dirs
        self.logw = np.zeros(len(dirs))
        self.eta = eta

    def decide(self, X, r):
        j = int(np.argmax(self.logw))
        return X @ self.strats[j]

    def observe(self, X, y, r, e, served_regret):
        for j, w in enumerate(self.strats):
            rg = regret(X @ w, y, self.k, self.w_max)
            self.logw[j] -= self.eta * rg


class HedgeLearnersArm(ArmBase):
    """A8b: Hedge over capacity-bounded LEARNING experts; the top-weight
    learner trains on the active regime (training follows the weight)."""
    name = "hedge-learners"

    def __init__(self, cfg, rng, N=4, K=2, mode="erm", memory="hard",
                 beta=1.0, eta=0.10):
        self.rng = rng
        self.k, self.w_max = cfg.k, cfg.w_max
        self.specs = [Specialist(cfg.d, K, cfg.k, cfg.w_max,
                                 np.random.default_rng(rng.integers(2**31)),
                                 mode=mode, memory=memory, beta=beta)
                      for _ in range(N)]
        self.logw = np.zeros(N)
        self.eta = eta

    def decide(self, X, r):
        return self.specs[int(np.argmax(self.logw))].predict(X, r)

    def observe(self, X, y, r, e, served_regret):
        for i, sp in enumerate(self.specs):
            rg = regret(sp.predict(X, r), y, self.k, self.w_max)
            self.logw[i] -= self.eta * rg
        self.specs[int(np.argmax(self.logw))].learn(X, y, r, e)


# ============================================================================
# Run loop and metrics
# ============================================================================

ARM_FACTORIES = {
    "A1-monolith-erm":  lambda cfg, rng, K, mem: MonolithArm(cfg, rng, "erm", mem, K=K),
    "A2-router":        lambda cfg, rng, K, mem: RouterArm(cfg, rng, K=K, memory=mem),
    "A3-recentperf":    lambda cfg, rng, K, mem: RecentPerfArm(cfg, rng, K=K, memory=mem),
    "A4-randomfixed":   lambda cfg, rng, K, mem: FixedNicheArm(cfg, rng, K=K, memory=mem),
    "A5-risp-erm":  lambda cfg, rng, K, mem: RISPArm(cfg, rng, K=K, mode="erm", memory=mem),
    "A6-risp-inv":  lambda cfg, rng, K, mem: RISPArm(cfg, rng, K=K, mode="inv", memory=mem),
    "A7-monolith-inv":  lambda cfg, rng, K, mem: MonolithArm(cfg, rng, "inv", mem, K=K),
    "A8a-hedge-fixed":  lambda cfg, rng, K, mem: HedgeFixedArm(cfg, rng),
    "A8b-hedge-learn":  lambda cfg, rng, K, mem: HedgeLearnersArm(cfg, rng, K=K, memory=mem),
    "A9-oracle-pinned": lambda cfg, rng, K, mem: FixedNicheArm(cfg, rng, K=K, memory=mem, oracle=True),
    "A10-oracle-inv":   lambda cfg, rng, K, mem: FixedNicheArm(cfg, rng, K=K, memory=mem, oracle=True, mode="inv"),
}


def run_arm(arm: ArmBase, market, sched: Schedule, cfg,
            probe: int = 15, min_dormancy: int = 90):
    """Run one arm through the schedule; return metric dict."""
    T = sched.T
    daily = np.zeros(T)
    for t in range(T):
        r = int(sched.regimes[t]); e = int(sched.episode[t])
        X, y = market.day_at(t, r, e)
        y_hat = arm.decide(X, r)
        rg = regret(y_hat, y, cfg.k, cfg.w_max)
        daily[t] = rg
        arm.observe(X, y, r, e, rg)
    react = sched.reactivation_days(min_dormancy)
    probe_mask = np.zeros(T, dtype=bool)
    for t0 in react:
        probe_mask[t0:t0 + probe] = True
    # steady-state regret: within-block days beyond the probe window
    late_mask = np.zeros(T, dtype=bool)
    t = 0
    while t < T:
        t1 = t
        while t1 + 1 < T and not sched.block_start[t1 + 1]:
            t1 += 1
        if t1 - t + 1 > probe:
            late_mask[t + probe:t1 + 1] = True
        t = t1 + 1
    half = int(T * 0.5)
    return {
        "overall": float(daily[half:].mean()),
        "post_react": float(daily[probe_mask & (np.arange(T) >= half)].mean())
        if (probe_mask & (np.arange(T) >= half)).any() else float("nan"),
        "steady": float(daily[late_mask & (np.arange(T) >= half)].mean()),
        "n_react": int(sum(1 for t0 in react if t0 >= half)),
        "daily": daily,
        "react_days": [t0 for t0 in react if t0 >= half],
    }


# ----------------------------------------------------------------------------
# Statistics: Welch tests + Holm-Bonferroni, mean +/- 95% CI over seeds
# ----------------------------------------------------------------------------

def welch(a, b):
    from scipy import stats
    t, p = stats.ttest_ind(a, b, equal_var=False)
    return float(t), float(p)


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        run = max(run, adj)
        out[k] = run
    return out


def ci95(xs):
    xs = np.asarray(xs, dtype=float)
    m = xs.mean()
    h = 1.96 * xs.std(ddof=1) / np.sqrt(len(xs)) if len(xs) > 1 else 0.0
    return float(m), float(h)
