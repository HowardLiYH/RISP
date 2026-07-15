# Pre-registration: Two-gate protocol + dissociation on French 49 industry portfolios

**Written: 2026-07-14, BEFORE any French-data experiment was run.** (Local
timestamp; upload this file to OSF before the equities/CRSP follow-up for an
external timestamp. The repo commit containing this file and no French
results is the verifiable marker.)

## Substrate

Ken French Data Library, 49 Industry Portfolios (Daily), value-weighted
returns, built from the 2026-05 CRSP database. **Primary window:
1990-01-02 through 2025-12-31** (matches the roadmap's flagship crisis
inventory: 2000, 2008, 2011, 2015, 2018, 2020, 2022). Industries with any
missing value (-99.99/-999) inside the window are dropped; we expect 0–2
drops. Survivorship handled by construction (portfolios absorb delistings).

## Design (fixed in advance; mirrors the paper's E0/E1r protocols exactly)

- **Features (8, return-derivable only — no OHLCV here):** mom5, mom20,
  mom100, rev1 (−r_{t−1}), vol20, magap50, xsrank20, const; all causal via
  shift(1), cross-sectionally standardized per day.
- **Labelers:** L1 (rolling vol-percentile band × trend sign) and L2
  (causal 2-state filtered vol × trend) on the equal-weight log-price
  index, daily windows 20/50/252 — at daily frequency bar-native and
  wall-clock conventions coincide, so the family is exactly TWO cells.
- **Decision layer:** top-k cardinality portfolio, k=5 of ~49, w_max=0.2,
  linear utility, decision regret as everywhere in the paper.
- **Gate 1 (structure):** identical walk-forward regime-conditioned ridge
  (refit 60d, min 30 obs, λ=10) vs block-shuffled labels vs pooled,
  second-half evaluation. **50 shuffle controls from the start** (no
  screen-then-confirm two-step this time). PASS criterion per cell:
  z_vs_shuffled > 2 AND one-sided p < 0.005 (t, 49 dof) AND
  cond-beats-pooled > 0 AND split-half gaps both positive. Family = 2
  cells; we apply Bonferroni ×2 mentally and report both cells regardless.
- **Gate 2 (harvestable forgetting):** Γ̂_forget = A1(monolith-ERM) −
  A9(oracle-pinned-ERM) post-reactivation regret, with paired per-seed 95%
  CI. Positive-and-significant = pass.
- **Dissociation:** the same ten arms as E1s/E1r, K=2, hard memory,
  probe 15 days, dormancy threshold 90 days, 20 seeds, the same
  pre-registered 6-pair Welch family + Holm. Two schedule designs:
  (a) **PRIMARY — real walk-forward**: the actual 1990–2025 history with
  causal labels; seeds vary arm initialization only. Reported alongside
  the natural dormancy distribution of the rarest regime.
  (b) SECONDARY — stitched controlled dormancy (as E1s/E1r), rare regime
  = the least-frequent label, dormancy ≥ 90 days.

## Pre-registered predictions (falsifiable, stated with confidence levels)

- **P1 (gate 1, genuinely open; lean PASS ~60%):** at least one of the two
  labeler cells passes. Rationale: daily industry momentum/vol structure
  is the regime-switching literature's home turf, and this is the first
  substrate in the program with both a wide cross-section (~49) and
  multi-decade episode inventory. A double fail would extend the E0 null
  from small universes to the canonical equity cross-section — reportable
  either way.
