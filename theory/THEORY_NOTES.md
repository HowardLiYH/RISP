# RISP Theory Notes (feeding main.tex §4, Explainer §Principle, Deep Dive Part on theory)

All statements are at the level of rigor of GAUSE's theory section: idealized-model
propositions with explicit assumptions, full proofs where the structure permits, and
explicit scope-honesty remarks. No adversarial-regret claims for the coupled
winner-take-all dynamics.

---

## 1. Setup and notation

- Stream t = 1..T; features x_t ∈ X, coefficient vector y_t ∈ Y ⊂ R^n (next-period
  returns), latent regime r_t ∈ [R]. Returns bounded: ‖y‖_∞ ≤ y_max.
- **Episodes.** The e-th maximal active spell of regime r is environment (r,e) with law
  P_{r,e} on X × Y. E_r = number of historical episodes of r available at time t.
- **Decision layer.** Feasible set Z = {z ∈ [0, w_max]^n : Σz_i ≤ W, ‖z‖₀ ≤ k},
  utility F(z,y) = yᵀz (linear). Optimal decision z*(y) = argmax_{z∈Z} yᵀz: put w_max
  on the k largest positive coordinates of y (truncate at the budget). A plug-in policy
  is z(ŷ) = z*(ŷ).
- **Decision regret.** ρ(ŷ; y) = F(z*(y), y) − F(z(ŷ), y) ∈ [0, B] with
  B = 2·k·w_max·y_max (crude but sufficient bound on the regret range; in fact
  ρ ≤ k·w_max·(max y − min y) ≤ 2k·w_max·y_max).
- **Episode risk.** For hypothesis q : X → Y (a regime head),
  L_{r,e}(q) = E_{(x,y)~P_{r,e}}[ρ(q(x); y)].
- **Hyper-distribution assumption (A1, episode exchangeability).** For each regime r,
  episodes are i.i.d. draws ξ_{r,1}, ξ_{r,2}, ... ~ Q_r from a regime-level
  hyper-distribution over environments; the deployed/test episode e' is a fresh draw.
  (This is the regime-indexed version of Inv-PnCO Assumption 1: the regime's
  decision-relevant structure is stable across episodes; what varies between episodes
  is itself i.i.d. "weather.") Define for fixed q:
  μ_r(q) = E_{ξ~Q_r}[L_ξ(q)],  σ_r²(q) = Var_{ξ~Q_r}[L_ξ(q)].

**Remark (honesty).** A1 is an idealization on two counts: real episodes are neither
independent (macro memory) nor exchangeable (secular drift), and E_r is small (5–7 for
crisis regimes). We use A1 exactly as Inv-PnCO uses its Assumption 1 — as the formal
expression of "the next crisis is a new draw from the crisis distribution" — and we
mitigate small E_r by sub-episode blocks and cross-asset episodes in the experiments.

---

## 2. Lemma 1 (episode transfer / invariance gap)

**Statement.** Under A1, for any fixed q and any δ ∈ (0,1], with probability ≥ 1−δ over
the draw of the test episode e' ~ Q_r,
    L_{r,e'}(q) ≤ μ_r(q) + σ_r(q)/√δ.
Consequently in expectation, E_{e'}[L_{r,e'}(q)] = μ_r(q), and the δ-quantile excess
over the mean is controlled exactly by σ_r(q).

**Proof.** One-sided Chebyshev (Cantelli): for any λ>0,
Pr[L_ξ(q) − μ_r(q) ≥ λ] ≤ σ_r²/(σ_r² + λ²) ≤ σ_r²/λ². Set λ = σ_r/√δ. ∎

(Use Cantelli in the papers for the slightly sharper σ√((1−δ)/δ) form; state the
simple Chebyshev form in main.tex, the Cantelli refinement in the Deep Dive.)

