# Pre-registration: the NBER-anchored labeler on French 49 industries
# (the WRDS-independent forward test)

**Author:** Yuhao Li (University of Pennsylvania).
**Written:** 2026-07-15. As of this writing, NBER recession dates have NOT
been joined to the French panel in any form, exploratory or otherwise, and
no L-NBER statistic of any kind has been computed. The OSF upload
timestamp is the external marker; the experiment runs only after lodging.

## Motivation (fixed before running)

The L3 drawdown labeler's deficit is event-robust but threshold-fragile
(PREREG_FRENCH49 addendum C). A structurally-anchored labeler with no free
threshold removes the specification degree of freedom entirely: NBER
recession dating is exogenous to our pipeline, coarse, and slow — crisis
regimes recur on multi-year scales by construction.

## Labeler L-NBER (causal)

Regime = NBER recession indicator × 50-day trend sign (4 regimes). To
avoid look-ahead from NBER's announcement lag, the recession state at day
t uses the indicator as it would have been knowable at t: recession start
dates shifted forward by the historical announcement delay for that
episode (documented per episode from NBER's announcement records), end
dates likewise. Both variants (announcement-lagged primary; calendar-dated
as a disclosed robustness check) are reported.

## Design

Identical to PREREG_FRENCH49 in every other respect: same panel
(French 49 daily VW, 1990–2025), same 8 features, k=5/w_max=0.2, gate 1
with 50 shuffle controls (permutation register), gate 2 Γ̂ with paired CI,
ten arms, 6-pair Holm family, walk-forward + stitched, 20 seeds, LORO +
era-blocked analyses, gross and net-of-25bps.

## Pre-registered predictions

- **PN1 (H-SIGN forward test, ~60%):** the sign of Γ̂ under L-NBER
  predicts the dissociation outcome direction (ordering iff Γ̂
  significantly positive). This is the same H-SIGN hypothesis as the CRSP
  registration, exposed here first because the data is free and on disk.
- **PN2 (~45%):** Γ̂ > 0 under L-NBER (recession regimes sleep 6–10 years;
  but linear heads refit fast, and near-miss rehearsals — 2011, 2015–16,
  2018, non-recession drawdowns — remain in the calm regimes under this
  labeler, which may keep every learner fresh).
- **PN3 (fragility discriminator):** if L-NBER (no threshold to tune)
  reproduces a positive deficit, the L3 threshold-fragility reads as a
  granularity window; if L-NBER is null, the artifact reading of L3
  gains, and the paper says so at headline prominence.
- **PN4:** all outcomes reported; no selective emphasis; one labeler, two
  causality variants, family-wise accounting disclosed.

## What would refute H-SIGN here

Γ̂ significantly positive with no ordering/inversion, or Γ̂ ≈ 0 with a
significant ordering, under the primary (announcement-lagged) variant.
