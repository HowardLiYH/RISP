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
lengths; above ~25% relative carrying cost, never — corrected from ~15% in
v1.0.1, see below). Scope honesty: no
adversarial-regret or convergence theorem is claimed for the coupled
winner-take-all dynamics — convergence is demonstrated (20/20), not proven.

### Pre-registered next steps

WRDS/CRSP equities panel (E0 gate decides framing); intraday-crypto E0
re-run; hard combinatorial decision layers (knapsack, scheduling);
staleness trigger for the E6 inversion; Inv-PnCO theory-coauthor decision
(Jul 1); risk-model-committee pivot (roadmap F3) if trading-side dormancy
proves too short.

---

## v1.0.1 — E1s reporting integrity fix

**Date**: 2026-07-14

- **A8a range exclusion corrected (integrity bug).** `main.tex` quoted the
  E1s post-reactivation band as 0.0134–0.0141, which silently excluded
  A8a-Hedge-fixed at 0.01325 — the numerically *best* arm on the stitched
  real-data null, and a no-learning baseline. The pre-registered test
  family contains no A8a comparisons, so no statistic was wrong, but the
  quoted range hid the fact that a baseline that learns nothing edged out
  every learning arm. Both `main.tex` and the Explainer now quote the full
  band (0.0132–0.0141), name A8a as the numerically lowest arm, and scope
  the "every pairwise p > 0.2" claim to the pre-registered family. The
  Deep Dive (Table in Part V) already reported this correctly and needed
  no change.
- **Arm-count wording fixed.** E1s ran ten arms (A10 oracle-INV requires
  generator access and is undefined on real data); `main.tex` and the
  Explainer said "eleven-arm" in the E1s sections. Corrected.
- **Break-even dormancy endpoints corrected (found by full number re-audit,
  2026-07-14).** `main.tex` §E3 quoted the retention window as [~40, ~6,000]
  days at 1% carrying cost, [~60, ~600] at 10%, vanishing above ~15% — all
  three numbers a consistent 4× off, as if N_p = 60 had been used instead of
  the paper's probe window N_p = 15. Correct values from the proposition's
  own inequality (f·D ≤ Φ(D)·N_p): D_max = N_p/f = 1,500 days at 1%, 150 at
  10%; threshold f* = N_p·max_D Φ(D)/D ≈ 27% on the measured E3 grid (~25–30%).
  The Deep Dive's worked example already had 1,500/150 but repeated the 15%
  threshold; the Explainer had 600 and 15%. All three documents now agree.
  Qualitative conclusion (a *window* exists; idle desks are not free)
  unchanged; the practical bite is 4× sharper — at 10% carrying cost the
  window is tighter than one crisis cycle.
- **Eight minor rounding/wording fixes** from the same audit (Table 1 cells
  0.0330→0.0329, ±0.0010→±0.0009, 0.0344→0.0343, ±0.0006→±0.0005; "twice the
  seed variance"→"1.8× the seed standard deviation"; E3 gap band
  0.0038–0.0044→0.0038–0.0041; E2 soft-vs-hard parenthetical made exact;
  E4 "23% slower"→"19% slower (ERM 23% faster)"). Abstract, E1 body, E0,
  E1s, E2, E5, E6 and all config counts verified clean against the JSONs.

---

## v1.1.0-dev — The intraday retest: first real-data gate pass, and the second gate

**Date**: 2026-07-14 (results in repo; papers not yet updated)

New experiments (all pre-registered in module docstrings before results):

1. **E0-intraday** (`code/e0_intraday.py` → `results/e0_intraday.json`):
   the roadmap's "re-run the gate where it might pass" item. 10 cells:
   {1D, 4H, 1H} × {L1, L2} × {bar-native, wall-clock windows}, rich
   10-feature OHLCV inventory (Parkinson vol, volume z, reversal, mom100,
   cross-sectional rank). Findings: rich features do NOT rescue the daily
   gate (feature axis not binding); all wall-clock cells fail; two
   bar-native cells pass the screen.
2. **Confirmation pass** (`code/e0_intraday_confirm.py` →
   `results/e0_intraday_confirm.json`; criteria fixed before the screen
   finished: 50 fresh shuffles, z>2, one-sided p<0.005, split-half
   stability): **4H/L2b CONFIRMED** — gap +3.15%, z=+2.32, p<1e-4,
   halves +3.42%/+2.92%, 951 episodes. First real-data structure pass on
   the decision metric in this project (or GAUSE). 1H/L1b failed (z=1.76);
   reported as screen-only.
