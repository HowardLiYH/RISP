# RISP — Execution Plan (Idea 1)

**Project:** *When the Regime Returns: Retention and Invariance in Decision-Focused
Strategy Pools for Non-Stationary Markets*
**Framework name:** **RISP** (Regime-Invariant Specialist Pools).
**Date started:** 2026-06-11. **Source assets:** GAUSE (paper + code + data, this repo),
Inv-PnCO (design described in `IDea 1/PAPER_DESIGN_AND_ROADMAP.tex`).

---

## 0. Decisions made up front (flagged for Yuhao's review)

1. **Naming: RISP (final, per Yuhao 2026-06-11).** The build initially adopted
   "NicheMem" (inferred from the requested file name `NicheMem Explainer.tex`); Yuhao
   subsequently confirmed the roadmap's pre-registered name **RISP**
   (Regime-Invariant Specialist Pools), and a global rename was applied across all
   papers, code identifiers, result-file keys (labels only — numbers untouched),
   figures, and README art. The explainer file is now `RISP Explainer.tex`.
2. **Data scope (honest).** The roadmap's flagship is a CRSP/WRDS S&P 500 panel — not
   available on this machine and the WRDS request has multi-week lead time. The
   experiments here therefore use the three data tiers that *are* available now:
   (a) **fully synthetic** regime-switching markets with controlled ground truth
   (the headline 2×2, where every causal claim is testable);
   (b) **semi-synthetic regime-stitched** real data (real per-regime return blocks from
   GAUSE's Bybit crypto + FRED commodities, re-stitched into controlled dormancy
   schedules — the roadmap's E3 design);
   (c) **real walk-forward** crypto (5 Bybit USDT pairs, daily + 1H, 2021–2025) and FRED
   commodities — small-universe, honestly reported as such.
   The papers state explicitly that the equities flagship is the planned extension and
   that present real-data evidence is crypto/commodities-scale. **No fabricated equity
   results.**
3. **Decision layer.** Cardinality-constrained long-only portfolio with linear utility
   `F(z,y) = yᵀz`, budget + ‖z‖₀ ≤ k. With linear utility the exact optimum is the
   top-k assets at maximum weight, so exact regret is computable in O(n log n) without
   Gurobi. This keeps the PnO/SPO structure (decisions, regret) while making 20-seed
   sweeps cheap. The knapsack/execution variants are noted as robustness extensions.
4. **Statistical battery scoped.** 20 seeds, Welch tests + Holm–Bonferroni, 95% CIs,
   transaction costs at 10 bps for any P&L-flavored number. DSR/SPA are described in the
   protocol section as required for *alpha* claims; our headline claims are regret/
   retention claims (mechanism, not alpha), per roadmap §8 R1.
5. **All three documents report what the experiments actually show** — including any
   cell of the 2×2 that comes out null (roadmap fallback F2 is wired in, not hidden).

---

## 1. Deliverables

| File | Style/length reference | Content |
|---|---|---|
| `IDea 1/paper/main.tex` | `GAUSE/paper/main.tex` (NeurIPS 2024, ~1700 lines) | The research paper: intro, related work, formal setup, RISP, theory (Props 1–4 with proofs/sketches), experiments E0–E5 with real numbers, honest audit, limitations |
| `IDea 1/paper/RISP Explainer.tex` | `GAUSE/paper/gause_explainer.tex` (AutoAgent format, ~1900 lines) | Explanatory companion: boxed abstract, ToC, blue headings, TikZ architecture + timeline diagrams, mechanism walkthroughs, worked demonstration, applications, when-not-to-use |
| `IDea 1/paper/Deep Dive.tex` | `GAUSE/paper/method_deep_dive.tex` (~4800 lines) | Mathematical deep dive: Parts; foundations from first principles (decision-focused learning/SPO, invariant risk & OOD, online learning & sleeping experts, regime-switching models, bounded-capacity memory); every proof in full; worked numerical examples; code listings; intuition/keypoint/warning boxes |
| `IDea 1/code/` | — | `risp` package + experiment scripts (reproducible, seeded) |
| `IDea 1/results/` | — | JSON results per experiment (papers cite these numbers) |
| `IDea 1/paper/figures/` | — | PDF figures generated from results |
| `IDea 1/theory/THEORY_NOTES.md` | — | Derivations feeding all three docs |

## 2. Formal core (what gets built and proven)

**Setup.** Stream t=1..T, features x_t, unknown coefficients y_t (next-period returns),
latent regime r_t ∈ {1..R}, regimes recur with dormancy D(r). The e-th occurrence of
regime r is environment (r,e) with law P_{r,e}(x,y). Decision ẑ = z(ŷ) solves the
cardinality portfolio; per-step decision regret ρ_t = F(z*(y_t),y_t) − F(z(ŷ_t),y_t) ≥ 0,
bounded by B under bounded returns.

**RISP mechanism** (batched competition cycle):
1. all specialists predict + decide; per-window (W_c ≈ 20 days) cumulative within-regime
   regret decides the **window winner**;
2. winner applies one EG/Hedge affinity update (η ≈ 0.6) on the regime simplex;
3. specialists holding r_t within capacity K train that regime's head with the
   **decision-focused invariance loss** over the regime's episode buffer:
   min over heads of Var_e[L_SPO(r,e)] + β·E_e[L_SPO(r,e)] (SPO+ surrogate);
4. affinities > 0.95 ⇒ **pin** assignment (reward-independent thereafter).

Memory models: **hard** (K LRU regime-heads, eviction = reset) and **soft** (shared
backbone + per-regime adapters; foreign updates decay untouched adapters by ρ).

**Theory (full derivations in `theory/THEORY_NOTES.md` → papers):**
- **Prop 1 (post-reactivation regret decomposition).** E[Regret_react(r)] ≤ G_inv + G_forget:
  G_inv = mean episode loss + C·sqrt(Var_e) (episode-level Chebyshev transfer to the
  unseen episode, episodes exchangeable draws from a regime hyper-distribution) and
  G_forget = Φ(D;A)·C_relearn. Includes the **KL→regret bridge**: bounded regret +
  Pinsker gives |L_e − L_e'| ≤ B·sqrt(KL(P_e‖P_e')/2), so an invariance-in-KL premise
  yields a regret-metric bound; honest fallback to the KL metric stated.
