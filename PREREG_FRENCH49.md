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

---

# ADDENDUM F — verdicts for addenda D and E (written 2026-07-15 AFTER the runs; registrations above unedited)

- **D1 (replay, synthetic): REFUTED by the letter, favorably.** Closure
  56.3% < the committed 60% (A1r-erm−A9 = +0.00073±0.00025, p=0.011) —
  the anti-branch activates: eviction-coupling is STRONGER than the theory
  requires. Second leg CONFIRMED: replay ≪ A6 (p=7.0e-14); replay+INV
  still worse than A6 (Holm 0.040) and A10 (Holm 0.017).
- **D2 (replay, French L3): CONFIRMED (primary branch).** Replay collects
  ~99% of the deficit (Γ over replay +0.00001±0.00023 n.s.) — data
  retention ≈ parameter retention vs the ERM oracle — yet **A6 still
  beats replay** (Holm 0.013; A6 vs replay+INV Holm 4.5e-4). Neither
  relabeling branch triggers; the pool-superiority claim survives its
  most dangerous baseline.
- **D3 (costs): CONFIRMED, beyond the prediction.** Γ_net strengthens
  monotonically with cost tier: +0.00126±0.00020 (25bps) → +0.00161 (50)
  → +0.00230 (100); full ordering at every tier (Holm down to 4.6e-19);
  mechanism as predicted (A1 turnover 1.03/day vs A6 0.62). The lodged
  "overall margin expected NOT to survive" is REFUTED in the favorable
  direction (survives and strengthens ~10×). **The L1 inversion REVERSES
  net of costs** (A6 beats A1, p=1.2e-16): the inversion, not the
  deficit, was the gross-only phenomenon. Gate-1 cost slice (sensitivity,
  not re-adjudication): L3 cond-vs-pooled −0.10% gross → +3.0% net.
- **E-X1 (rehearsal regression): NEITHER branch (the ~20% outcome).**
  No dormancy/rehearsal covariate explains Γ_i (all registered slopes
  n.s., pooled and within-event); probe-overlap dilution ruled out
  (≤4.4%). Per the register: artifact warning at headline prominence —
  now to be read jointly with D3/E-F (the effect is real and
  cost-amplified but not dormancy-mechanistic).
- **E-X3 (half-life): ANTI-BRANCH.** At 15% the A1−A9 gap does NOT decay
  across the probe (tail ≥ start; all-cell fits R²<0.2): a level offset,
  not a relearning transient. The registered rename applies — the
  quantity behaves as an ALLOCATION deficit (regime-conditional service
  gap), not eviction-forgetting. Where a true transient exists (20%),
  it relearns in 2–4 days and nets to zero (the E6 mechanism).
- **E-X4 (emergent forgetting): CONFIRMED, replicated, with one lodged
  divergence.** Γ-mlp = +0.01009±0.00037 at 100 seeds (p=1.9e-78),
  reactivation-localized (4× probe vs steady) — interference measured,
  not injected; the "coded, not emergent" objection dies. Honest null:
  A6-vs-A5 invariance effect absent under the MLP (p=0.13). Divergence
  at full prominence: the E6 inversion does NOT reproduce at 4× SNR
  (Γ grows ~5× instead); post-hoc architectural caveat recorded in the
  JSON (single readout vs regime-keyed heads — not apples-to-apples).
- **E-F (withheld era 1926–1989): the decisive record.**
  Gate 1 passes at z=23.5 (strongest in program) while the frozen 15%
  spec INVERTS (Γ=−0.00024±0.00008) — gate 1 again dissociates from pool
  value. Sweep: dissociation at 10% (Γ=+0.00020, ordering Holm 1.9e-6),
  flat at 12/20%. Sub-eras at 15%: 1926–57 inversion (Holm 0.023);
  **1958–89 Γ=+0.00021 with the full ordering (Holm 2.1e-4)**. Sign-rule
  scorecard: **5 of 6 withheld cells consistent, both directions,
  including two positive-side confirmations**; one conservative miss
  (12%: Γ marginally negative, table flat — a hit under the weak "iff
  significantly positive" form, a miss under the strong directional
  form; both scorings reported). Granularity clause 1 REFUTED (multi-year
  dormancy everywhere, sign varies); fragility pattern replicates but the
  window RELOCATES (15%→10%) with crisis density; artifact reading
  confirmed at the letter for 15%-off-sample yet undermined as a full
  account (the phenomenon reappears off-sample with full ordering).
