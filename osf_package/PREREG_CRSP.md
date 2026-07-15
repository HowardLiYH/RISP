# Pre-registration: the CRSP constituent-level forward test of the Γ-sign rule

**Author:** Yuhao Li (University of Pennsylvania).
**Written:** 2026-07-15, BEFORE any CRSP data has been obtained or examined
(WRDS access request pending). This document fixes the complete test
battery in advance; the OSF upload timestamp is the external marker.

## The hypothesis under test (formulated 2026-07-14, in-sample; this is its
## first ex-ante exposure)

**H-SIGN:** On a capacity-bounded specialist pool over a real cross-section,
the sign of the measured forgetting deficit
Γ̂_forget = A1(monolith-ERM) − A9(oracle-pinned-ERM) post-reactivation
decision regret determines whether the pool pays:
- Γ̂ significantly positive ⇒ the pre-registered dissociation ordering
  (A6 < A5 < A1 on post-reactivation regret) emerges;
- Γ̂ ≈ 0 or negative ⇒ no dissociation, and the invariance-premium
  inversion (A1 beats A6) is permitted.
In-sample record to date (French 49 industries, one history): 3-for-3 on
direction (L1: Γ≈0 → inversion; L3@15%: Γ>0 → ordering; L3@20%: Γ<0 →
inversion). This registration exposes H-SIGN to refutation on new data.

## Substrate

CRSP daily stock file via WRDS (share codes 10/11; exchanges NYSE/AMEX/
NASDAQ), S&P 500 constituents by point-in-time membership (CRSP dsp500list
or equivalent), 1990-01-02 through the latest available date, delisting
returns incorporated. Survivorship-bias-free by construction.

## Design (identical to the French-49 protocol; PREREG_FRENCH49.md)

- Features: the same 8 return-based causal features (mom5, mom20, mom100,
  rev1, vol20, magap50, xsrank20, const), cross-sectionally standardized.
- Decision layer: top-k cardinality portfolio, k=25 of ~500, w_max=0.04
  (invested fraction 1.0, same proportional structure as k=5/49).
- Labelers, fixed in advance, THREE cells with Bonferroni ×3 disclosed:
  L1 (vol-band × trend), L3 (drawdown 15% × trend, exactly as French),
  and L-NBER (NBER recession indicator, lagged one month for causality
  [announcement-lag-free variant: use only the recession's own dates
  shifted by the historical announcement delay], × 50-day trend).
- Gate 1: walk-forward regime-conditioned ridge vs 50 block-shuffled
  controls vs pooled; criteria: z>2 (permutation register; empirical
  floor 1/51), conditioned beats pooled, split-half gaps both positive.
- Gate 2: Γ̂_forget with paired per-seed 95% CI, 20 seeds, probe 15 days,
  min dormancy 90 days.
- Dissociation: the same ten arms, same 6-pair Welch family + Holm; both
  walk-forward (primary) and stitched (secondary) designs; plus
  era-blocked analysis (1990s/2000s/2010s/2020s) and
  leave-one-reactivation-out, both now standard.
- Costs: all headline numbers reported both gross and net of 25 bps
  (with 50/100 bps crisis-window sensitivity), per PREREG addendum D3.

## Pre-registered predictions

- **PC1 (H-SIGN, the paper's forward bet, ~60%):** the sign of Γ̂ on each
  labeler cell predicts that cell's dissociation outcome direction
  (ordering iff Γ̂ significantly positive), evaluated per cell across the
  three labeler cells.
- **PC2 (~50%):** at least one labeler cell (most plausibly L-NBER or L3)
  yields Γ̂ > 0 at constituent level — the fourth cell of the
  precondition matrix.
- **PC3 (aggregation check, genuinely open):** if the French-49 L3 deficit
  was an aggregation artifact (Lo–MacKinlay), the constituent-level Γ̂
  will be materially smaller or zero at the same labeler; similarity of
  magnitudes supports the mechanism reading.
- **PC4:** any outcome — including H-SIGN's refutation — is reported at
  headline prominence, per the project's standing rule.

## What would refute H-SIGN

A cell with Γ̂ significantly positive and no ordering (or an inversion),
or a cell with Γ̂ ≈ 0/negative and a significant ordering. One clean
refuting cell falsifies the rule as stated.
