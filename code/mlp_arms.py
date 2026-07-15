"""
E-X4 (PREREG_FRENCH49.md, addendum E): MLP arms for the CPU emergent-
forgetting probe.

Design constraints (binding, quoted from the prereg):
  "shared trunk 20->32->32 + linear heads, SAME architecture for all arms,
   NO eviction model -- the monolith is one trunk+head; A9 pins heads
   sharing the trunk; forgetting can arise ONLY as representation
   interference."

Every arm here is the SAME network class: a shared trunk
    x (d=20) -> tanh(x W1 + b1) (32) -> tanh(. W2 + b2) (32)
with one or more linear heads y_hat = z2 . v_h + c_h on the 32-dim
representation.  There is NO eviction, NO buffer deletion, NO decay knob
anywhere in this file.  The training buffer only ever grows.  Forgetting,
if it appears, can arise only as gradient interference in the shared trunk
(and, for A1-mlp's single head, in the head itself).

Activation choice (documented per prereg): tanh.  Rationale: heads are
zero-initialised to match risp.py's linear Specialist (w = 0), so early
SPO+ error vectors are sparse +/-2*w_max spikes; a bounded, symmetric
activation keeps the backprop signal stable under those spikes, whereas
relu with a zero head risks dead units.  tanh is also the classical
setting of the catastrophic-interference literature.

Training objective: the same SPO+ decision surrogate as risp.py, with the
gradient taken w.r.t. y_hat and backpropagated through head + trunk:
    dl/dy_hat = 2 (z*(2 y_hat - y) - z*(y))
(identical algebra to risp.spo_plus_loss_grad, which uses
grad_w = X^T dl/dy_hat for the linear predictor).

Read-only reuse from risp.py: solve_topk, regret, ep_sample.  Nothing in
risp.py is modified.

Arms (interface = risp.ArmBase: decide(X, r) -> y_hat; observe(...)):
  A1-mlp : one trunk + ONE head trained on everything (no regime routing).
  A9-mlp : oracle -- one head per regime, pinned by the true regime label;
           the trunk receives gradients from whichever head is active.
  A5-mlp : RISP-ERM-style emergent competition over N=4 heads, a faithful
           port of risp.RISPArm's batched winner-take-all window + EG
           affinity update + pin rule (Wc=20, eta=0.6, lam=0.3,
           pin_thresh=0.95 -- same constants).  Documented simplifications
           vs the linear RISPArm (see class docstring below).
  A6-mlp : A5-mlp + the episode-variance invariance penalty
           Var_e[lbar_e] + beta E_e[lbar_e] on the active head's loss
           across the episode buffer (buffers are a legitimate TRAINING
           data structure; nothing is ever deleted).

SGD protocol, matched across arms: plain SGD, fixed lr, N_STEPS_PER_DAY
parameter-update steps per served day (2, matching risp.Specialist.learn's
default); minibatch = up to 8 stored days of one episode (risp.ep_sample's
default).  During A5/A6's unpinned competition phase, training happens in
a batch at window close, 1 step per window day -- exactly mirroring
risp.RISPArm._close_window (winner trains with n_steps=1 per day).

All randomness flows through the rng handed in by the driver (99*s + 7,
the E1 convention).  Trunk init draws W1 then W2 in a fixed order, and
heads are zero-init (no draws), so all four arms of a given seed start
from the IDENTICAL trunk.
"""

from __future__ import annotations
import numpy as np

from risp import solve_topk, regret, ep_sample

# ---------------------------------------------------------------------------
# Hyperparameters (fixed in advance; no tuning loop was run -- see the
# driver's config block for the one documented adjustment policy)
# ---------------------------------------------------------------------------
HIDDEN = 32
LR = 0.05                  # fixed SGD learning rate, all arms, all params
N_STEPS_PER_DAY = 2        # matches risp.Specialist.learn default
MINIBATCH_DAYS = 8         # matches risp.ep_sample default
N_HEADS_COMPETITION = 4    # A5/A6 head pool size (= linear N specialists)
WC = 20                    # competition window (risp.RISPArm Wc)
ETA = 0.6                  # EG affinity step (risp.RISPArm eta)
LAM = 0.3                  # niche bonus (risp.RISPArm lam)
PIN_THRESH = 0.95          # pin rule (risp.RISPArm pin_thresh)
BETA = 1.0                 # invariance E_e weight (risp.Specialist beta)
ACTIVATION = "tanh"