- **Prop 2 (reward-independence zeroes forgetting).** Hard model: reward-driven
  allocation ⇒ Pr[eviction during D] → 1 with an explicit geometric-waiting-time rate;
  any reward-independent assignment ⇒ Φ ≡ 0. Soft model: (1−ρ)^{U_D} decay vs exact
  preservation. (Extends GAUSE Obs. 1/Prop. about reallocation to the regret setting.)
- **Prop 3 (additive interaction).** The two terms are controlled by independent design
  choices; the bound is additive ⇒ predicted monotone 2×2. Empirical interaction index
  defined and measured.
- **Prop 4 (break-even dormancy).** Carrying cost c per idle specialist-day vs expected
  reactivation saving S(D): retention pays iff D ≥ D* with closed form under the hard
  model — quantified in E3 (roadmap C5).
- Scope honesty carried over from GAUSE: idealized models; no adversarial-regret claim
  for coupled WTA dynamics; finite-episode estimation error of Var_e flagged (crisis
  regimes have ~5–7 episodes; sub-episode blocks + cross-asset episodes as mitigations).

## 3. Experiments (all seeded, 20 seeds unless noted; results → JSON)

- **E0 — Structure diagnostic (gate, runs first).** Real crypto + commodities: oracle
  regime-conditioned linear predictor vs shuffled-label control **on decision regret**
  (GAUSE found no exploitable structure under the *prediction* metric for these
  domains; re-testing under the decision metric is itself a finding either way).
- **E1 — Headline 2×2 dissociation.** Arms (capacity-matched): A1 monolith-ERM,
  A2 MoE router (gate trained on realized regret), A3 recent-performance capital
  allocator (industry baseline), A4 random fixed niches, A5 RISP-ERM,
  A6 RISP-full (INV), A7 monolith-INV, A8a sleeping experts over fixed strategies,
  A8b sleeping experts over learning experts. Metrics: overall regret,
  **post-reactivation regret** (first 15 days after each reactivation), relearning
  half-life. Pre-registered ordering: A6 < A5 ≈ A4 ≪ A2 ≈ A3 ≈ A1; A7 helps overall but
  not post-reactivation. Run on synthetic (headline) + semi-synthetic crypto.