- **D6 (seed parity, French): L1 complete at 100 seeds** — gates
  unchanged; wf inversion stands with Γ now negative-significant
  (−0.00013±0.00007); stitched Γ turns marginally positive
  (+0.00023±0.00015) — a new wrinkle disclosed here. L3 100-seed run
  completing; verdict to be appended when saved.
- **Synthesis (the surviving claims):** (1) Γ̂'s sign prices the pool —
  now 5/6 on withheld data, cost-robust, replay-tested; (2) the deficit,
  where positive, is real economics (amplified net of crisis-window
  costs, collected by replay on real data but the invariance-equipped
  pool still wins); (3) its mechanism on real data is NOT
  eviction-forgetting (X1/X3/E-F clause-1) — the honest name is a
  regime-conditional allocation deficit, and the synthetic/MLP forgetting
  transient remains a distinct, controlled-setting phenomenon; (4) gate 1
  does not price the pool and is demoted to a structure screen.

- **D6 verdict, completed:** L3 at 100 seeds — walk-forward Γ=+0.00089
  ±0.00011 with the full ordering (min Holm 1.4e-65; seed-noise precision,
  single-history caveat unchanged), reproducing the 20-seed result;
  stitched Γ turns marginally positive-significant (+0.00023±0.00016)
  with the same ordering direction (family flat, min raw p=0.50) — the
  schedule-resampling design now leans the deficit's way, disclosed as a
  favorable wrinkle. Prediction "outcomes unchanged" CONFIRMED.

---

# CUSTODY UPDATE (2026-07-15, 22:47 ET)

This document (as the snapshot PREREG_FRENCH49_snapshot_2026-07-15.md),
PREREG_CRSP.md, and PREREG_NBER_FRENCH49.md were lodged with the Open
Science Framework: project osf.io/nsx4e (created 2026-07-15 22:45 ET,
files uploaded 22:47 ET). The NBER-labeler forward test is UNFROZEN as of
this lodging; NBER dates had not been joined to any panel before this
point. All future registrations in this program are OSF-first.

---

# ADDENDUM G — NBER forward-test verdicts (written 2026-07-15 ~23:15 ET, AFTER the run; registration lodged at osf.io/nsx4e 22:47 ET; NBER dates first joined to the panel 22:55 ET)

- **PN1 (H-SIGN): HIT, weak AND strong forms, on the primary
  (announcement-lagged, causal) walk-forward cell.** Γ̂ = +0.00081±0.00033
  (net-25bps +0.00105±0.00033, the D3 amplification pattern on a labeler
  D3 never saw) with the ordering Holm-significant (A6<A1 1.6e-4 gross;
  full A6<A5<A1 chain ≤3.1e-5 net, A6<A9 1.7e-3 net). Neither lodged
  refutation clause triggered. Primary stitched: Γ̂ n.s. with flat table —
  hit under both forms. Calendar (non-causal robustness): wf hit/hit;
  stitched Γ̂ negative-significant with flat table — weak hit, STRONG-FORM
  MISS (the E-F 12% pattern), disclosed.
- **PN2: CONFIRMED** (walk-forward; single-history seed-noise caveat
  verbatim; stitched flat).
- **PN3: the granularity/window branch obtains** — a labeler with no free
  threshold anywhere reproduces the positive deficit with ordering; the
  artifact reading of L3's 15% cutoff loses this discriminator.
- **PN4: satisfied** — all four cells, both variants, gross and net, raw
  seeds, and the strong-form miss in the JSONs; no selective emphasis.
- Gate 1 FAILED in both cells (z=1.74/1.35; pooled edges conditioning)
  while the pool priced positive — the third independent dissociation of
  gate 1 from pool value.