3. **E1r-4H** (`code/e1r_4h.py` → `results/e1r_4h_crypto.json`): ten-arm
   dissociation on the confirmed substrate, stitched dormancy schedules,
   20 seeds. Pre-registered prediction (gate passed → arms should
   separate) **REFUTED**: flat table, all pre-registered pairs p>0.57.
   The decomposition localizes why: post-reactivation elevation (~+7%) is
   identical for A9 oracle-pinned, so the forgetting deficit A1−A9 ≈ 0
   (synthetic: 0.0021) — regime structure exists (gate 1) but dormancy
   causes no forgetting damage (gate 2 fails). A8a no-learning flips from
   best (E1s, failed gate) to worst (E1r, passed gate): learning pays,
   retention has nothing to save.

**Emergent contribution:** the E0 gate is necessary but not sufficient;
the deployment protocol becomes **two-gate** (structure on the decision
metric; nonzero measured forgetting deficit via the A1-vs-A9
counterfactual). Real data now instantiates three cells of the
precondition 2×2, each null predicted in advance. The equities panel
targets the fourth.
- **Staleness trigger (E6 remedy) attempted — honest outcome: not a fix.**
  Additive arm A6t (unpin + re-open competition on confident pinned-owner
  underperformance; conservative defaults; byte-identical e1 regression
  check) swept over the E6 SNR grid at 20 seeds
  (`results/e6_trigger.json`). Result: no cost at low SNR (A6t ≈ A6,
  p>0.93), a directional ~15% recovery of the high-SNR *steady-state*
  pathology (8×: 0.0351 vs 0.0412, p=0.070; 4×: 0.0233 vs 0.0258,
  p=0.096), and NO repair of the post-reactivation inversion (nominally
  worse, n.s.). The E6 deployment boundary stands; the trigger is recorded
  as an attempted remedy, not adopted into the headline mechanism.
- **100-seed promotion (2026-07-14).** The E1–E6 battery (incl. the
  stitched E1s) replicated at 100 seeds (`results_100seed/*.json`; seeds
  0–19 identical to the 20-seed run by construction) and promoted to
  primary in `paper/main.tex`; figures regenerated from the 100-seed JSONs
  via `code/make_figures_100seed.py` (fig7_trace self-simulates and is
  unchanged). Headline shifts: retention axis −6.1% → **−4.3%**
  (p 1.3e−3 → 1.9e−7), invariance axis −4.4% → **−5.0%** (p 6.1e−3 →
  5.8e−9), joint −10.3% → **−9.1%** (p 9.2e−7 → **6.0e−23**; 38% → 36% of
  excess over the noise floor); interaction index −0.0015±0.0005 →
  −0.0017±0.0002; A6 now significantly beats A9 oracle-ERM (p 0.011 →
  1.5e−6); A4 separates from A5 (p 0.28 → 0.011). E1s stays null under
  the pre-registered Holm family (min Holm p = 0.17) with one disclosed
  raw trend (A6 < A1, uncorrected p = 0.028; band 0.0129–0.0136, A8a
  still numerically lowest). E6 inversion deepens: −49.3% → **−60.0%**
  at 8× SNR (crossover still between 2× and 4×). E3 break-even threshold
  f* ≈ 25% → **≈20%** (Φ(21) 0.38 → 0.27, Φ(63) 0.94 → 0.86; window
  endpoints unchanged: ~60–1,500 d at f=1%, ~60–150 d at f=10%).
  Not rerun (kept at true n): E1r-4H, E0-intraday(+confirm), E6-trigger,
  and the 20-seed assignment diagnostic (crisis affinity 0.67–0.87,
  20/20 covering, 3 pinned) — n=20 now stated explicitly in the paper.
- **Internal red-team audit + register repairs (2026-07-14).** A
  multi-perspective internal adversarial audit of the manuscript drove
  five same-day honesty repairs in main.tex: E1r's refuted pre-registered prediction stated plainly; the
  abstract's "each null predicted in advance" corrected (one predicted, one
  retrospectively diagnosed and converted into a falsifiable second gate);
  multiplicity/selection caveats added to the 4H gate pass (10-cell screen,
  14-test family, same-span confirmation, max-selection bias;
  disjoint-period replication committed); "irreducible noise floor" renamed
  to converged invariant-service floor (four ERM arms trade below it at
  steady state); and a new steady-state-tax paragraph charging the
  invariance premium in full (overall margin 2.2% stated alongside the
  probe-window headline). Headline theory items applied next:
  Prop. 3 → CVaR register,
  de-circularized dichotomy, PackNet/HAT/SupSup + Bousquet-Warmuth 2002
  citations, TOST equivalence tests, capacity-accounting re-headline.