- **E2 — Capacity sweep** K = 1..R, hard + soft memory. Expected: reward-independent
  arms flat in K; reward-driven close only as K→R.
- **E3 — Dormancy sweep** (semi-synthetic stitched schedules, D ∈ {21, 63, 126, 252,
  504} trading days) → break-even dormancy for Prop 4.
- **E4 — Episode-heterogeneity sweep** (allocation fixed at RISP; vary episode
  count and inter-episode shift): ERM degrades with heterogeneity, INV flat.
- **E5 — Ablations.** β sweep; **no-variance-term** control (expect it can underperform
  ERM, the Inv-PnCO Table-7 analogue); W_c ∈ {1,5,20,60}; λ ∈ {0, 0.3}; pinned vs
  never-pinned; L1 vs L2 labels; cost sensitivity 5/10/25 bps.

## 4. Honest-reporting protocol

Every number in the papers traces to a results JSON. Pre-registered predictions stated
*before* results in the papers; deviations reported as findings, not buried. The audit
section maps when RISP does **not** pay (unlimited capacity, no regime structure,
no dormancy, drift-dominated regimes, carrying costs above break-even).

## 5. Order of work and progress reviews

Phase 1 plan → Phase 2 theory → Phase 3 code (+unit sanity checks) → Phase 4 E0/E1
(**review checkpoint: does the 2×2 hold? trigger F1/F2 framing if not**) → Phase 5
E2–E5 (**review checkpoint after each sweep; add experiments where results are
ambiguous**) → Phase 6 figures/tables → Phase 7 write main.tex → Phase 8 Explainer →
Phase 9 Deep Dive → Phase 10 compile + red-team against the roadmap §8 attack list +
number-consistency audit.

## 6. Open questions for Yuhao (non-blocking; defaults chosen)

1. RISP vs RISP naming (default: RISP).
2. Equities flagship: submit the WRDS/CRSP request now so the panel exists for the
   AAAI/KDD-cycle version (papers are written so equity results slot in additively).
3. Inv-PnCO theory coauthor invitation (roadmap suggests deciding by Jul 1).

---

## STATUS (2026-06-11, end of build session): COMPLETE

All deliverables built, compiled, and number-audited. `paper/main.pdf` (19 pp),
`paper/RISP Explainer.pdf` (18 pp), `paper/Deep Dive.pdf` (80 pp) — zero LaTeX
errors, zero undefined refs/cites; every number traces to `results/*.json`; 46-point
numeric audit passed; roadmap attack list R1–R7 each addressed and verified.

**Headline (synthetic, 20 seeds, Holm-corrected):** 2×2 dissociation confirmed.
Retention −6.1% (p=1.3e−3), invariance −4.4% (p=6.1e−3), joint −10.3% (p=9.2e−7;
38% of excess over noise floor). Super-additive interaction confirmed
(monolith+INV ≈ monolith, p=0.88; I=−0.0015±0.0005). RISP-full ≈ oracle+INV
skyline (p=0.72). Router/recent-perf/Hedge-learners cluster with the monolith;
Hedge-fixed retains but loses everywhere.

**Honest results reported at full prominence:**
1. E0 real-data gate FAILS (crypto+commodities, decision metric, both causal
   labelers) → E1s real-data dissociation correctly null. Diagnostic-first
   protocol is a co-equal contribution (roadmap fallback F1 activated).
2. Pre-registered batching expectation REFUTED (flat in W_c; EG accumulation is
   the operative averager).
3. E6 SNR audit (born from the failed first prototype): the advantage INVERTS at
   high signal-to-noise (−49% at 8×) — measured deployment boundary.
4. β=0 variance-only collapses (worse than ERM), as theory predicts.
5. Crisis regime: stable unique ownership in 20/20 seeds but α only 0.67–0.87
   (below formal pin threshold; scarce windows).
6. Soft-memory model corrected mid-build (initial implementation still evicted);
   E2-soft rerun: reward-driven arms flat at ~0.0328 at every K — interference
   never closes the gap.

**Next steps (unchanged):** WRDS/CRSP equities panel for the flagship real-data
test (E0 gate pre-registered); Inv-PnCO coauthor decision by Jul 1; risk-committee
pivot (F3) if equity dormancy proves too short.
