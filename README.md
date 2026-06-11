# 🐻‍❄️ RISP: When the Regime Returns

### Regime-Invariant Specialist Pools — Retention and Invariance in Decision-Focused Strategy Pools for Non-Stationary Markets

<div align="center">

<img src="assets/cover.png" alt="The reward-chaser trashes the crisis playbook during calm markets; the RISP specialist sleeps on it — and when the regime returns, one panics and one performs." width="100%">

<br><br>

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Numbers: traced to JSON](https://img.shields.io/badge/Every%20number-traced%20to%20results%2F*.json-green.svg)](#reproducibility)
[![Honesty: 3 nulls shipped](https://img.shields.io/badge/Honest%20nulls-3%20shipped%20at%20headline-orange.svg)](#-what-did-not-survive-and-why-thats-the-point)

**The crisis specialist should idle through calm markets — and still be right about the *next* crisis, not the last one.**

[Papers](#-papers) • [Core Idea](#-the-core-idea-in-90-seconds) • [Key Results](#-key-results) • [Honest Nulls](#-what-did-not-survive-and-why-thats-the-point) • [Quick Start](#-quick-start) • [Experiments](#-experiment-map) • [Citation](#-citation)

</div>

---

## 📖 Abstract

**RISP** (Regime-Invariant Specialist Pools) is a strategy-pool architecture for decision-focused (predict-then-optimize) learning under regime-switching non-stationarity. Its claim: financial non-stationarity is **two-layered**, and the layers are owned by **different design knobs**.

- **(N1) Regimes switch and recur** with long, irregular dormancy. Any allocator that assigns capacity by chasing current reward — trailing-Sharpe capital weights, a learned MoE gate — starves and overwrites the dormant-regime specialist, *because a dormant regime emits no reward to protect itself with*. The fix is an **allocation property**: a reward-independent, covering regime→specialist assignment, which RISP reaches *emergently* via batched winner-take-all competition (the [GAUSE](https://github.com/HowardLiYH/GAUSE) mechanism, ported to decision regret) and then pins.
- **(N2) Each recurrence differs** (2008 ≠ 2020 ≠ 2022). A *retained* specialist trained by ERM still fails out-of-distribution on the next episode of its own regime — retention preserves the overfitting too. The fix is an **objective property**: train each niche on `Var_e[ℓ_e] + β·E_e[ℓ_e]` across the regime's historical episodes (an Inv-PnCO-style invariance penalty on an SPO+ decision-regret surrogate).

We prove a post-reactivation regret bound that splits into a **forgetting deficit** (zero for any reward-independent covering assignment; → full relearning cost for any reward-chasing one, at an explicit eviction rate) plus an **invariance gap** (controlled by the episode-variance penalty, with a one-step Pinsker bridge from divergence-style guarantees to regret) — and we confirm the predicted 2×2 dissociation experimentally, including its sharpest falsifiable signature: **the invariance objective is *inert* inside a reward-driven allocator** (p=0.88), because no loss function can help a head that was evicted during dormancy.

<div align="center">
<img src="assets/mechanism.png" alt="Compete -> Pin -> Retain + Generalize" width="95%">
</div>

---

## 🎯 The Core Idea in 90 Seconds

A multi-strategy fund keeps playbooks for conditions that are mostly absent. The allocation question — *who gets capital and recalibration today, and who keeps a playbook whose regime is dormant?* — has a standard answer (route by recent reward) with a structural flaw: **the regime most needing protection is the one emitting no reward.** When the regime returns, the reward-chaser relearns *during* the crisis — the exact window where decisions are most expensive.

RISP's two moves:

1. **Retention by identity, not P&L.** Specialists win regimes through competition; once converged, the assignment is pinned and stops responding to reward. The crisis specialist idles through calm markets with its heads and episode library structurally untouchable.
2. **Generalize what you retain.** The retained specialist trains across *all* stored episodes of its regime, penalizing the variance of its decision-regret surrogate across them — keeping the structure all crises share and discarding what only the last one had.

Each move is useless without the other (measured, not asserted — see the super-additive interaction below).

---

## 📊 Key Results

*Synthetic regime-switching markets calibrated to realistic daily signal-to-noise; 11 arms; 20 seeds; Welch tests with Holm correction; metric = mean decision regret in the first 15 days after a ≥90-day-dormant regime reactivates. Full tables in the papers and `results/*.json`.*

<div align="center">
<img src="assets/results_2x2.png" alt="The 2x2 dissociation" width="75%">
</div>

| Finding | Number | p |
|---|---|---|
| Retention axis (RISP-ERM vs capacity-matched monolith) | **−6.1%** | 1.3e−3 |
| Invariance axis (RISP-full vs RISP-ERM) | **−4.4%** | 6.1e−3 |
| Joint (38% of the excess over the irreducible noise floor) | **−10.3%** | 9.2e−7 |
| **Invariance inside a reward-driven monolith — inert** | −0.3% (nothing) | 0.88 |
| Super-additive interaction (per-seed, 95% CI excludes 0) | −0.0015 ± 0.0005 | — |
| RISP-full vs **hand-pinned oracle assignment** (same objective) | indistinguishable | 0.72 |
| Learned MoE router vs monolith | indistinguishable (both forget) | 0.83 |
| Recent-performance capital allocator (industry baseline) | **worst learning arm** (its capital floor erodes dormant desks continuously) | — |
| Hedge over fixed strategies / over learning experts | retains-but-can't-adapt / adapts-but-forgets | — |

**Boundary sweeps:** the RISP arms are flat in capacity K (reward-driven arms close the gap only at K=R under hard slots — and *never* under graded interference); the retention gap grows with dormancy and saturates once eviction is near-certain (~1 quarter); the ERM-vs-invariant gap widens 2.4× as episode heterogeneity rises; and a break-even analysis prices retention against idle-desk carrying costs (above ~15% relative carrying cost, *no* dormancy length justifies a dedicated specialist — "let it decay" is sometimes rational).

---

## 🔍 What Did NOT Survive (and why that's the point)

This project treats its own claims the way it treats market structure: **gate first, claim second.**

<div align="center">
<img src="assets/honest_audit.png" alt="E6 inversion and E0 null" width="95%">
</div>

1. **The real-data gate failed — we shipped the null.** A pre-registered structure diagnostic (oracle regime-conditioning vs block-shuffled labels, *on the decision metric*, two causal leakage-free labelers) finds **no exploitable regime structure** in our real panels (5 Bybit crypto pairs, 3 FRED commodities, daily). The full 11-arm experiment on regime-stitched real crypto is consequently **flat (all p > 0.2)** — exactly what the failed gate predicts. The same machinery that separates arms at p~1e−6 where structure exists goes flat where it doesn't. *An evaluation that cannot go flat should not be trusted when it goes sharp.* The equities flagship (S&P 500 constituents, 1990–2025, with 7 crisis episodes) is the pre-registered next test.
2. **Our batching story was refuted by our own ablation.** We pre-registered that per-step competition would converge to noise at market SNR (hence 20-day windows). Wrong: performance is flat across windows of 1–60 days — the EG affinity accumulation across windows does the averaging. Reported as a revision, with the corrected mechanism story.
3. **The mechanism inverts where signal is strong.** At 4–8× our baseline SNR, greedy episode-chasing ERM *beats* invariant retention by up to **49%** (the oracle skyline inverts identically — it's the regime, not our mechanism). The audit exists because our own first prototype, built at unrealistically high SNR, showed nothing — we promoted the failure to an experiment. The deployment boundary is a measured crossover, not a caveat.

---

## 🚀 Quick Start

```bash
git clone https://github.com/HowardLiYH/RISP.git
cd RISP
pip install numpy scipy pandas matplotlib   # that's the whole stack — no GPU

cd code
python run_experiments.py e1   --seeds 20   # headline 2x2 (11 arms)
python run_experiments.py e0               # real-data structure gate
python run_experiments.py e2               # capacity sweep (hard + soft memory)
python run_experiments.py e3               # dormancy sweep / break-even
python run_experiments.py e4               # episode-heterogeneity sweep
python run_experiments.py e5               # ablations (beta, W_c, lambda, pinning)
python run_experiments.py e6               # the honest SNR audit
python make_figures.py all                 # regenerate every paper figure
```

The full battery reruns in **under an hour on a laptop**. Every experiment writes a JSON to `results/`; every number in the papers traces to one.

---

## 🧪 Experiment Map

| ID | Question | Result file |
|---|---|---|
| **E0** | Does regime structure exist on the *decision* metric in real data? (gate) | `e0_structure_diagnostic.json` |
| **E1** | The headline 2×2 + 11-arm dissociation | `e1_synth.json` |
| **E1s** | Same arms on regime-stitched real crypto (null, as E0 predicts) | `e1s_stitched_crypto.json` |
| **E2** | Capacity sweep K=1..R, hard LRU vs soft interference | `e2_capacity_sweep.json` |
| **E3** | Dormancy sweep + break-even carrying-cost window | `e3_dormancy_sweep.json` |
| **E4** | Episode heterogeneity isolates the invariance axis | `e4_heterogeneity_sweep.json` |
| **E5** | β / competition-window / niche-bonus / pinning ablations | `e5_ablations.json` |
| **E6** | The audit: where does the mechanism stop paying — and invert? | `e6_snr_audit.json` |

**The 11 arms:** monolith (ERM/INV), reward-trained MoE router, recent-performance capital allocator, random fixed niches, RISP (ERM/full), Hedge over fixed strategies, Hedge over learning experts, and hand-pinned oracle assignments (ERM/INV — the skylines). All share identical specialists, learning rates, and data; they differ **only** in who learns what when, and with which loss.

---

## 📄 Papers

| Document | What it is |
|---|---|
| [`paper/main.pdf`](paper/main.pdf) | The research paper (19 pp, NeurIPS format): theory, 2×2, audits |
| [`paper/RISP Explainer.pdf`](paper/RISP%20Explainer.pdf) | Explanatory companion (18 pp): architecture, worked demos, applications, when-not-to-use |
| [`paper/Deep Dive.pdf`](paper/Deep%20Dive.pdf) | Mathematical deep dive (80 pp): every proof from first principles, full experimental tables, code walkthrough |
| [`NEXT_STEPS_AND_REVIEW.pdf`](NEXT_STEPS_AND_REVIEW.pdf) | Frank self-review: what's strong, what a referee will attack, deferred items + costs |
| [`CHANGELOG.md`](CHANGELOG.md) | The research journey, including everything that went against us |

---

## 🧬 Relation to GAUSE and Inv-PnCO

RISP is the financial, decision-focused successor to **[GAUSE](https://github.com/HowardLiYH/GAUSE)** (reward-independent capacity assignment defeats catastrophic forgetting in learner populations) and imports the **environment-indexed invariance** idea of Inv-PnCO (invariant predict-and-optimize under distribution shift), with episodes-of-a-regime as environments. Its two novel moves: the **decomposition** showing retention and invariance are independent knobs with a super-additive product, and the **Pinsker bridge** converting divergence-style invariance guarantees into the decision-regret currency.

## 🔬 Reproducibility

Seeded end-to-end (schedule, market, and each arm's RNG derive from the seed; arms within a seed see identical data — a paired design). Statistics: Welch tests, Holm–Bonferroni within pre-registered pair families, 95% CIs over seeds. **No claims of live-market alpha are made anywhere** — by the E0 gate, the panels where such claims could have been manufactured do not carry the structure that would make them meaningful.

## ⚠️ When NOT to Use This

No verifiable regime structure (run E0 first — ours failed!); strong fast-learnable within-regime signal (the E6 inversion); no real dormancy; slack capacity with hard isolation; carrying costs above break-even. Each boundary is measured, not assumed — see the Explainer §"When Not to Use It".

## 📚 Citation

```bibtex
@misc{li2026risp,
  title  = {When the Regime Returns: Retention and Invariance in
            Decision-Focused Strategy Pools for Non-Stationary Markets},
  author = {Li, Yuhao},
  year   = {2026},
  note   = {RISP. Code and papers: https://github.com/HowardLiYH/RISP}
}
```

## 📜 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">
<sub>🐻‍❄️ <b>The wager of this research program:</b> in non-stationary worlds, <i>who is allowed to keep knowing things</i> — and <i>what they are trained to keep knowing</i> — matter more than how well anything is known today.</sub>
</div>