- **Tier-1 audit fixes (2026-07-14).** The headline theory/citation items
  from the internal audit, applied to `paper/main.tex` + `references.bib`
  (E0/E1s/E1r sections untouched; being extended separately). (1) Prop. 3
  register fix: the decomposition no longer injects Lemma 1's Cantelli
  quantile term into an expectation — restated at fixed tail level as
  E_A[CVaR_δ over the episode draw] ≤ G_inv(δ) + G_forget with
  G_inv(δ) = μ_r + σ_r·√((1−δ)/δ) + O(B/√E_r); eviction-branch bookkeeping
  made explicit (C_relearn is an excess over the retained benchmark, so the
  branch is benchmark + C_relearn); proof rewritten via the pointwise
  accounting inequality + CVaR-Cantelli; new interpretation paragraph:
  allocation controls the mean of the reactivation transient, the invariance
  objective its tail across episode draws (at δ=1 the σ-term vanishes and
  ERM is mean-optimal — stated honestly). Same fix applied to
  `theory/THEORY_NOTES.md` §5. (2) De-circularized eviction dichotomy:
  operative property renamed *isolated covering assignment* (isolation +
  coverage defined in Assumption 2); new Remark ("Isolation, not
  reward-independence, does the work"): reward-independence is neither
  necessary nor sufficient (round-robin counterexample); Prop 1(ii) now
  zeroes the deficit for any isolated covering assignment, with RISP pinning
  one emergent route; direction (i) carries the disclosed marginal-p
  boundary (a fixating allocator can accidentally retain); abstract/C3/N1/
  synthesis/conclusion wording aligned. (3) Related work: parameter-isolation
  CL passage (PackNet, HAT, SupSup, Expert Gate, PathNet — the CL
  instantiation of isolation; what they lack: allocation-under-competition +
  invariance axis); Fixed-Share/mixing-past-posteriors passage (MPP retains
  the pointer, not the playbook; Herbster–Warmuth 1998, Bousquet–Warmuth
  2002, Blum–Mansour 2007); CP-MoE/StaR-MoE dormancy passage (arXiv
  2605.20247 / 2605.17571); Ang–Bekaert 2002 and Philps et al. 2018 added.
  Bib hygiene: duplicate li2026emergent merged into li2026gause; 30
  never-cited entries deleted (MARL/ecology/QD leftovers; kept
  cesa2006prediction, french1999catastrophic, peters2016causal — cited by
  the Deep Dive/Explainer); 12 web-verified entries added. (4) TOST
  equivalence tests from `results_100seed/e1_synth.json` raw arrays, paired,
  margin ±0.0008 pre-declared as half the smallest confirmed family effect
  (A6−A5 = −0.0016): A6 vs A10 p = 2.6e−12, A7 vs A1 p = 9.6e−29, A2 vs A1
  p = 8.2e−12 — all three ≈-claims now positively established, sentences
  added at each claim site in E1. (5) Capacity-accounting re-headline: E1
  retention axis now leads with A5 vs A2 (identical total capacity, 4×K=2;
  0.0324 vs 0.0339, p = 2.5e−7, Holm 1.5e−6), monolith comparison kept as
  confirmatory with the E2 K=4 caveat (0.0322 ≈ A5's 0.0324); arms paragraph
  gains a capacity-accounting note; abstract phrase "capacity-matched
  monolith" → "monolith with the same per-specialist capacity" with a
  pointer to the E1 accounting. main.tex recompiles clean (0 errors, 0
  undefined references, 22 pp).
- **E1f — the French 49-industry batteries (2026-07-14, pre-registered in
  PREREG_FRENCH49.md before each run).** Gate 1 passes on daily equities
  for the first time (L1: +1.14%, z=3.18, 50 controls, no selection
  caveat); L2 fails; L3 (drawdown labeler) fails gate 1 by the pooled
  sub-criterion only. Gate 2: Γ_forget = 0 again under L1, but
  **+0.00091 ± 0.00020 under L3 — the first positive forgetting deficit
  on real data** (crisis dormancy up to 2,953 trading days). Walk-forward
  dissociations: L1 → significant INVERSION (A1 beats A6, Holm 4.8e-8);
  L3 → **the full pre-registered ordering on real data** (retention Holm
  8.1e-8, invariance Holm 2.5e-4, joint −5.3% Holm 4.1e-12, A6 beats the
  pinned oracle Holm 4.8e-3). The deficit's sign predicted both outcomes;
  gate 1's pooled criterion predicted neither → protocol revised: Γ̂ is
  the binding, single-number deployment rule (revision itself flagged as
  post-hoc; forward test = CRSP). Caveats in text at equal prominence:
  single-history walk-forward, flat stitched counterparts (two candidate
  readings), L3 designed post-A (disclosed), gross of costs. Abstract,
  C4, and new §E1f updated; main.tex recompiled clean.
- **Second internal audit + full reconciliation (2026-07-14, evening).**
  A second adversarial audit of the E1f revision verified all first-round
  theory fixes correct and every E1f number exact against the JSONs, but
  found: the gate-1 p-values SE-register-inflated (t vs shuffle-mean;
  L2 z=0.88 ↔ p=7.5e-8 is the proof), the Bonferroni ×3 sentence false as
  written, zero finance literature cited in E1f, drawdown-threshold
  robustness untested, and five stale self-descriptions from earlier
  drafts. ALL applied same day:
  permutation-register p's (L1 z=3.18, normal-fit ~7e-4; deleted the
  1e-27/1e-21 decorations), corrected ×3 accounting (five primaries
  survive ≤8e-4; L1 inversion sub-claims do not), predicted→tracked tense
  + postdiction framing + Γ-circularity note, A5-vs-A2 headlined in E1f
  and abstract, overall columns added (L3: pool wins overall too; L1:
  wash), labeler-anatomy correction (crisis UNION recurs 1-3yr with
  2010/2011/2015-16/2018 rehearsals in inventory; 2,953d belongs to the
  crisis-up cell), 12 finance/CL citations + positioning paragraph
  (Daniel-Moskowitz, Cooper et al., Pesaran-Timmermann, GEM/replay,
  Lo-MacKinlay aggregation caveat), soft-model isolation redefined (no
  updates other than to r), stats/limitations/synthesis/intro/protocol
  sections reconciled with E1f, two silent Missing-$ errors fixed,
  prereg Addendum B records P5/P7 REFUTED + P6 CONFIRMED.
- **LORO analysis (results/e_french49_L3_loro.json; run_arm gains
  additive collect_react flag, byte-identical regression check).** The
  L3 deficit survives every single-event exclusion (min 0.00071, 78% of
  headline), survives dropping all of 2020 (0.00080±0.00019), and is
  positive-significant within the 2010s (n=14) and 2020s (n=12)
  independently. Not carried by COVID. Reported in E1f caveat (v).
- **Threshold sweep (PREREG C): P8 REFUTED — the L3 deficit is
  specification-fragile.** Exists only at the pre-registered 15% cutoff;
  null at 10/12%; at 20% a third inversion (Γ=−0.00045, monolith beats A6,
  min raw p=4.6e-4). Reported at headline prominence in E1f with both
  readings (artifact warning vs granularity window parallel to Prop 4,
  the latter flagged post-hoc); abstract caveat list updated. Combined
  state of E1f-L3: event-robust (LORO), specification-fragile (sweep),
  single-history. CRSP + NBER-anchored labeler are the discriminating
  forward tests.

---

## v1.2.0-dev — The addenda D–F wave: costs, replay, mechanism honesty, emergent forgetting, and the withheld era

**Date**: 2026-07-15 (results integrated into `paper/main.tex`; see
PREREG_FRENCH49.md addenda D, E, and F for the registrations and verdicts)

One integration pass over the completed D/E-series batteries. E1f is
rewritten as the paper's real-data centerpiece around Addendum F's
synthesis; all quoted numbers recomputed from the result JSONs and the
audit manifest extended (347 claims, all PASS).

1. **100-seed parity (D6, `results_100seed/e_french49_*.json`).** L3
   walk-forward Γ = +0.00089 ± 0.00011 with the full ordering (joint Holm
   5.2e-65, −5.5%); L1 inversion stands with Γ now negative-significant
   (−0.00013 ± 0.00007, headline Holm 1.2e-26). New wrinkle disclosed:
   both stitched Γ turn marginally positive (≈+0.00023) with flat arm
   families (min raw p 0.50/0.34). Bonferroni ×3 caveat updated: every
   primary claim and all three L1 inversion pairs now survive.
2. **Costs (D3, `results/e_french49_L3_costs.json`).** Γ_net strengthens
   with tier: +0.00126/+0.00161/+0.00230 at 25/50/100 bps (both-pay
   convention; orderings hold at every tier, Holm down to 4.6e-19 at
   25 bps); mechanism confirmed (A1 churn 1.03/day vs A6 0.62). **The L1
   inversion REVERSES net of costs** (A6 beats A1, p=1.2e-16) — the
   inversion, not the deficit, was the gross-only phenomenon. Gate-1 cost
   slice lodged as sensitivity (L3 pooled sub-criterion −0.10% gross →
   +3.0% net; gate 1 as registered remains a gross FAIL). Caveat (iv)
   rewritten: costs are now measured, not deferred, for L3/L1.
3. **Replay (D1/D2, `results/e1_replay.json`,
   `results/e_french49_L3_replay.json`).** Synthetic: decoupled buffer +
   generous burst refit closes only 56.3% of the deficit (< the lodged
   60% — eviction-coupling stronger than the theory requires) and stays
   ≪ A6 (p=7.0e-14); replay+INV beats A9 but loses to A6 (Holm 0.040)
   and A10 (Holm 0.017). A1r rows added to Table 1 (conventions match;
   shared arms reproduce to quoted precision). French L3: replay collects
   ~99% of the deficit yet A6 beats replay (Holm 0.013) and replay+INV
   (Holm 4.5e-4) — data retention matches parameter retention against the
   ERM oracle; the pool still wins.
4. **Mechanism honesty (E-X1/E-X3, `results/e_french49_L3_x1.json`).**
   No dormancy/rehearsal covariate explains Γ_i (all registered slopes
   n.s.; overlap dilution ≤4.4%); the 15% gap does not decay across the
   probe (R²<0.2) — a level offset, not a relearning transient. The
   registered RENAME executed in the paper: on real data the measured
   quantity is a **regime-conditional allocation deficit**;
   eviction-forgetting remains demonstrated only in the controlled
   settings. Symbol and definition of Γ̂ unchanged.
5. **E-X4 → new §E1m (`results/e_x4_mlp.json`).** Shared trunk 20→32→32,
   nothing evicted, identical architecture across arms: Γ-mlp =
   +0.01009 ± 0.00037 (100 seeds, p=1.9e-78), reactivation-localized
   (~4× probe vs steady); competition pins 3/4 regimes every seed and
   matches the oracle. Honest null: invariance effect absent under the
   MLP (p=0.13). Lodged divergence at full prominence: the E6 inversion
   does not reproduce at 4× SNR (Γ grows ~5×), with the recorded
   single-readout architectural caveat — the linear E6 boundary stands
   as the linear result. "Forgetting is coded, not emergent" is answered.
6. **The withheld era (E-F, `results/e_french49_prewar_L3_*.json`).**
   36 industries, 1926–1989, frozen 15% spec, zero new researcher degrees
   of freedom. Gate 1's strongest pass ever (z=23.5) coincides with an
   inversion at 15% (Γ=−0.00024±0.00008) → gate 1 demoted to a structure
   screen. **Sign-rule scorecard: 5/6 withheld cells consistent in both
   directions**, incl. two positive-side full orderings (10% Holm 1.9e-6;
   1958–89 Holm 2.1e-4); the 12% conservative miss reported under both
   scorings (weak-form hit / strong-form miss). Fragility replicates in
   pattern but the window RELOCATES (15%→10%) with crisis density (41%
   vs 13% crisis-union days); both simple readings (fixed-threshold
   artifact; naive granularity) refuted as stated.
7. **Paper-wide reconciliation.** Abstract rewritten around the new
   record (same caveat prominence, no growth); C4/C5, register paragraph,
   E1 (replay paragraph + Table 1 rows), E1s arm-count note, stats
   (seed counts per battery; costs inside the metric for E1f),
   Synthesis (the four surviving claims), Limitations (multi-era but one
   country/one aggregate; mechanism attribution open, CRSP + NBER as
   deciders). references.bib: + Kumar et al. (FnT ML 2025, average-reward
   CL thesis Γ̂ operationalizes) and Capitaine et al. (ICLR 2026, online
   DFL regret, drift-only) with one differentiation line each; ReCAP
   deliberately NOT added pending a full read (TODO comment in source).
8. **Audit.** `code/audit_manifest.json`: 37 stale claims replaced,
   112 claims added (replay closures, cost tiers, prewar cells,
   sign-rule count as an eq-claim, X4 Γ, 100-seed values, stitched
   wrinkle). `python3 code/audit_numbers.py`: **347 claims checked,
   347 PASS**. main.tex recompiles clean.

---

## v1.3.0 — The addenda G–O wave: external custody resolves, event-level honesty, Japan, and the window map

**Date**: 2026-07-21 (registrations and verdicts in
`PREREG_FRENCH49.md` Addenda G–O; custody grades in `PROVENANCE.md`;
results integrated into `paper/main.tex`, now 38 pp)

Every battery below was registered before it ran (custody grade per
registration in `PROVENANCE.md`; from Addendum J onward each spec was
pushed alone, before its implementation existed).

1. **The NBER forward test resolved — a hit under both scoring forms,
   under third-party custody** (Addendum G; registration deposited at
   osf.io/nsx4e 22:47 ET 2026-07-15, NBER dates first joined to the
   panel 22:55 ET). Causal walk-forward: Γ = +0.00081 ± 0.00033 gross,
   +0.00105 ± 0.00033 net of 25 bps; A6 < A1 at Holm 1.6e-4; gate 1
   null again (third screen/pool-value dissociation). Stitched
   variants flat, disclosed; the non-causal calendar cell is a
   weak-form hit / strong-form miss. The owed LORO/era supplement
   (2026-07-16, `results/e_french49_nber_loro.json`): the deficit
   survives every single-event and calendar exclusion (drop-2020
   +0.00042 ± 0.00026; drop-2008/09 +0.00036 ± 0.00030) but dropping
   January 2009 alone leaves 41% of headline, and the 2010s era block
   is negative-significant — two-recession concentration, stated
   wherever the cell is cited.
2. **Banded-monolith control (PREREG H / Addendum I,
   `results/e_french49_banded.json`).** The practitioner
   countermeasure: A1 that only re-trades when > b names change.
   Banding is free but cannot buy the pool: A6 beats both bands net of
   25 bps (L3 Holm ≤ 7.1e-17; L1 residual +0.00028 ± 0.00011, with the
   62% b=2 attenuation of the L1 net reversal disclosed). The
   registered ≥30% turnover-cut clause was NOT met (4.1%/15.7%) —
   selection quality, not just churn, carries the deficit. Addendum I
   also records D4's fourth outcome (A3′ strictly worse than A3) and
   the D5 CVaR tail-reading refutation (interpretation demoted).
3. **Expanding-window baseline + 100-seed reversal (Addenda J/K2,
   `results/e_french49_L3_expwin*.json`).** The 20-seed pilot took the
   middle branch (A1e collects 73.0% of Γ, residual n.s.) and the
   ICAIF class sentence was narrowed to recency-driven policies. At
   the registered 100-seed budget the pilot's null residual REVERSED:
   A1e collects 58.7% and A1e−A9 = +0.000366 ± 0.000128 is
   positive-significant (~+3.7 bps/day) — the residual is real. A6
   beats A1e (Holm 1.4e-23). Replay remains the full collector
   (share ≈96%, A1r−A9 n.s.), and A6 still beats replay: paired
   A1r−A6 = +0.000389 ± 0.000096, p = 2.7e-12, computed post-hoc from
   the released raw seeds (the lodged Holm family omitted exactly this
   pair — disclosed; supersedes the 20-seed Holm 0.013). D8: Γ
   positive-significant in all 6 probe/dormancy re-read cells. K3:
   Γ's sign survives k=3 and k=10 decision layers.
4. **The event-level program (K1, N1, O) — the register in which most
   cells weaken, taken in full.** L3 (n=27): Wilcoxon p = 0.016
   passes, sign test p = 0.061 MISSES → lodged adverse branch taken,
   all walk-forward seed CIs relabeled implementation-precision-only.
   NBER (n=20): passes BOTH registered tests (sign 0.021, Wilcoxon
   0.016) — the program's strongest event-level cell. Prewar 10%
   (n=56): Wilcoxon-only (0.029; sign 0.175); 1958–89 (n=21): fails
   both. The pooled cross-history register (Addendum O, n=109,
   independent histories once, Japan's negatives signed): sign test
   p = 0.0625 FAILS → **the frequency claim is retired
   program-wide**; Wilcoxon p = 0.0086 passes; the dollar register
   (+4,274 bps-days; bootstrap CI [−1,881, +9,977] covers zero) makes
   the economic claim region-conditional: +4,859 / +1,542 / −2,127
   bps-days (US-modern / US-prewar / Japan).
5. **Japan — the first non-US cell (Addendum L,
   `results/e_japan_*.json`).** The E-R register's lodged
   region-specific prediction ("Γ_Japan ≈ 0 or negative") HIT on the
   negative side: Γ = −0.00060 ± 0.00016 with the predicted inversion
   at Holm 3.9e-8 — the largest real-data inversion in the program
   (−6.0 bps/day). Flagged OCCUPANCY-ANOMALOUS in the same sentence:
   crisis union occupies 67.2% of Japanese trading days at 15%
   (scoring clause post-hoc for Japan, lodged ex-ante for the
   remaining regions). All three sweep cells sign-rule consistent;
   screen z = −0.90, a fourth screen/pool-value dissociation.
   Out-of-sample sign-rule record: 9 of 10 cells; full record 12/16
   strong, 16/16 weak.
6. **E-X2 resolved on both eras: WINDOW — and the relocation
   narrative superseded** (`results/e_french49_L3_x2.json`,
   `results/e_french49_prewar_L3_x2.json`). Modern era: window at
   every hysteresis level; the registered 15%/h0 cell sits inside and
   reproduces on tier-2 re-read (+0.00091 ± 0.00020, full ordering) —
   the island clause is dead. Withheld era: window only under
   hysteresis (h4 13–16%, h6 14–16%), and the lodged PX2e anchor
   sub-criterion MISSED — the era's 10% anchor is an isolated h0
   positive (cell solid on tier-2 re-read, +0.00013 ± 0.00006, full
   ordering). Cross-era (descriptive): the windows OVERLAP at 13–16%
   under hysteresis, and hysteresis flips the prewar 15% cell from
   inversion to a positive full ordering. **This supersedes v1.2.0-dev
   item 6's relocation claim ("the window RELOCATES (15%→10%)"): the
   apparent relocation was an artifact of scanning only h=0.**
7. **The window-location estimator (κ) failed calibration and is
   retired pre-CRSP** (`results/window_estimator_calibration.json`).
   The occupancy rule committed in the CRSP T-split amendment requires
   disjoint κ intervals on the two eras ((0.129, 0.143] vs
   (0.471, 0.486]) and is directionally wrong. Disclosed before any
   CRSP data access; the CRSP L3-family primary falls back to the
   frozen 15% threshold; any successor rule must be OSF-lodged
   pre-data (Addendum N3).
8. **The withheld era net of costs — the amplification clause refuted
   out-of-sample (N2, `results/e_prewar_costs.json`).** Both prewar
   positive cells survive the adjudicating 25 bps register
   (+0.00015 ± 0.00010; +0.00020 ± 0.00017) but net sits BELOW gross
   and fades to n.s. at 50/100 bps — the tiers realistic for 1926–89 —
   with the crisis-churn turnover signature absent (A1 1.10 vs A9 1.13
   per day). Cost amplification is an era-local 1990–2025 phenomenon
   and every "costs amplify" sentence is now scoped accordingly. The
   counterpoint at equal prominence: the pool's A6-over-A1 net edge is
   significant at every tier in both cells (~+10.6/+11.3 bps/day at
   25 bps, growing with tier).
9. **Paper-wide integration + audit.** `paper/main.tex` (38 pp)
   rewritten around the extended record: abstract, scorecard
   accounting (12/16 strong, 16/16 weak, 9/10 out-of-sample, with the
   dependence discount stated first), event-level paragraph, Japan and
   X2/κ paragraphs, era-scoped cost claims, claims ledger and
   limitations reconciled. `code/audit_manifest.json` extended
   347 → **508 claims, all PASS** (`python3 code/audit_numbers.py`).
   README and this changelog synced to the paper at HEAD; the README
   had been two waves stale (badge said 272; its relocation section
   and 20-seed replay/2×2 numbers superseded above).