- **P2 (the two-gate protocol's core commitment, from the paper):** the
  dissociation ordering A6 < A5 ≪ reward-driven cluster emerges **iff
  gate 1 AND gate 2 both pass**. This is the protocol's first fully
  ex-ante test on a new substrate.
- **P3 (gate 2, lean PASS ~55%):** Γ̂_forget > 0 on the walk-forward
  design. Rationale: crisis-regime dormancy here is measured in years at
  daily frequency (unlike 4H crypto's fast relearning); against: linear
  heads refit fast everywhere, and E6 warns that relearning speed, not
  dormancy length, is what kills the deficit.
- **P4:** if gates disagree with the dissociation outcome in either
  direction, that refutes the two-gate protocol as stated and will be
  reported as such at full prominence.

## What will be reported regardless of outcome

All four cells' gate statistics, the natural dormancy distribution, the
full ten-arm table for both schedule designs, Γ̂_forget with CI, and the
verdict on P1–P4. No selective reporting: the family is two labeler cells,
one window, one k — there is no screen to select from.

---

# ADDENDUM — Results and verdicts (written 2026-07-14 AFTER the runs; nothing above this line was edited)

- **P1 (gate 1): CONFIRMED.** L1 cell PASSES all pre-registered criteria:
  gap +1.14%, z=+3.18, p=1.5e-27 (50 shuffles), cond>pooled, both halves
  positive. L2 cell FAILS (z=0.88 < 2; gap +0.32%). First daily-frequency
  structure pass in the program, on the canonical equity cross-section,
  with a two-cell family (no screen selection).
- **P3 (gate 2): REFUTED in the lean, PARTIALLY in substance.** Γ̂_forget:
  walk-forward −0.00013 ± 0.00018 (n.s.), stitched +0.00007 ± 0.00025
  (n.s.) — zero on the third real substrate in a row. The lean-PASS
  prediction (55%) was wrong.
- **P2 (dissociation iff both gates): the stitched design is CONSISTENT
  (flat, min raw p=0.70); the walk-forward design produces something the
  protocol did NOT predict — a significant INVERSION: A1-monolith beats
  A6-RISP-inv (raw 8.0e-9, Holm 4.8e-8), A9-oracle-pinned beats A6
  (Holm 0.030), A1 beats A5 (Holm 0.024).** The protocol said "no
  dissociation" under a failed gate 2; it did not say "significant
  anti-dissociation." Post-hoc reading (flagged as post-hoc): with
  Γ_forget = 0 there is no insurance claim to collect, so the invariance
  premium (the steady-state tax measured in the synthetic E1) becomes a
  net, visible cost — the E6 inversion mechanism operating at real-data
  effective SNR. This retrospective account must itself be treated as a
  gate-3 hypothesis to test out-of-sample, not as a save.
- **P4: triggered.** The two-gate protocol as stated is incomplete: gate
  outcomes predicted flat, reality delivered directional inversion in the
  walk-forward design. Reported at full prominence.
- **Critical statistical caveat (stated before any use of these numbers):**
  the walk-forward design shares ONE market history across seeds; seeds
  vary only arm initialization (A8a is deterministic: CI ±0.00000). Its
  CIs quantify implementation noise conditional on this history, not
  sampling uncertainty over markets. The stitched design (schedule
  resampling) is the honest variance estimate and is flat. The inversion
  is therefore "precisely estimated on this one history," not
  "established across histories" — both statements go in the paper.
- Dormancy reality check: the L1 labeler cycles fast even on equities
  (median reactivation dormancy 5–9 days; 98 reactivations ≥90 days across
  regimes; evaluated n_react=46). The roadmap's "multi-year crisis
  dormancy" intuition applies to crisis LABELS, not to vol-band labels —
  a labeler with slower dynamics (e.g., NBER-recession-anchored or
  drawdown-regime labels) is the right instrument for the fourth cell and
  is now the top data-design priority for the CRSP follow-up.

---

# PRE-REGISTRATION B — the slow-dormancy (drawdown) labeler (written 2026-07-14 BEFORE any L3 run; follows directly from the addendum's last bullet)

**Motivation (stated before running):** L1/L2 produce regimes that cycle in
days, so gate 2 never sees crisis-scale dormancy. L3 is designed for it.

**L3 labeler (causal):** on the equal-weight log-price index, drawdown
dd_t = 1 − exp(lp_{t−1} − max_{s≤t−1} lp_s); crisis state = dd > 15%;
crossed with 50-day trend sign (both via t−1 data only) → 4 regimes:
0 calm-up, 1 calm-down, 2 crisis-up, 3 crisis-down. Expected crisis
episodes in 1990–2025: 2000–03, 2008–09, 2020, 2022 clusters, with
multi-YEAR dormancy between them.

**Design:** identical to pre-registration A in every other respect (same
features, same gate-1 criteria with 50 shuffles, same gate 2, same ten
arms/pairs/Holm, walk-forward primary + stitched secondary, min_dormancy
90, probe 15). The gate-1 family grows to THREE cells total (L1, L2, L3);
we disclose Bonferroni ×3 and note L3 was designed after seeing L1/L2
GATE results but before seeing any L3 statistic.

**Predictions:** P5 (gate 1 on L3, ~50%): crisis-conditioned structure on
the decision metric is plausible (crisis betas differ) but the crisis
regime has few episodes (~4–6), so power is limited. P6 (gate 2 on L3,
~50%): this is the best shot the program has at a positive forgetting
deficit — multi-year dormancy at last; against it, linear heads refit in
~30 observations regardless of how long they slept, which is the E6
lesson and would predict Γ ≈ 0 yet again. P7: if BOTH pass, the
dissociation ordering emerges (the protocol's core commitment); if gate 2
fails again with multi-year dormancy, that is strong evidence the
forgetting deficit for LINEAR-HEAD specialists is structurally zero on
liquid daily data — the deployment set may be empty for this model class,
and the paper should say so (the "organizational
carrier" reading becomes the survivor).

---

# PRE-REGISTRATION C — L3 threshold-robustness sweep (written 2026-07-14 BEFORE the sweep runs; motivated by internal red-team review)

Rerun the L3 walk-forward battery (gate 2 + ten arms, identical protocol)
at dd_thresh ∈ {10%, 12%, 20%} (15% already run). Forensics already
established (episode list printed 2026-07-14, before this sweep): the
crisis union at 15% ALREADY includes the 2010/2011/2015-16/2018 near-miss
episodes; the ~2,953-day dormancy belongs to the crisis-up CELL, not the
union — the paper's current phrasing misattributes this and will be
corrected regardless of sweep outcome.

**Predictions:** P8 (~65%): Γ̂_forget > 0 and the A6<A5<A1 ordering
direction is stable across all three thresholds (magnitudes may shrink at
10-12% where crisis inventory densifies and dormancies shorten). P9: if
the deficit dies or flips at looser thresholds, the "rehearsal
hypothesis" (near-miss recalibration, not isolation, carries crisis
knowledge) gains direct support and E1f's mechanism attribution must be
revised toward it — reported at full prominence either way.

---

# ADDENDUM B — L3 results and verdicts (written 2026-07-14 AFTER the L3 runs; pre-registration B above unedited)

- **P5 (gate 1 on L3): REFUTED by the letter.** z=+2.24 clears the shuffle
  criterion (normal-fit p≈1.3e-2; empirical floor 1/51) and both halves
  are positive (+0.86%/+0.89%), but pooled beats conditioning by 0.10%,
  failing the pooled sub-criterion. Verdict: gate-1 FAIL as registered.
  (Register note, recorded after internal review: the prereg's auxiliary
  t-based p-criterion is SE-vs-SD inflated by ~√50 and non-discriminating
  — L2 passes it while failing z; the binding criteria were and remain z,
  pooled, split-half.)
- **P6 (gate 2 on L3): CONFIRMED** — first positive forgetting deficit on
  real data: walk-forward Γ̂ = +0.00091 ± 0.00020 (seed-noise CI, single
  history). Stitched Γ̂ = +0.00027 ± 0.00030 (n.s.).
- **P7: REFUTED as written.** P7 committed "if BOTH pass, the ordering
  emerges"; gate 1 failed by the letter yet the full ordering emerged in
  the walk-forward (A6<A5<A1; joint Holm 4.1e-12; A6 beats A9 Holm
  4.8e-3), and the stitched design is flat. Combined with Addendum A's P4,
  the protocol has now been refuted in both directions; the surviving
  hypothesis — Γ̂'s sign prices the pool; gate 1's pooled criterion
  measures the wrong (asymptotic) quantity — was formulated AFTER these
  results and is committed as the ex-ante hypothesis for CRSP.
- Labeler anatomy (forensics run before the threshold sweep): the crisis
  UNION recurs every 1–3 years (2010/2011/2015–16/2018 near-misses all in
  inventory); the 2,953-day dormancy belongs to the crisis-with-uptrend
  CELL. Paper text corrected accordingly.

---

# ADDENDUM C — threshold-sweep results (written 2026-07-14 AFTER the sweep; pre-registration C above unedited)

- **P8: REFUTED.** The deficit and ordering exist only at the
  pre-registered 15% cutoff. 10%: Γ̂=+0.00013±0.00027 n.s., ordering
  dissolved. 12%: Γ̂=−0.00010±0.00017 n.s. 20%: Γ̂=−0.00045±0.00026,
  monolith beats A6 (min raw p=4.6e-4) — a third inversion.
- **P9: ACTIVATED.** The fragility supports either the artifact reading
  or a granularity-window reading (rehearsal density at fine thresholds
  kills the deficit exactly as the E6/relearning axis predicts; event
  scarcity at coarse thresholds leaves nothing to harvest). 15% was fixed
  before any L3 run, so it is not a tuned peak — but robustness to the
  neighborhood is refuted and the paper says so at headline prominence.
- Combined evidential state of E1f-L3: event-robust (LORO: survives every
  single-event and all-of-2020 exclusions; era-consistent) but
  specification-fragile (threshold ±5pp kills it) on one history. Forward
  discriminating tests: CRSP constituents; NBER-anchored labeler.

---

# PRE-REGISTRATION D — replay, costs, A3′, CVaR panel, seed parity (written 2026-07-15 BEFORE any of these runs; predictions with probabilities)

- **D1 (replay, synthetic; ~70%/85%):** We predict a monolith with its
  replay buffer decoupled from head eviction closes at least 60% of the
  A1−A9 deficit (landing within CI of A9's 0.0322) while remaining
  significantly worse than A6 (0.0308); if replay+INV also matches A6,
  that confirms Proposition 1(ii)'s isolation reading — retention bought
  in data space at O(buffer) memory instead of O(d) parameters — and the
  pool's surviving claim is emergent assignment under capacity, not raw
  performance; if replay fails to close the deficit, the eviction-coupling
  mechanism is stronger than the theory requires and is reported as such.
- **D2 (replay, French L3; ~50%):** We predict replay-ERM collects most of
  the L3 deficit (Γ over the replay monolith n.s.) while A6 still beats
  it, mirroring A6-vs-A9. Pre-committed branches: replay matching or
  beating A6 relabels the E1f headline as "retention, however implemented,
  prices the pool" and withdraws the pool-specific superiority claim in
  both papers; replay failing on L3 (decade-stale crisis buffers) is
  reported as the first substrate where parameter retention beats data
  retention.
- **D3 (costs; ~70% probe survives, ~65% overall does not):** We predict
  the L3 probe-window ordering and Γ survive 25 bps crisis-window
  effective costs and strengthen with the cost tier, because a reactivated
  monolith's near-uninformed predictions churn the top-5 hardest exactly
  when spreads are widest; if the ordering dies at 25 bps, every E1f
  decision-layer claim is relabeled gross-only in both papers, per the
  standing commitment; the overall-regret margin (0.00011/day) is declared
  exploratory NOW and is expected not to survive cost adjustment.
- **D4 (A3′; ~50%):** We predict A3′ (reward-driven capital,
  reward-independent training) lands strictly between A3 and A5 — the
  organizational-carrier dissociation: expertise retained, deployment
  starved. A3′ ≈ A5 corrects the A3 narrative to training starvation
  alone; A3′ ≈ A3 establishes that capital routing by itself destroys the
  value of retained expertise.
- **D5 (CVaR panel; ~65%):** We predict the A5−A6 gap concentrates in the
  upper quantiles of per-reactivation regret (q75/q90/CVaR gaps exceeding
  the median gap) on the synthetic 100-seed battery, per the revised
  Proposition 3's interpretation; a uniform shift demotes that
  interpretation to an unconfirmed bound and is reported as such; the
  French-L3 quantile panel (27 events) is declared descriptive-only in
  advance.
- **D6 (seed parity; ~70% E1r null):** We predict E1f outcomes unchanged
  at 100 seeds and E1r-4H still null under the pre-registered Holm family.
  Pre-committed: a significant A6-over-A1 separation at Γ≈0 on 4H refutes
  the revised sign rule a third time and will be reported at headline
  prominence; a significant inversion there would instead be the sign
  rule's fourth consistent cell.
- **Implementation register for D1/D2:** decoupling = remove the buffer
  eviction in Specialist._touch (buffer survives head eviction) plus a
  GENEROUS burst-refit at head recreation (full refit on the retained
  buffer, not the 2-steps/day trickle) — committed in advance so the
  deficit cannot "survive" as an artifact of our own SGD budget.
- **Deferral rule (honest-tension flag):** D1/D2 run BEFORE the ICAIF
  submission. If compute prevents it, the ICAIF text discloses the lodged,
  unrun baseline at the same prominence as a result.

---

# PRE-REGISTRATION E — mechanism probes and out-of-sample eras (written 2026-07-15 BEFORE any of these runs)

- **E-X1 (rehearsal regression, within-event fixed effects):** Per-reactivation
  deficit Γ_i (matched A1−A9, shared deterministic schedule) regressed on
  {log cell-dormancy, log union-dormancy, rehearsal count R_i} across
  thresholds {10,12,15,20%}, with event fixed effects exploiting the same
  calendar crises appearing at multiple thresholds with different rehearsal
  histories; cluster-robust SEs + Spearman backstops (n≈18–25/threshold).
  Predictions: rehearsal reading (~40%) = Γ_i decreasing in R_i and
  union-dormancy dominating cell-dormancy → E1f attribution revised toward
  rehearsal, fragility becomes mechanism; dormancy reading (~40%) = cell-
  dormancy dominates, R_i coefficient ≈0 → isolation story stands and the
  10/12% nulls get a separate explanation (probe-overlap dilution, checkable
  from n_days); neither (~20%) = Γ not localized in identifiable
  reactivations → artifact warning at headline prominence.
- **E-X2 (granularity-window map):** thresholds 8–22% ×1pp × hysteresis exit
  bands {0,2,4,6pp}; tier 1 = A1/A9 Γ at 10 seeds, tier 2 = +A5/A6 at 20
  seeds where tier-1 CI excludes 0. **Window criterion fixed now:** Γ CI>0
  in ≥3 contiguous thresholds at some hysteresis level = window (granularity
  reading vindicated); only 15±0 positive = island (artifact reading wins,
  E1f demotes to one-specification-one-history); between = ambiguous,
  reported without adjudication.
- **E-X3 (relearning half-life):** per-day probe profiles regret(t0+j),
  j=0..14, A1 vs A9, per threshold; exponential fit → τ(θ). Prediction
  (~55%): τ(15%) ≳ probe window while τ(10/12%) ≲ 5 days — the E6 crossover
  operating on real data; anti-branch: parallel/flat profiles mean the
  deficit is a level offset, not a reactivation transient, and the
  "forgetting" label is wrong (candidate rename: allocation deficit) —
  reported plainly.
- **E-X4 (CPU emergent forgetting):** shared trunk 20→32→32 + linear heads,
  SAME architecture for all arms, NO eviction model — the monolith is one
  trunk+head; A9 pins heads sharing the trunk; forgetting can arise ONLY as
  representation interference. Minimal battery {A1,A5,A6,A9}, 20 seeds,
  SNR 1×; full 100-seed + SNR {0.5,1,4}× if minimal is clean. Predictions:
  Γ>0 emerges (~55%) → "coded, not emergent" objection dies; Γ≈0 (~45%) →
  the synthetic deficit is an artifact of the hard-memory model and the
  paper's synthetic headline takes a scope caveat at full prominence.
- **E-F (withheld era 1926–1989):** byte-identical L3@15% battery + 10/12/20%
  sweep on the 36 complete industries, window 1926-07-01–1989-12-31 (one
  era primary; 1926–57/1958–89 split reported as robustness). Inherits the
  lodged Γ-sign hypothesis and the frozen L3 spec — zero new researcher
  degrees of freedom. Predictions: granularity reading (~50%) = Γ>0 with
  ordering wherever the era contains multi-year crisis-cell dormancy, and
  threshold-fragility REPLICATES in pattern; artifact reading = deficit
  absent at 15% off-sample. Depression-era drawdowns (~85%) also probe the
  20%-threshold branch with episodes the 1990–2025 window lacks.
- **E-R (regional register):** the Γ-sign hypothesis will be tested on the
  French international daily 25-portfolio panels in this fixed region
  order: Japan, Europe, Asia-Pacific ex Japan, North America, Developed ex
  US (k=5 of 25, w_max=0.2, same battery). Region-specific prediction
  stated in advance: Japan's crisis-cell dormancy 1990–2012 is SHORT
  (crisis frequent) → Γ_Japan ≈ 0 or negative expected; Europe's rarer
  crises → positive Γ plausible. Sign-tracking is scored per region.
- **Cost convention for D3 (fixed before the cost run):** both the arm and
  the oracle benchmark pay costs (net regret = net-of-cost oracle utility
  minus net-of-cost arm utility, turnover = 0.5·Σ|z_t − z_{t−1}|·2 sides);
  the arm-only-pays variant is reported as sensitivity.