def spo_plus_yhat_grad(y_hat: np.ndarray, y: np.ndarray, k: int,
                       w_max: float):
    """SPO+ loss and its gradient w.r.t. y_hat (same algebra as
    risp.spo_plus_loss_grad, predictor-agnostic form)."""
    z_star = solve_topk(y, k, w_max)
    z_alt = solve_topk(2.0 * y_hat - y, k, w_max)
    loss = float((2.0 * y_hat - y) @ z_alt - 2.0 * y_hat @ z_star
                 + y @ z_star)
    g_y = 2.0 * (z_alt - z_star)          # d l / d y_hat
    return loss, g_y


class SharedTrunkMLP:
    """Trunk 20->32->32 (tanh) + n_heads linear heads on the 32-dim rep.

    ~1.8k trunk parameters (20*32+32 + 32*32+32 = 1760) + 33 per head.
    Heads are zero-initialised (matches the linear Specialist's w = 0).
    """

    def __init__(self, d: int, n_heads: int, rng: np.random.Generator,
                 hidden: int = HIDDEN):
        self.d, self.hidden, self.n_heads = d, hidden, n_heads
        self.W1 = rng.normal(0.0, 1.0 / np.sqrt(d), (d, hidden))
        self.b1 = np.zeros(hidden)
        self.W2 = rng.normal(0.0, 1.0 / np.sqrt(hidden), (hidden, hidden))
        self.b2 = np.zeros(hidden)
        self.v = np.zeros((n_heads, hidden))   # head weights
        self.c = np.zeros(n_heads)             # head biases

    def forward(self, X: np.ndarray, h: int):
        Z1 = np.tanh(X @ self.W1 + self.b1)
        Z2 = np.tanh(Z1 @ self.W2 + self.b2)
        y_hat = Z2 @ self.v[h] + self.c[h]
        return y_hat, (X, Z1, Z2)

    def predict(self, X: np.ndarray, h: int) -> np.ndarray:
        return self.forward(X, h)[0]

    def backward(self, cache, h: int, g_y: np.ndarray) -> dict:
        """Gradients of (1/n) * loss w.r.t. all params, given dl/dy_hat.
        The 1/n matches risp's per-observation normalisation
        (grad / max(1, n))."""
        X, Z1, Z2 = cache
        g = g_y / max(1, X.shape[0])
        dv = Z2.T @ g
        dc = float(g.sum())
        dZ2 = np.outer(g, self.v[h])
        dA2 = dZ2 * (1.0 - Z2 * Z2)
        dW2 = Z1.T @ dA2
        db2 = dA2.sum(axis=0)
        dZ1 = dA2 @ self.W2.T
        dA1 = dZ1 * (1.0 - Z1 * Z1)
        dW1 = X.T @ dA1
        db1 = dA1.sum(axis=0)
        return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2,
                "v": dv, "c": dc, "h": h}

    def apply(self, grads: dict, lr: float):
        h = grads["h"]
        self.W1 -= lr * grads["W1"]
        self.b1 -= lr * grads["b1"]
        self.W2 -= lr * grads["W2"]
        self.b2 -= lr * grads["b2"]
        self.v[h] -= lr * grads["v"]
        self.c[h] -= lr * grads["c"]

    @staticmethod
    def combine(grad_list, weights):
        """Weighted sum of grad dicts sharing the same head."""
        out = {k: None for k in ("W1", "b1", "W2", "b2", "v", "c")}
        h = grad_list[0]["h"]
        for g, w in zip(grad_list, weights):
            assert g["h"] == h
            for k in out:
                out[k] = (w * g[k]) if out[k] is None else (out[k] + w * g[k])
        out["h"] = h
        return out


