# CHANGELOG

## Research Journey: Regime-Invariant Specialist Pools

This document chronicles the project from conception (the Idea-1 roadmap,
June 10, 2026) through the v1.0.0 build, in the convention of the GAUSE
companion repository: every revision that changed a claim is recorded,
including the ones that went against us. The framework was briefly named
"NicheMem" during the build; it was renamed to the roadmap's pre-registered
**RISP** (Regime-Invariant Specialist Pools) on the author's decision before
release. Identifiers in archived result files were renamed accordingly
(labels only — no number changed).

---

## v1.0.0 — The Two-Axis Build: Retention x Invariance

**Date**: 2026-06-11
**Scope**: Full first iteration — theory with complete proofs, an eleven-arm
experimental battery (E0–E6, 20 seeds, Welch + Holm), three papers
(`paper/main.pdf` 19pp, `paper/RISP Explainer.pdf` 18pp, `paper/Deep
Dive.pdf` 80pp), and a self-contained reproducible codebase (numpy-only,
laptop-scale, every paper number traced to `results/*.json`).

### Headline results (`results/e1_synth.json`)

| arm | post-react regret | class |
|---|---|---|
| A10 oracle assignment + INV (skyline) | 0.0305 ± 0.0008 | skyline |
| **A6 RISP-full (ours)** | **0.0307 ± 0.0007** | reward-indep. + INV |
| A9 oracle assignment + ERM | 0.0321 ± 0.0008 | skyline (ERM) |
| A5 RISP-ERM | 0.0321 ± 0.0007 | reward-indep. |
| A4 random fixed niches | 0.0330 ± 0.0013 | reward-indep. (gaps) |
| A2 MoE router | 0.0341 ± 0.0011 | reward-driven |
| A8b Hedge over learning experts | 0.0341 ± 0.0010 | reward-driven |
| A1 monolith (ERM) | 0.0342 ± 0.0010 | reward-driven |
| A7 monolith (INV) | 0.0344 ± 0.0010 | reward-driven + INV |
| A3 recent-performance allocator | 0.0378 ± 0.0010 | reward-driven |
| A8a Hedge over fixed strategies | 0.0439 ± 0.0009 | static |

Retention axis −6.1% (p=1.3e−3), invariance axis −4.4% (p=6.1e−3), joint
−10.3% (p=9.2e−7; 38% of excess over the noise floor). **The signature
prediction confirmed:** invariant training is inert inside a reward-driven
monolith (A7 vs A1, p=0.88) — super-additive interaction −0.0015 ± 0.0005
per seed (CI excludes 0). RISP-full is statistically indistinguishable from
the hand-pinned oracle skyline with the same objective (p=0.72).

### The honest record (not spun)

1. **The first prototype refuted itself — and became experiment E6.** At the
   initial (unrealistically high) synthetic signal-to-noise, *no arm
   separated from any other*: a fresh learner refit an evicted regime within
   2–5 days and retention was demonstrably worthless. Rather than tune the
   failure away silently, the SNR axis was promoted to a pre-registered
   audit: at 0.5–2x realistic SNR the mechanism pays (+7–10%); at 4–8x it
   **inverts** (−13% to −49%) — greedy episode-chasing beats invariant
   retention where signal is strong and fast to fit, and the oracle skyline
   inverts identically (it is the regime, not the mechanism). The deployment
   boundary is a measured crossover near 2–3x.
2. **The real-data structure gate FAILED, and we shipped the null.** E0
   (oracle regime-conditioning vs block-shuffled labels, decision metric,
   two causal labelers) finds no exploitable regime structure in 5-pair
   daily crypto or 3-commodity panels (all |z| < 0.7). The 11-arm experiment
   on regime-stitched real crypto is consequently flat (all p > 0.2) —
   exactly what the failed gate predicts. The real-data contribution of
   v1.0.0 is therefore the *diagnostic-first protocol*, not a market result;
   the pre-registered equities flagship (CRSP S&P 500, 7 crisis episodes) is
   the open test.
3. **The batching prediction was REFUTED by its own ablation.** Pre-
   registered: per-step competition converges to noise at market SNR, hence
   20-day windows. Measured: flat across W_c ∈ {1,5,20,60} (0.0303–0.0309),
   W_c=1 marginally best — the EG affinity accumulation across windows does
   the averaging the single-window Hoeffding analysis attributed to
   batching. The corrected mechanism story is in all three papers.
4. **Variance-only control collapses, as theory predicts.** β=0 gives
   0.0356 — worse than retained ERM (0.0321): a uniformly bad head has zero
   episode-variance. The objective needs both terms; plateau β ∈ [0.25, 4].
5. **The crisis regime never formally pins.** Across 20/20 seeds the
   assignment is covering and one-per-regime, but the rare regime's owner
   reaches affinity only 0.67–0.87 (too few competition windows). Ownership
   is stable throughout; deployments should pin on ownership stability, not
   the affinity scalar. (An earlier 4-seed check reported 0.79–0.87; the
   20-seed range is wider and the papers carry the corrected number.)

### Mid-build corrections (recorded, not hidden)

- **Soft memory model fixed and rerun.** The initial "soft" implementation
  still evicted at capacity (decay merely added on top), making K=1 soft
  byte-identical to hard — caught by the Part-V audit. Corrected to the
  GAUSE-style no-eviction, overflow-scaled interference model and E2-soft
  rerun: reward-driven arms are now flat at ~0.0328 at *every* K — under
  shared representations the gap to RISP (0.0307) never closes at any
  capacity. Hard-model numbers reproduced identically.
- **E4 slope claim corrected.** ERM degrades ~23% faster than the invariant
  objective with heterogeneity (not "2x the slope"); the 2.4x figure is the
  growth of the ERM−INV *gap* (0.0010 → 0.0024). Both papers fixed.
- **β=16 reading corrected.** Large β is not "clean ERM recovered" but an
  unstably large effective step (0.0352, worse than A5 at 0.0321); A5
  remains the proper β→∞ reference.

### Theory shipped (full proofs in `paper/Deep Dive.pdf`)

Post-reactivation regret decomposition (invariance gap + forgetting
deficit); Cantelli episode-transfer with explicit O(B/√E_r) estimation price
for few episodes; eviction-rate dichotomy (coupon-collector; reward-
independence + coverage ⇒ deficit ≡ 0); the **KL→regret Pinsker bridge**
(closing the roadmap's flagged gap, constant B = 2k·w_max·y_max, stated
loose); break-even dormancy (retention pays only in a *window* of dormancy
lengths; above ~15% relative carrying cost, never). Scope honesty: no
adversarial-regret or convergence theorem is claimed for the coupled
winner-take-all dynamics — convergence is demonstrated (20/20), not proven.

### Pre-registered next steps

WRDS/CRSP equities panel (E0 gate decides framing); intraday-crypto E0
re-run; hard combinatorial decision layers (knapsack, scheduling);
staleness trigger for the E6 inversion; Inv-PnCO theory-coauthor decision
(Jul 1); risk-model-committee pivot (roadmap F3) if trading-side dormancy
proves too short.