- **Disclosed omission (owed):** the lodged LORO + era-blocked analyses
  for this cell were not run in this pass (recorded in the JSONs'
  meta.disclosed_omissions); the cell is not to be cited as complete
  until they exist.
- Announcement dates verified against nber.org and recorded in the JSONs;
  endpoints inclusive; recession-cell dormancies 2,445/2,557 trading days
  (primary), matching the 1992→2001→2008→2020 gaps.

- **Addendum G supplement (2026-07-16): the owed LORO/era slices are run**
  (results/e_french49_nber_loro.json; sanity-reproduces Γ̂ exactly).
  Disposition, stated in full: survives all 20 single-event and all
  calendar exclusions (drop-2020 +0.00042±0.00026; drop-2008/09
  +0.00036±0.00030) — not single-event-carried — but concentrated in the
  two deep-dormancy recession entries (2009-01-06 d=1378; 2020-06-08
  d=2445; dropping the former cuts Γ̂ to 41% of headline and extinguishes
  the A1−A6 contrast), and the 2010s era block is NEGATIVE-significant
  for both contrasts (that block contains zero recession-cell
  reactivations — premium-without-claims at cell level, flagged as
  interpretation). Event-robust strictly; two-recession-concentrated;
  not era-consistent; materially weaker than the L3 cell's profile. The
  cell is now citable as complete, carrying this sentence.

---

# PRE-REGISTRATION H — the banded monolith (turnover-discipline control) (written 2026-07-16 BEFORE any run; motivated by the practitioner review's standing demand)

**Question:** is the pool's net-of-cost advantage purchasable for free with
a no-trade band on the monolith? The cost battery showed A1 churns
1.03/day vs A6's 0.62 exactly when spreads are widest; a band is the
cheapest desk countermeasure and must be tested before the net-cost
claims are cited as pool-specific.

**Arm A1b (banded monolith):** identical to A1 except the served
portfolio updates only when the newly ranked top-k differs from the
held book by more than a hysteresis band; two lodged variants,
b ∈ {1 name, 2 names} (update only if ≥b+1 names would change). No other
changes; training identical to A1.

**Battery:** French-49 L3@15% walk-forward and L1 walk-forward (the two
cells where the net claims live), arms {A1, A1b(1), A1b(2), A9, A6},
20 seeds, standard conventions, gross and net-25bps (both-pay).

**Predictions:** PH1 (~55%): banding materially cuts A1's net cost drag
(turnover falls ≥30%) but does NOT close the net gap to A6 on L3
(selection quality, not just churn, carries part of the deficit).
PH2 (~30%): banding closes most of the L1 net reversal (where Γ≤0, the
pool's net win was mostly discipline — the turnover-discipline product
is buyable with a band there, and the paper's L1-reversal sentence is
relabeled accordingly). PH3 (adverse, ~15–20%): banded-A1 ≈ A6 net on
L3 too — the pool's net-of-cost superiority claim is withdrawn in favor
of "any turnover-disciplined implementation collects it," reported at
full prominence per the standing commitment.

---

# ADDENDUM I — verdicts for addenda H, D4, D5 (written 2026-07-16 AFTER the runs; registrations above unedited)

- **PH3 (adverse branch): REFUTED — the pool's net-of-cost superiority
  SURVIVES the banded countermeasure.** A6 beats both banded monoliths
  net-25bps on L3 (Holm ≤7.1e-17; gap ≥79% intact) and on L1 (residual
  +0.00028±0.00011, Holm 2.1e-5). Banding is free (gross unharmed, net
  improves) yet cannot buy the pool's advantage.
- **PH1: substantive clause CONFIRMED a fortiori; lodged magnitude
  FAILED.** The registered bands cut turnover only 4.1%/15.7% (<30%
  lodged) — A1's churn comes from >2-name daily re-rankings that defeat
  narrow bands — while the net gap to A6 stands. "Selection quality, not
  just churn, carries the deficit" holds.