class GrowingBuffer:
    """regime -> episode -> [(X, y), ...].  APPEND-ONLY: nothing is ever
    deleted or capped (prereg: 'NO buffer deletion').  Contrast with
    risp.Specialist (buf_days=40, buf_episodes=6 caps): those caps are a
    forgetting knob and are therefore banned here."""

    def __init__(self):
        self.buf: dict[int, dict[int, list]] = {}

    def store(self, X, y, r: int, e: int):
        self.buf.setdefault(r, {}).setdefault(e, []).append((X, y))

    def episodes(self, r: int) -> dict:
        return self.buf.get(r, {})


class MLPArmBase:
    """Shared machinery: SPO+ SGD steps (ERM or invariance) on the active
    regime's episode buffer, routed through a chosen head."""

    name = "mlp-base"

    def __init__(self, cfg, rng, n_heads: int, mode: str = "erm",
                 beta: float = BETA, lr: float = LR,
                 n_steps: int = N_STEPS_PER_DAY):
        self.rng = rng
        self.k, self.w_max = cfg.k, cfg.w_max
        self.mode, self.beta, self.lr, self.n_steps = mode, beta, lr, n_steps
        self.net = SharedTrunkMLP(cfg.d, n_heads, rng)
        self.buffer = GrowingBuffer()

    # -- one parameter-update step on regime r's buffer through head h --
    def _step(self, h: int, r: int):
        eps = self.buffer.episodes(r)
        if not eps:
            return
        if self.mode == "erm" or len(eps) < 2:
            keys = list(eps.keys())
            ekey = keys[int(self.rng.integers(len(keys)))]
            Xb, yb = ep_sample(eps[ekey], self.rng, m=MINIBATCH_DAYS)
            y_hat, cache = self.net.forward(Xb, h)
            _, g_y = spo_plus_yhat_grad(y_hat, yb, self.k, self.w_max)
            self.net.apply(self.net.backward(cache, h, g_y), self.lr)
        else:
            # invariance: Var_e[lbar_e] + beta * E_e[lbar_e]
            # (same estimator as risp.Specialist.learn, inv branch; here the
            #  variance spans ALL stored episodes because nothing is capped)
            losses, grads = [], []
            for ekey in eps:
                Xb, yb = ep_sample(eps[ekey], self.rng, m=MINIBATCH_DAYS)
                y_hat, cache = self.net.forward(Xb, h)
                l, g_y = spo_plus_yhat_grad(y_hat, yb, self.k, self.w_max)
                losses.append(l / max(1, Xb.shape[0]))
                grads.append(self.net.backward(cache, h, g_y))
            E = len(losses)
            lbar = float(np.mean(losses))
            wts = [(2.0 * (l - lbar) + self.beta) / E for l in losses]
            self.net.apply(self.net.combine(grads, wts), self.lr)

    def _learn_day(self, X, y, r: int, e: int, h: int, n_steps=None):
        self.buffer.store(X, y, r, e)
        for _ in range(self.n_steps if n_steps is None else n_steps):
            self._step(h, r)


class A1MLP(MLPArmBase):
    """A1-mlp: one trunk + ONE head trained on everything.  No regime
    routing anywhere; the regime label r is ignored except for buffer
    bookkeeping (which episode the day belongs to)."""

    name = "A1-mlp"

    def __init__(self, cfg, rng, **kw):
        super().__init__(cfg, rng, n_heads=1, mode="erm", **kw)

    def decide(self, X, r):
        return self.net.predict(X, 0)

    def observe(self, X, y, r, e, served_regret):
        self._learn_day(X, y, r, e, h=0)


class A9MLP(MLPArmBase):
    """A9-mlp: oracle -- one linear head per regime, pinned by the TRUE
    regime label; the shared trunk receives gradients from whichever head
    is active.  This is the arm whose dormant-regime readout is protected;
    any deficit A1 shows relative to A9 must come from interference."""

    name = "A9-mlp"

    def __init__(self, cfg, rng, **kw):
        super().__init__(cfg, rng, n_heads=cfg.R, mode="erm", **kw)

    def decide(self, X, r):
        return self.net.predict(X, int(r))

    def observe(self, X, y, r, e, served_regret):
        self._learn_day(X, y, r, e, h=int(r))