**Finite-episode estimation (Lemma 1').** The learner sees only the empirical
μ̂_r(q) = (1/E_r)Σ_e L_{r,e}(q) and σ̂_r²(q) (and only finitely many samples per
episode). Since L ∈ [0,B]: with probability ≥ 1−δ over the training episodes (q fixed,
i.e., before uniform-convergence considerations),
  |μ̂_r(q) − μ_r(q)| ≤ B·√(log(2/δ)/(2E_r))    (Hoeffding over episodes)
and a corresponding √(1/E_r) bound holds for the standard deviation via, e.g.,
Maurer–Pontil empirical-Bernstein. The papers state the population result as the
proposition and carry the O(B/√E_r) estimation term explicitly as the price of few
episodes — this is precisely why crisis regimes (E_r ≈ 5–7) need the sub-episode and
cross-asset mitigations. A uniform-over-q version costs the usual complexity term; we
do not need it for the mechanism claim and say so (scope honesty: the trained q̂
depends on the training episodes, so the plug-in application of Lemma 1' is heuristic
at the same register as Inv-PnCO's use of its Theorem 1).

**Why minimizing Var_e + β·E_e targets exactly this bound.** The RISP training
objective per regime is min_q σ̂_r²(q) + β·μ̂_r(q) (SPO+ surrogate for ρ inside each
episode risk). Up to the estimation terms above, this is a Lagrangian scalarization
sweeping the (μ_r, σ_r) Pareto frontier: the bound in Lemma 1 is monotone in both
arguments, so for each δ there is a β(δ) whose minimizer optimizes the bound. β ≈
trades mean for tail-robustness across episodes. (Deep Dive: include the standard
counterexample showing ERM (β→∞ equivalent, variance ignored) can have larger
μ + σ/√δ — the spurious-feature construction of §6 of the notes.)

---

## 3. Lemma 2 (KL→regret bridge; the "known technical gap" of the roadmap)

Inv-PnCO-style invariance statements bound divergences between solution distributions,
not regret. We bridge in two steps.

**Statement.** For any two episode laws P, P' on X×Y and any measurable q,
  |L_P(q) − L_{P'}(q)| ≤ B · TV(P, P') ≤ B · √(KL(P‖P')/2).

**Proof.** ρ(q(x); y) ∈ [0,B] pointwise, so the difference of expectations of a
[0,B]-valued function under P, P' is at most B·TV by the variational characterization
TV(P,P') = sup_{0≤g≤1} |E_P g − E_{P'} g| applied to g = ρ/B. Pinsker gives
TV ≤ √(KL/2). ∎

**Corollary (regret form of an invariance premise).** If a representation Φ renders
episode laws ε-invariant in KL — KL(P_{r,e}(·|Φ) ‖ P̄_r(·|Φ)) ≤ ε for all e — and q
factors through Φ, then sup_e |L_{r,e}(q) − L̄_r(q)| ≤ B√(ε/2); in particular
σ_r(q) ≤ B√(ε/2) ≤ B√ε. So a KL-invariance guarantee *implies* a small variance
penalty, and Lemma 1 applies with σ_r ≤ B√(ε/2). This is the constant-explicit bridge:
the price of moving from the KL metric to the regret metric is exactly the factor
B/√2, i.e., the regret range. (Fallback per roadmap: if a referee objects to B being
loose, the decomposition statement survives verbatim in the KL metric.)

**Remark (constants).** B = 2k·w_max·y_max. With k=5, w_max=0.2, daily |returns| ≤ 20%
⇒ B = 0.4 (40% of capital per day) — loose but explicit; empirical regret ranges are
~50× smaller, stated in the audit.

---

## 4. Lemma 3 + Prop 2 (forgetting deficit; reward-independence zeroes it)

**Memory models.** Specialist i holds at most K regime-heads.
- Hard (LRU): a foreign update to a non-held regime when full evicts the
  least-recently-used head (reset to prior). Retention of r's head is binary.
- Soft (interference): shared backbone, per-regime adapters; each foreign update decays
  untouched adapters' effective knowledge by factor (1−ρ_int).

**Dormancy process (A2).** Regime r dormant on an interval of length D. During
dormancy, the allocation mechanism A routes learning updates; let U_D = number of
*distinct* non-held foreign regimes the owner of r is made to learn during the
interval. Under a reward-driven A, each dormant step makes the owner learn an active
foreign regime with probability ≥ p > 0 (it is selected/allocated by current reward,
which only active regimes emit).

**Lemma 3 (eviction rate).** Hard model, reward-driven A: r's head is evicted once
U_D ≥ K. The waiting time to accumulate K distinct foreign regimes is a sum of K
geometric variables; hence
  Pr[retained after D] = Pr[U_D < K] ≤ exp(−c_p (D − K/p)₊)-type tail; the clean form
  used in the paper: if each dormant step independently hits a uniformly-drawn active
  regime from a window of W_a ≥ K distinct active regimes with prob p, then
  Pr[U_D < K] ≤ Pr[Binom(D, p·(W_a−K+1)/W_a) < K] → 0 exponentially in D.
  (Paper states the limit + exponential rate; Deep Dive carries the coupon-collector
  computation in full.)

**Prop 2 (dichotomy).**
(i) Reward-driven A: E[relearn cost at reactivation] = Pr[U_D ≥ K]·C_relearn → C_relearn
as D → ∞ (hard); soft: cost ∝ 1 − (1−ρ_int)^{N_D} where N_D = number of foreign
updates, → full cost.
(ii) Any A independent of the realized reward process (pinned converged competition,
random fixed niches, frozen gate, hand-designed silos): the owner of r receives zero
foreign updates during dormancy ⇒ U_D = 0 deterministically ⇒ retention exact (hard)
or bounded by the regime's own drift (soft, no decay from foreign updates by
construction). Φ(D; A) ≡ 0 for all D.
**Proof.** (i) Lemma 3 + LRU definition; soft case immediate from per-update decay.
(ii) By definition of reward-independence + one-owner-per-regime coverage, the dormant
owner is never the argmax of any current-reward allocation it doesn't already hold...
more precisely: the assignment map is measurable w.r.t. information independent of the
realized reward stream, and at convergence assigns r's owner only regime r (K≥ slots
for its niche set); during r's dormancy the owner receives no updates at all. ∎

**Coverage caveat (carried from GAUSE).** Reward-independence is necessary within the
assignment-only protection class; reward-independence + persistent coverage is
sufficient. Random fixed niches can leave r unowned (coverage gap): retention holds
only for covered regimes. RISP's WTA competition guarantees coverage at N ≥ R
(GAUSE coverage result imported as corroborated premise, re-verified empirically here).

**C_relearn.** Under the probe-window metric, C_relearn = (1/N_probe)·Σ_{first N_probe
days} E[ρ_t(fresh head)] − μ_r(q̂) — the regret excess of a from-prior head over a
retained head, integrated over the probe window. Measured directly in E1 (relearning
half-life). The paper treats C_relearn as an empirical constant, not a theorem.

---

## 5. Prop 1 (decomposition) and Prop 3 (additivity / the 2×2)

**Prop 1 (register fixed 2026-07-14; matches the paper).** The previous statement
mixed registers: it bounded E[Regret_react] while injecting Lemma 1's Cantelli
*quantile* term σ_r/√δ into the expectation — type-inconsistent (the σ-term is a
tail object; in expectation it vanishes). Fixed statement at fixed tail level
δ ∈ (0,1]: CVaR over the fresh episode draw e′, expectation over the
allocation/eviction randomness:
  E_A[ CVaR_δ^{e′}[Regret_react(r)] ] ≤ G_inv(δ) + G_forget
  G_inv(δ) = μ_r(q̂_r) + σ_r(q̂_r)·√((1−δ)/δ) + O(B/√E_r),
  G_forget  = Φ(D;A)·C_relearn.
At δ = 1 this specializes to E[Regret_react] ≤ μ_r + O(B/√E_r) + G_forget: the
σ-term vanishes and the population-level bound is minimized by the mean-optimal
(ERM) head. Interpretation: allocation controls the *mean* of the reactivation
transient; the invariance objective controls its *tail* across episode draws.
**Eviction-branch bookkeeping (also fixed):** C_relearn is an EXCESS over the
converged retained benchmark, so the eviction branch's regret is
(retained benchmark + C_relearn), not C_relearn alone; the pointwise accounting is
  Regret_react(r) ≤ L_{r,e′}(q̂_r) + 1{evict}·C_relearn.
**Proof.** Pointwise accounting inequality above; the eviction event is a function of
the dormancy-period allocation stream, independent of e′ under A1. Conditional on the
event, apply the CVaR form of Cantelli (CVaR_δ[X] ≤ μ + σ√((1−δ)/δ) for any X with
mean μ, variance σ² — same one-sided moment argument as Lemma 1's quantile version)
plus Lemma 1's estimation terms to the first term; the second term is constant given
the event. Take E over the indicator: E[1{evict}] = Φ(D;A) from Lemma 3/Prop 2. ∎

**Prop 3 (independent controls; additive bound).** G_forget depends only on (A, D, K,
memory model) and is zeroed by reward-independent assignment (Prop 2(ii)) regardless
of the training objective; G_inv depends only on (training objective, Q_r, E_r) and is
optimized by the variance-penalized objective (Lemma 1 discussion) regardless of the
assignment mechanism. Hence the upper bound is additive in the two design axes, and
the predicted 2×2 is monotone in each axis. **Honest register:** additivity of the
*bound* does not force additivity of realized regret; the empirical interaction index
I = (A1−A5) + (A1−A7) − (A1−A6) is measured in E1 and reported.

---

## 6. Why ERM fails across episodes (the construction used in E4 + Deep Dive worked example)

Two-feature linear construction. In regime r, episode e: invariant feature x_inv with
y = θ·x_inv + noise stable across episodes; spurious feature x_sp with y-correlation
γ_e flipping sign/magnitude across episodes (E[γ_e] small, Var[γ_e] large). ERM pooled
over training episodes loads on x_sp in proportion to the *pooled* correlation (which
is nonzero in-sample with few episodes); per-episode losses then vary strongly
(σ_r large), and the unseen episode draws a fresh γ_{e'} ⇒ excess regret σ-sized.
The variance penalty forces the weight on x_sp toward 0 (its contribution to
Var_e[L_e] scales with Var[γ_e]·w_sp²-order terms), recovering the invariant
predictor at an O(β) mean-loss price. Full computation with explicit Gaussians in the
Deep Dive (worked example with numbers); the same construction drives the E4 synthetic
generator, so theory and experiment use one object.

## 7. Prop 4 (break-even dormancy)

Carrying cost c per idle specialist-day (infra/attention/calibration ops). Over a
dormancy spell D + probe window: retained specialist costs c·D; reward-driven arm
saves the carrying cost but pays Φ(D;A)·C_relearn·N_probe-scaled regret at
reactivation. Retention pays iff
  c·D ≤ Pr[U_D ≥ K]·C_relearn·N_probe·V
(V = capital-scaling of one unit of probe regret). Hard-model closed form with the
Lemma 3 rate; since Pr[U_D≥K] saturates at 1 while c·D grows linearly, there is a
finite window [D_min, D_max]: dormancy long enough that eviction is near-certain but
not so long that carrying costs swamp the one-shot saving. D* solved numerically in
E3; the *existence of an upper break-even* is the honest, non-obvious part (idle desks
are not free — roadmap C5).

## 8. Convergence/coverage remark (imported from GAUSE, restated for batched windows)

Batched WTA with window W_c: the winner statistic is a W_c-sample mean of within-regime
regret differences, so the probability the *wrong* specialist wins a window decays as
exp(−W_c·Δ²/2σ_n²) (sub-Gaussian noise σ_n, competence gap Δ) — the formal reason
per-step competition (W_c=1) converges to noise on financial data and batching is the
domain adaptation. Stated as a remark with proof sketch (Hoeffding), feeding the W_c
ablation E5.