- **PH2: PARTIAL; relabeling clause NOT triggered.** b=2 closes 62% of
  the L1 net reversal on magnitude; the residual A6 advantage remains
  significant. The L1-reversal sentence keeps its label with the
  attenuation reported alongside.
- **D4: a FOURTH, UNREGISTERED outcome — A3′ is strictly WORSE than A3**
  (0.04580 vs 0.03748; Holm 1.7e-68), audited not-artifact (training
  intensity matched 1.000 vs 1.001 calls/day; serving path verbatim
  A3). Mechanism: under A3 the capital leader holds a head for the
  active regime 94.6% of days (reward-coupled training is
  self-correcting on the serving side); under A3′ only 39.7% — lagged
  capital routes serving to the previous regime's owner, which under
  siloed training holds nothing for the active regime.
  Reward-coupled SERVING alone is anti-selective at switches. Reported
  at full prominence as an unpredicted cell.
- **D5: the upper-quantile concentration prediction FAILS on synthetic**
  (gap ratios to median: q75 1.09, q90 0.68, CVaR@10% 0.43; all Holm
  n.s.; CVaR leans OPPOSITE). Pre-committed language applies verbatim:
  the tail interpretation of the CVaR-form decomposition is demoted to
  an unconfirmed bound. The French-L3 panel (descriptive-only as
  lodged) leans the predicted way (median +0.00062 → CVaR +0.00264),
  unscored.
- Regression proofs: byte-identical 2-seed e1 (sha256 match) before/
  after all edits; banded battery reproduces the D3 cost series per-seed
  exactly. All open registrations are now closed except the two
  market-clock forward tests (temporal-deployment 2027-04-07; CRSP).

---

## Addendum J (2026-07-20): Expanding-window baseline (D7) and probe/dormancy sensitivity (D8)

Written and pushed BEFORE any implementation or run (git-separated
custody; this commit contains PREREG_FRENCH49.md alone). Verdicts will be
appended below after the runs, with this section unedited.

### D7 — the expanding-window monolith (arm A1e-expwindow)