class CompetitionMLP(MLPArmBase):
    """A5-mlp (mode='erm') / A6-mlp (mode='inv'): emergent head-regime
    assignment via risp.RISPArm's batched winner-take-all competition,
    ported to N heads on the shared trunk.

    Faithful to RISPArm: per-day window bookkeeping of every candidate's
    decision regret; at window close (Wc in-regime days or a regime
    switch), winner = argmax of [-mean window regret + lam*(alpha[:,r] -
    1/R)]; EG update alpha[i*,r] *= exp(eta) then row-normalise; the
    winner trains on the window's data (1 step per window day); a regime
    pins to the current winner once alpha[i*, r] >= pin_thresh; pinned
    regimes get owner-only daily training (n_steps/day).

    Documented simplifications vs the linear RISPArm (unavoidable /
    deliberate under the shared-trunk architecture):
      (1) Competitors are N heads on ONE shared trunk, not N independent
          capacity-K Specialists.  Capacity K and head eviction do not
          exist here by design (prereg: NO eviction model).
      (2) The training buffer is a single arm-level append-only store
          shared by all heads, not per-specialist private buffers (with a
          shared trunk there is no per-competitor state to attach a
          private buffer to).  Losers' window data therefore remains
          available to whichever head later trains on that regime.
      (3) predict() for a head that has never trained returns the
          zero-head output (empty portfolio) rather than risp's 1e-6
          random tie-break noise.
    The competition dynamics themselves (window statistic, scoring, EG
    step, pin rule, constants Wc/eta/lam/pin_thresh, and the
    1-step-per-window-day winner training) are unchanged."""

    def __init__(self, cfg, rng, mode="erm", N=N_HEADS_COMPETITION,
                 Wc=WC, eta=ETA, lam=LAM, pin_thresh=PIN_THRESH, **kw):
        super().__init__(cfg, rng, n_heads=N, mode=mode, **kw)
        self.R, self.N = cfg.R, N
        self.alpha = np.full((N, cfg.R), 1.0 / cfg.R)
        self.Wc, self.eta, self.lam, self.pin_thresh = Wc, eta, lam, pin_thresh
        self.pinned: dict[int, int] = {}
        self.win_quality = np.zeros(N)
        self.win_days = 0
        self.win_regime = None
        self.win_data: list = []
        self.name = "A5-mlp" if mode == "erm" else "A6-mlp"

    def _owner(self, r):
        if r in self.pinned:
            return self.pinned[r]
        return int(np.argmax(self.alpha[:, r]))

    def decide(self, X, r):
        return self.net.predict(X, self._owner(r))

    def _close_window(self):
        if self.win_days == 0 or self.win_regime is None:
            return
        r = self.win_regime
        score = -self.win_quality / self.win_days \
            + self.lam * (self.alpha[:, r] - 1.0 / self.R)
        i_star = int(np.argmax(score))
        a = self.alpha[i_star].copy()
        a[r] *= np.exp(self.eta)
        self.alpha[i_star] = a / a.sum()
        # winner trains on the window's data, 1 step per window day
        # (mirrors risp.RISPArm._close_window -> learn(..., n_steps=1))
        for (X, y, e) in self.win_data:
            self._learn_day(X, y, r, e, h=i_star, n_steps=1)
        if r not in self.pinned and self.alpha[i_star, r] >= self.pin_thresh:
            self.pinned[r] = i_star
        self.win_quality = np.zeros(self.N)
        self.win_days = 0
        self.win_data = []

    def observe(self, X, y, r, e, served_regret):
        if r in self.pinned:
            self._learn_day(X, y, r, e, h=self.pinned[r])
            return
        if self.win_regime is not None and r != self.win_regime:
            self._close_window()
        self.win_regime = r
        for i in range(self.N):
            self.win_quality[i] += regret(self.net.predict(X, i), y,
                                          self.k, self.w_max)
        self.win_data.append((X, y, e))
        self.win_days += 1
        if self.win_days >= self.Wc:
            self._close_window()


MLP_ARM_FACTORIES = {
    "A1-mlp": lambda cfg, rng: A1MLP(cfg, rng),
    "A5-mlp": lambda cfg, rng: CompetitionMLP(cfg, rng, mode="erm"),
    "A6-mlp": lambda cfg, rng: CompetitionMLP(cfg, rng, mode="inv"),
    "A9-mlp": lambda cfg, rng: A9MLP(cfg, rng),
}
