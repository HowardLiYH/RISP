# Pre-registration: the deployment-form temporal test of the Γ-sign rule

**Author:** Yuhao Li (University of Pennsylvania).
**Written:** 2026-07-16. To be uploaded to osf.io/nsx4e upon creation; the
OSF timestamp is the external marker. This is the first test in the
program whose *measurement* — not merely its specification — is split in
time: the diagnostic is computed on data ending BEFORE the outcomes it is
scored against begin.

## Design

- **Freeze date:** all diagnostic quantities are computed on the French
  49-industry VW daily panel through **2026-06-30** (data already
  published by Ken French as of this writing; the outcome window below
  has not yet occurred for the most part and is unknowable in full).
- **Diagnostics at freeze (computed once, upon this registration's OSF
  upload, and committed to the public repo):** Γ̂_forget = A1−A9
  post-reactivation regret under (a) the L-NBER announcement-lagged
  labeler and (b) L3@15%, each on the trailing window 1990-01-01
  through 2026-06-30; 20 seeds, conventions identical to
  PREREG_FRENCH49/PREREG_NBER.
- **Outcome window:** 2026-07-01 through **2027-03-31** (scored at a
  pre-named date: **2027-04-07**, before the program's mid-April paper
  freeze).
- **Scored outcome:** the sign of the realized A6−A1 post-reactivation
  regret difference over qualifying reactivations inside the outcome
  window (probe 15 days, min dormancy 90 days, same ten-arm harness,
  arms trained walk-forward through the outcome window with no
  retraining of the frozen diagnostics). If the outcome window contains
  ZERO qualifying reactivations (possible: it requires a regime,
  dormant ≥90 days as of a window date, to reactivate), the test is
  declared VOID — reported as such, not as a hit or miss.
- **Prediction (H-SIGN, deployment form):** sign(Γ̂ at freeze) predicts
  sign(A1−A6 realized) per labeler cell: Γ̂ > 0 (significant) ⇒ A6
  outperforms A1 in the outcome window's reactivations; Γ̂ ≤ 0 ⇒ A6
  does not outperform (flat or inversion permitted).
- **Scoring:** weak and strong forms as defined in PREREG_FRENCH49
  addendum F, fixed here BEFORE any outcome exists — this closes the
  post-hoc-taxonomy gap disclosed for the withheld-era scorecard.
- **What would refute:** a significantly positive frozen Γ̂ followed by
  A1 outperforming A6 in the outcome window (or vice versa). One clean
  refuting cell falsifies the deployment form of the rule.

## Why this design exists

Prior cells validated the rule out-of-era and (once) under third-party
spec custody, but every prior cell computed the diagnostic and the
outcome on the same window. This registration commits the rule in the
only form a deployer can actually use: measure first, act, find out
later. It is scored on 2027-04-07 regardless of outcome and reported at
headline prominence either way.