**Question:** the most common desk deployment is not A1's implicit
recency window — it is a single model retrained on ALL accumulated
history. Does the ICAIF class sentence ("A1 represents every allocation
policy whose training resource follows current reward") cover it, and
does data retention WITHOUT parameter isolation collect the deficit, as
the decoupled-buffer replay arm A1r did (98.7% of Γ)?

**Arm A1e-expwindow (additive):** a capacity-matched monolith identical
to A1 except trained, every day, on the union of ALL stored episodes
across ALL regimes — an expanding window with no regime conditioning and
no recency weighting.

Implementation register (lodged before coding):
- Additive only: new classes + one `EXTRA_ARM_FACTORIES` entry in
  `code/risp.py`; no existing class or factory touched. Regression proof
  owed: byte-identical 2-seed e1 JSON (sha256) before/after the edit,
  per the D1/H convention.
- One weight vector serves every regime (no regime conditioning makes
  per-regime heads meaningless); `decide(X, r)` ignores `r`. Parameter
  count is d vs A1's K·d = 2d — a capacity DISADVANTAGE for A1e that we
  accept and disclose; if A1e nonetheless collects the deficit the
  conclusion is a fortiori.
- Training budget identical to A1: 2 SGD steps per day, same lr, same
  minibatch sampler (`_sgd_step` inherited unchanged). The episode
  buffer is global, keyed (regime, episode), appends every day, and is
  NEVER evicted or capped (A1 caps at 6 episodes × 40 days per regime;
  A1e's window expands without bound). Each ERM step samples one stored
  episode uniformly — exactly how A1r accesses its retained buffer at
  burst-refit, but unconditionally on every day rather than only at
  reactivation.

**Battery:** French-49 L3@15% walk-forward (the headline Γ>0 cell),
arms {A1-monolith-erm, A9-oracle-pinned, A5-risp-erm, A6-risp-inv,
A1r-replay-erm, A1e-expwindow}, 20 seeds, per-arm seeding 1311*s+17,
K=2, hard memory, probe 15, min_dormancy 90 — mirroring
`e_french_L3_replay.py` exactly. Output
`results/e_french49_L3_expwin.json` with post_react means/ci95, paired Γ
contrasts (A1−A9, A1−A1e, A1e−A9) and Welch/Holm p-values in the
battery's convention.

**Deficit-collection metric:** share = Γ(A1−A1e) / Γ(A1−A9), paired
means over the 20 common seeds (A1r's share on this cell is 98.7%:
0.00090/0.00091).

**Lodged predictions (probabilities BEFORE running):**
- **PJ1 (p=0.55):** A1e collects ≥80% of the A1−A9 deficit — it behaves
  like A1r: retention of the data alone, without parameter isolation,
  is enough on this cell.
- **PJ2 (p=0.30):** A1e sits strictly between A1 and A1r, collecting
  20–80% of the deficit (mixing all regimes into one head costs part of
  what retention buys).
- **PJ3 (p=0.15):** A1e ≤ A1 (collects <20%, or is worse than A1), or a
  fourth unlodged outcome (e.g. A1e's steady-state degrades enough that
  post-react comparisons are confounded).

**Adverse branch, stated in advance at full prominence:** if A1e
collects the deficit (PJ1), then the ICAIF class sentence "A1 represents
every allocation policy whose training resource follows current reward"
is FALSE as written — A1e's training resource follows current reward on
serving-day mixture only trivially, and it escapes the deficit. The
sentence must be narrowed to RECENCY-DRIVEN policies (training resource
follows current reward AND discards or evicts dormant-regime data), and
the narrowing is reported at full prominence in both papers, not in a
footnote.

### D8 — probe-length and dormancy-threshold sensitivity (L3 walk-forward cell)

**Question:** the registered primary reads Γ at probe N_p=15,
min_dormancy=90. Is the sign an artifact of that measurement window?

**Cells (7 lodged, 6 unique):** N_p ∈ {5, 10, 15, 30} at fixed
min_dormancy=90, and min_dormancy ∈ {60, 90, 120} at fixed N_p=15; the
duplicate (15, 90) cell is the registered primary re-read at 10 seeds
for like-for-like comparison.

**Design (declared):** 10 seeds each (reduced-seed robustness register —
seed-noise CIs will be wider than the 20-seed primary; this is a
sensitivity scan, not a headline estimate). Seeding 1311*s+17, s ∈ 0..9,
walk-forward only, arms {A1-monolith-erm, A9-oracle-pinned}. Because
probe and min_dormancy enter `run_arm` ONLY through the post-hoc
evaluation masks (they touch no training or serving path), each seed's
daily trajectory is computed once and the 6 cells are measurement
re-reads of the same 10 trajectories — exactly like-for-like across
cells by construction; we declare this rather than pretend 60
independent runs. Γ = paired A1−A9 post-react per cell. Output
`results/e_french49_L3_sensitivity.json`: per cell Γ mean±ci95,
positive-significance flag, n_react.

**Lodged prediction PJ4 (p=0.8):** Γ's SIGN is stable (positive) across
all 6 cells. Magnitude may drift with N_p (shorter probes concentrate on
the relearning transient, longer probes dilute it) — no direction is
lodged for the magnitude. If any cell flips sign significantly, that is
a MISS, reported with the specification-fragility sentence already
attached to this cell (Addendum C) — the cell's honest state would then
be fragile in BOTH the labeler threshold and the measurement window.

## Addendum J verdicts (written 2026-07-20 AFTER the runs; registration above unedited)

- **D7: the MIDDLE branch PJ2 (lodged p=0.30) won, not the modal PJ1
  (p=0.55).** A1e collects **73.0%** of the A1−A9 deficit — inside PJ2's
  20–80% band, below PJ1's ≥80% threshold. A1e post_react
  0.021832±0.000228; paired contrasts: A1−A1e = +0.000667±0.000276
  (positive-significant; Holm 4.1e-4), A1e−A9 = +0.000247±0.000254 (NOT
  significant), A1−A9 = +0.000914±0.000201 (headline, reproduced
  exactly). A1r's share on the common seeds: 98.7%. A6 beats A1e (paired
  +0.000523±0.000276; Holm 1.8e-3), so the pool retains a significant
  edge over the expanding window.
- **The lodged adverse consequence for the ICAIF class sentence is
  TAKEN, with the trigger scored honestly.** The lodged trigger was PJ1
  (≥80%); the outcome fell in PJ2 at 73.0%. But the operative fact the
  adverse branch was written for obtains regardless of the 80% line:
  A1e's residual deficit vs A9 is statistically indistinguishable from
  zero while A1's is Holm-significant at 8.2e-12 — an expanding-window
  policy trained on all accumulated data is NOT in A1's behavioral
  class. The sentence "A1 represents every allocation policy whose
  training resource follows current reward" is therefore narrowed to
  RECENCY-DRIVEN policies (training resource follows current reward AND
  dormant-regime data is discarded or evicted), at full prominence in
  both papers per the lodged commitment. Data retention without
  parameter isolation collects most of the deficit (A1r 98.7%, A1e
  73.0%); what parameter isolation (A6) still buys over A1e is
  significant and reported alongside.
- **Battery-level like-for-like proof:** the five arms shared with the
  D2 replay battery reproduce e_french49_L3_replay.json's post_react
  means EXACTLY (same seeds, same factories, same schedule) — the D7 run
  is a strict superset re-read, not a new configuration.
- **D8: PJ4 (p=0.8) CONFIRMED — Γ's sign is positive-significant in ALL
  6 cells.** probe5/90: +0.001343±0.000541 (n_react 27); probe10/90:
  +0.001242±0.000331 (27); probe15/90 (primary re-read, 10 seeds):
  +0.001100±0.000255 (27; consistent with the 20-seed headline
  +0.000914±0.000201, wider CI as declared); probe30/90:
  +0.000574±0.000108 (27); probe15/60: +0.001034±0.000136 (44);
  probe15/120: +0.001165±0.000323 (20). The L3 measurement window is
  not carrying the sign.
- **Unlodged descriptive observation (labeled as such, no lodged
  direction existed):** per-day Γ declines monotonically with probe
  length (13.4 → 5.7 bps/day from N_p=5 to 30) while the CUMULATIVE
  deficit Γ×N_p saturates: 67 → 124 → 165 → 172 bps·day — the
  relearning transient is mostly complete within ~15 days, consistent
  with the registered probe sitting near the saturation knee. Post-hoc,
  descriptive only.
- Regression proofs: 2-seed e1 JSON byte-identical (sha256
  cc5987144b11380f93b8ae07fe1aeda50e006debe00361d2518f9296ca57e33c)
  before/after the additive risp.py edit, per the D1/H convention; plus
  the battery-level exact reproduction above.

## Addendum K (2026-07-20): Event-level inference (K1), expanding-window at full seed budget (K2), decision-layer perturbation (K3)

Lodged BEFORE any of the three scripts below exist. Same discipline as
Addenda D/E/H/J: this section is committed and pushed ALONE; code and
results follow in later commits; verdicts are appended below this line
without editing the registration.

### K1 — Event-level inference on the LORO per-reactivation Γ values

**Honest scoping — analysis-plan registration, not data custody.** The
per-reactivation Γ values this test will consume are ALREADY released:
`results/e_french49_L3_loro.json` and `results/e_french49_nber_loro.json`,
field `contrasts/A1_minus_A9/per_reactivation_gamma[*].gamma_i_mean`
(n=27 for the L3 cell, n=20 for NBER), and their means/SDs were already
quoted in the paper's power guidance. Nothing here is unseen data. What
this addendum registers is the ANALYSIS PLAN — the tests, sidedness,
alpha, and consequences — before any of these tests are computed.

Plan, per cell (L3 walk-forward; NBER walk-forward):
- One-sided sign test (H1: median per-event Γ > 0): scipy
  `binomtest(n_positive, n, 0.5, alternative='greater')`. Zeros, if any,
  are dropped from n (standard sign-test convention; none expected).
- One-sided Wilcoxon signed-rank (H1: pseudomedian > 0),
  `alternative='greater'`.
- Event-level one-sample t on the gamma_i_mean values, reported as
  DESCRIPTIVE only (the events are not iid draws — dormancy and era
  cluster them; the sign test and Wilcoxon are the registered tests).
- Alpha 0.05 per test, no multiplicity correction across the two cells
  (each cell's verdict stands alone, as in the LORO registration).
- Script: `code/e_event_level.py`; output
  `results/e_event_level_inference.json` with per-cell n, n_positive,
  median in bps, both p-values, and the descriptive t.

**Lodged predictions:**
- PK1a (p=0.75): L3 sign test p < 0.05.
- PK1b (p=0.70): L3 Wilcoxon p < 0.05.
- PK1c (p=0.45): NBER passes BOTH tests at p < 0.05. (Lower confidence
  lodged deliberately: the NBER cell's mass sits in two recessions, and
  the LORO supplement already showed drop-Jan-09 attenuation to 41% of
  headline; 20 events with clustered mass can fail a median test even
  when the mean survives.)

**Adverse branch (binding):** if a cell fails at event level (either
registered test at p ≥ 0.05 for that cell), the paper's headline claim
for that cell is restated in the seed register explicitly labeled
IMPLEMENTATION-PRECISION-ONLY (the seed-level CI measures Monte-Carlo
precision of the pipeline, not event-level generality), and the
event-level failure is disclosed in the abstract-adjacent text at full
prominence — not in a footnote.

### K2 — D7 expanding-window battery at the full 100-seed budget

Rerun the Addendum J D7 battery exactly — same six arms {A1, A9, A5,
A6, A1r-replay-erm, A1e-expwindow}, same config (L3 walk-forward, K=2,
hard memory, probe 15, min_dormancy 90, dd 15%), same per-arm seeding
1311*s+17 — at seeds=100 instead of 20. The 20-seed run left A1e−A9 at
+0.000247±0.000254 (n.s.); 100 seeds shrinks the CI by ~sqrt(5) to
roughly ±0.000114, so this is a genuine test of whether the residual is
a small positive effect or noise. Output:
`results/e_french49_L3_expwin_100s.json`.

**Lodged predictions:**
- PK2a (p=0.60): A1e's deficit share collected lands in 55–85%
  (20-seed point estimate was 73.0%).
- PK2b (p=0.50): A1e−A9 is positive-significant at 100 seeds
  (mean − 1.96·SE > 0).

**Branches (both directions lodged):**
- If PK2b HITS (residual significant): the paper says an
  expanding-window desk faces a SMALL BUT REAL residual, ~2–3 bps on
  the post-reactivation register, alongside the existing narrowed class
  sentence. A6's edge over A1e is restated with the 100-seed numbers.
- If PK2b MISSES (residual stays n.s. at the full budget): the current
  wording stands — data retention without parameter isolation collects
  most of the deficit and the residual is statistically
  indistinguishable from zero — now backed by the full seed budget.

### K3 — Decision-layer perturbation (top-k robustness)

The headline decision layer is top-k selection with k=5, w_max=0.2
(gross exposure k·w_max = 1.0). Test whether Γ's sign and the A6-vs-A1
ordering survive perturbing the decision layer itself: L3 walk-forward,
arms [A1-monolith-erm, A9-oracle-pinned, A5-risp-erm, A6-risp-inv],
20 seeds, seeding 1311*s+17, K=2, hard memory, probe 15, min_dormancy
90, at two cells:
- k=3, w_max=1/3 (concentrated)
- k=10, w_max=0.1 (diversified)

w_max is scaled to hold gross exposure at 1.0 in both cells, matching
the headline's exposure, so the perturbation moves concentration only,
not leverage. Script: `code/e_french_L3_topk.py`; output
`results/e_french49_L3_topk.json` with per-cell Γ = A1−A9 paired mean
± ci95 and positive-significance flag, plus the four-arm Welch/Holm
table per cell.

**Lodged predictions:**
- PK3a (p=0.70): Γ is positive AND significant in BOTH cells.
- PK3b (p=0.65): the A6 < A1 ordering (A6 lower post-reactivation
  regret than A1) is direction-preserved in BOTH cells.

**Adverse branch (binding):** a Γ sign flip at either k is disclosed as
a DECISION-LAYER FRAGILITY at the same prominence as the labeler
threshold fragility (Addendum C) — the two fragility sentences travel
together wherever the L3 cell is quoted.

## Addendum K verdicts (written 2026-07-20 AFTER the runs; registration above unedited)

- **K1 — PK1a (p=0.75) MISS; PK1b (p=0.70) HIT; PK1c (p=0.45) HIT.**
  L3 cell (n=27, 18 positive, median +4.5 bps): sign test p=0.0610 —
  FAILS the registered 0.05 line (19/27 positives were needed; 18
  observed); Wilcoxon p=0.0159 passes; descriptive t p=0.006. NBER cell
  (n=20, 15 positive, median +4.5 bps): sign test p=0.0207 AND Wilcoxon
  p=0.0164 — both registered tests pass; the deliberately low-confidence
  PK1c prediction was wrong in the favorable direction.
- **K1 adverse branch: TRIGGERED for the L3 cell, taken in full.** The
  lodged clause fires on "either registered test at p ≥ 0.05," and the
  L3 sign test is at 0.0610. Consequence, binding: the L3 headline's
  seed-register CI is restated as IMPLEMENTATION-PRECISION-ONLY
  (Monte-Carlo precision of the pipeline, not event-level generality),
  with the event-level failure disclosed abstract-adjacent at full
  prominence — the L3 cell now carries THREE travel-together sentences
  (threshold fragility, single-history, event-level sign-test miss),
  while its Wilcoxon (p=0.016) is reported alongside as the passing
  registered test. The corresponding paper edits are OWED to the next
  paper wave (this campaign does not touch paper/). The NBER cell keeps
  its event-level standing (both tests pass) — notable because its LORO
  profile was the weaker one.
- **K2 — PK2a (p=0.60) HIT; PK2b (p=0.50) HIT.** At 100 seeds the
  headline reproduces (Γ = +0.000887±0.000110 vs +0.000914±0.000201 at
  20 seeds). A1e's collected share lands at **58.7%** — inside the
  lodged 55–85% band, though well below the 20-seed point estimate of
  73.0% (drift disclosed). **A1e−A9 = +0.000366±0.000128 — positive-
  significant at the full budget**: the PK2b HIT branch applies, and the
  paper's wording upgrades to "an expanding-window desk faces a SMALL
  BUT REAL residual (~3.7 bps/day on the post-reactivation register)"
  alongside the narrowed class sentence. A6 beats A1e by +0.000718
  ±0.000112 paired (Welch/Holm 1.4e-23). Replay remains the full
  collector: A1r share 95.8%, A1r−A9 = +0.000038±0.000121 n.s.
  (Welch p=0.52) even at 100 seeds.
- **K3 — PK3a (p=0.70) HIT; PK3b (p=0.65) HIT; no decision-layer
  fragility disclosure triggered.** k=3/w_max=1/3: Γ = +0.000268
  ±0.000244 (positive-significant, thin margin — CI lower edge +0.00002,
  disclosed); A6 < A1 direction holds with A1−A6 = +0.000580±0.000169
  paired, Holm 1.4e-4 (A6-vs-A9 and A6-vs-A5 not Holm-significant in
  this cell). k=10/w_max=0.1: Γ = +0.000495±0.000123; A6 < A1 at Holm
  3.5e-13, A1−A6 = +0.000602±0.000083 paired. Γ's sign survives the
  decision-layer perturbation in both directions.
- **Unlodged descriptive observation (labeled as such):** Γ is
  concentration-sensitive in magnitude — +0.00027 (k=3) / +0.00091
  (k=5, headline) / +0.00049 (k=10) — peaking at the registered k=5.
  No direction was lodged for magnitude; the sign, which is what the
  registered predictions and the sign rule consume, is stable. Post-hoc
  only.
