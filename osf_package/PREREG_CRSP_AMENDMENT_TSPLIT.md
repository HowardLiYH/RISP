# Amendment to PREREG_CRSP.md: temporal-split design, adjudicating register, and the window-location estimator

**Author:** Yuhao Li (University of Pennsylvania).
**Written:** 2026-07-16, BEFORE any WRDS/CRSP data access (access expected
September 2026). To be uploaded to osf.io/nsx4e alongside the original
CRSP registration, which it amends and supersedes where they conflict.

## A. Temporal-split (deployment-form) design — the primary test

The original registration's concurrent battery is demoted to secondary.
The PRIMARY CRSP test is time-split:

- **Split dates T\*:** rolling, one per era: 1999-12-31, 2007-12-31,
  2015-12-31, 2019-12-31 (four cells).
- For each T\*: Γ̂ is computed on constituent data **≤ T\* only** (same
  conventions: A1−A9 post-reactivation, 20 seeds, probe 15, dormancy 90,
  L-NBER announcement-lagged and L3@15% labeler cells); the sign and
  magnitude are recorded BEFORE the post-T\* slice is scored.
- The arm ordering is adjudicated on **post-T\* qualifying reactivations
  only** (through the earlier of T\*+8 years or data end), arms trained
  walk-forward through the outcome window with no access to the frozen
  diagnostic.
- **Prediction (H-SIGN, deployment form):** sign(Γ̂ ≤ T\*) predicts the
  post-T\* outcome direction per cell, scored under the weak and strong
  forms of PREREG_FRENCH49 addendum F (fixed before any CRSP outcome
  exists).

## B. Adjudicating register — fixed now

The **net-of-25bps (both-pay)** register adjudicates the strong-form
ordering chain, with gross reported alongside; this choice is made here,
before any CRSP data exists, on the D3 economic argument (crisis-window
costs are integral to the phenomenon, and the arm-only sensitivity is
register-identical). The strong-form chain is A6 < A5 < A1 with A6-vs-A1
Holm < 0.05 in the 6-pair family; A6-vs-A5 and A5-vs-A1 reported, chain
"full" only if all three legs hold.

## C. The window-location estimator — committed

For the L3-family cells, the drawdown threshold is NOT swept on CRSP.
It is set per era by an estimator whose form is fixed now and whose
single parameter is calibrated ONLY on already-run cells (French-49
1990–2025 and 1926–1989, plus the regional cells of PREREG addendum E-R
if run before CRSP delivery): **θ(era) = the smallest threshold at which
the era's crisis-union occupancy falls below κ of trading days**, κ
calibrated to reproduce the two known paying windows (15% ↔ 13%
occupancy modern; 10% ↔ prewar). κ, its calibration table, and the
resulting CRSP-era θ will be committed to osf.io/nsx4e BEFORE data
access; if the calibration is ambiguous, the ambiguity and the chosen
rule are lodged with it. A fixed-15% cell is retained as a disclosed
robustness column, not a selection opportunity.

## D. Void and refutation clauses

A T\*-cell with zero qualifying post-T\* reactivations is VOID (reported,
not scored). One clean refuting cell (significantly positive frozen Γ̂
followed by A1 outperforming A6 post-T\*, or the reverse) falsifies the
deployment form of the rule; all cells are reported regardless.
