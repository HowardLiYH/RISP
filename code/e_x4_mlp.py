"""
E-X4 driver (PREREG_FRENCH49.md, addendum E): CPU emergent-forgetting probe.

Replicates the E1 protocol of run_experiments.py e1() exactly (probe=15,
min_dormancy=90, schedule rng 1000+s, market seed 5000+s shared across arms,
arm rng 99*s+7), on the minimal battery {A1-mlp, A5-mlp, A6-mlp, A9-mlp},
20 seeds, SNR 1x (SynthConfig defaults), T from make_schedule.

Pre-registered predictions (quoted verbatim in VERDICT_INTERPRETATION
below).  Gamma-mlp = A1-mlp - A9-mlp post-react, paired per-seed CI.

Usage:  python e_x4_mlp.py [--seeds N] [--pilot]
        python e_x4_mlp.py --precommit          # record expansion prediction
        python e_x4_mlp.py --expand100          # conditional expansion (1)
        python e_x4_mlp.py --snr                # conditional expansion (2)
Writes ../results/e_x4_mlp.json.  Creates no other files.

Conditional expansion (authorized 2026-07-15 after the minimal battery came
back clean, per the prereg's "full 100-seed + SNR {0.5,1,4}x if minimal is
clean"): --expand100 runs the same four arms / same protocol at 100 seeds,
SNR 1x; --snr runs the {0.5, 1, 4}x sweep at 20 seeds each, mirroring
run_experiments.e6()'s SNR mechanism exactly (cfg = SynthConfig(snr_mult=
snr); snr_mult scales theta and gamma, i.e. signal, not noise; identical
seed conventions).  Both append to the existing JSON under new keys
(expansion_100seed, snr_sweep) without touching the minimal-battery block,
and refuse to run unless the pre-committed prediction has been recorded in
the JSON first (--precommit).
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risp import (SynthConfig, SyntheticMarket, make_schedule, run_arm,
                  welch, ci95)
import mlp_arms
from mlp_arms import MLP_ARM_FACTORIES

RESULTS = Path(__file__).resolve().parents[0] / ".." / "results"
RESULTS.mkdir(exist_ok=True)

SEEDS = 20
PROBE = 15
MIN_DORM = 90

ARMS = ["A1-mlp", "A5-mlp", "A6-mlp", "A9-mlp"]

VERDICT_INTERPRETATION = {
    "gamma_positive": (
        "Gamma>0 emerges (~55%) -> \"coded, not emergent\" objection dies"),
    "gamma_zero": (
        "Gamma~=0 (~45%) -> the synthetic deficit is an artifact of the "
        "hard-memory model and the paper's synthetic headline takes a "
        "scope caveat at full prominence"),
}

HYPERPARAMS = {
    "architecture": "trunk 20->32->32 (tanh) + linear heads on the 32-dim "
                    "representation; trunk params = 20*32+32 + 32*32+32 = "
                    "1760; +33 per head; heads zero-initialised "
                    "(matches linear Specialist w=0); trunk init "
                    "N(0, 1/sqrt(fan_in)), identical across arms per seed "
                    "(same rng seed 99*s+7, same draw order)",
    "activation": mlp_arms.ACTIVATION,
    "hidden": mlp_arms.HIDDEN,
    "loss": "SPO+ decision surrogate (risp.spo_plus_loss_grad algebra), "
            "gradient w.r.t. y_hat backpropagated through head + trunk",
    "optimizer": "plain SGD, fixed lr, no momentum/decay/clipping",
    "lr": mlp_arms.LR,
    "n_steps_per_day": mlp_arms.N_STEPS_PER_DAY,
    "minibatch_days": mlp_arms.MINIBATCH_DAYS,
    "buffer": "arm-level append-only regime->episode->days store; NOTHING "
              "ever deleted or capped (no buf_days/buf_episodes caps)",
    "competition_A5_A6": {
        "n_heads": mlp_arms.N_HEADS_COMPETITION,
        "Wc": mlp_arms.WC, "eta": mlp_arms.ETA, "lam": mlp_arms.LAM,
        "pin_thresh": mlp_arms.PIN_THRESH,
        "window_winner_training": "1 step per window day at window close "
                                  "(mirrors risp.RISPArm._close_window)",
        "simplifications": "N heads on one shared trunk instead of N "
                           "capacity-K specialists (no capacity/eviction "
                           "by design); single shared append-only buffer "
                           "instead of per-specialist buffers; untrained "
                           "head serves the zero-head output instead of "
                           "1e-6 tie-break noise. Competition dynamics, "
                           "scoring, EG step, pin rule and constants "
                           "unchanged from risp.RISPArm.",
    },
    "A6_invariance": {"beta": mlp_arms.BETA,
                      "objective": "Var_e[lbar_e] + beta*E_e[lbar_e] over "
                                   "ALL stored episodes of the active "
                                   "regime (uncapped, vs linear's "
                                   "6-episode cap)"},
    "tuning": "defaults picked in advance from the linear arms' constants "
              "(lr scaled 0.08->0.05 for the deeper credit path); one "
              "single-seed pilot run to confirm learning/runtime only; "
              "no hyperparameter search / no adjustment round used",
}


def summarize(per_arm_metric: dict) -> dict:
    out = {}
    for arm, xs in per_arm_metric.items():
        xs = [x for x in xs if np.isfinite(x)]
        m, h = ci95(xs)
        out[arm] = {"mean": m, "ci95": h, "n": len(xs)}
    return out


def main(seeds=SEEDS):
    res = {a: {"overall": [], "post_react": [], "steady": []} for a in ARMS}
    pins = {a: [] for a in ("A5-mlp", "A6-mlp")}
    t0 = time.time()
    for s in range(seeds):
        cfg = SynthConfig()                       # SNR 1x, het 1.0 defaults
        rng = np.random.default_rng(1000 + s)     # E1 schedule convention
        sched = make_schedule(rng)
        for a in ARMS:
            mkt = SyntheticMarket(cfg, seed=5000 + s)   # same data per arm
            arm = MLP_ARM_FACTORIES[a](cfg, np.random.default_rng(99 * s + 7))
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM)
            for key in ("overall", "post_react", "steady"):
                res[a][key].append(m[key])
            if a in pins:
                pins[a].append(sorted(arm.pinned.items()))
        if s == 0:
            print(f"seed 0 done in {time.time()-t0:.1f}s; "
                  f"n_react={m['n_react']}, T={sched.T}")
        else:
            print(f"seed {s} done ({time.time()-t0:.0f}s)")

    # ---- Gamma-mlp: paired per-seed A1 - A9 post-react ----
    a1 = np.asarray(res["A1-mlp"]["post_react"], dtype=float)
    a9 = np.asarray(res["A9-mlp"]["post_react"], dtype=float)
    ok = np.isfinite(a1) & np.isfinite(a9)
    diffs = (a1 - a9)[ok]
    g_mean, g_h = ci95(diffs)

    # ---- pairwise Welch on post-react (pre-registered pairs) ----
    pairs = [("A1-mlp", "A9-mlp"), ("A6-mlp", "A5-mlp"), ("A6-mlp", "A1-mlp")]
    pv, tv = {}, {}
    for a, b in pairs:
        t, p = welch(res[a]["post_react"], res[b]["post_react"])
        pv[f"{a} vs {b}"] = p
        tv[f"{a} vs {b}"] = t

    # ---- verdict per the pre-committed branches ----
    ci_lo, ci_hi = g_mean - g_h, g_mean + g_h
    if ci_lo > 0.0:
        verdict_key = "gamma_positive"
        verdict = ("Gamma-mlp > 0: paired 95% CI excludes 0 from above "
                   f"([{ci_lo:.5f}, {ci_hi:.5f}]). Forgetting EMERGES as "
                   "gradient interference in the shared trunk.")
    elif ci_hi < 0.0:
        verdict_key = "gamma_zero"
        verdict = ("Gamma-mlp significantly NEGATIVE (paired 95% CI "
                   f"[{ci_lo:.5f}, {ci_hi:.5f}]): an inversion, not "
                   "anticipated by either branch; scored under the "
                   "Gamma~=0 branch (no emergent deficit) and flagged.")
    else:
        verdict_key = "gamma_zero"
        verdict = ("Gamma-mlp ~= 0: paired 95% CI covers 0 "
                   f"([{ci_lo:.5f}, {ci_hi:.5f}]). No emergent deficit.")

    out = {
        "experiment": "E-X4 (PREREG_FRENCH49.md addendum E, CPU emergent "
                      "forgetting)",
        "config": {
            "seeds": seeds, "snr_mult": 1.0, "het": 1.0,
            "probe": PROBE, "min_dormancy": MIN_DORM,
            "protocol": "run_experiments.e1 conventions: schedule rng "
                        "1000+s, market seed 5000+s (same data per arm), "
                        "arm rng 99*s+7; T from make_schedule",
            "arms": ARMS,
            "hyperparameters": HYPERPARAMS,
        },
        "post_react": summarize({a: res[a]["post_react"] for a in ARMS}),
        "overall": summarize({a: res[a]["overall"] for a in ARMS}),
        "steady": summarize({a: res[a]["steady"] for a in ARMS}),
        "gamma_mlp": {
            "definition": "A1-mlp - A9-mlp post-react, paired per seed",
            "mean": float(g_mean), "ci95": float(g_h),
            "ci_lo": float(ci_lo), "ci_hi": float(ci_hi),
            "n": int(ok.sum()),
            "per_seed": [float(x) for x in diffs],
        },
        "welch_t": tv,
        "welch_p": pv,
        "pin_assignments": {a: [dict((str(r), i) for r, i in p)
                                for p in pins[a]] for a in pins},
        "verdict": verdict,
        "verdict_branch": verdict_key,
        "pre_committed_interpretation": VERDICT_INTERPRETATION[verdict_key],
        "pre_committed_interpretation_both_branches": VERDICT_INTERPRETATION,
        "raw": res,
        "runtime_sec": float(time.time() - t0),
    }
    f = RESULTS / "e_x4_mlp.json"
    with open(f, "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"[saved] {f.resolve()}")
    print("\nGamma-mlp =", f"{g_mean:.5f} +/- {g_h:.5f}",
          f"(95% CI [{ci_lo:.5f}, {ci_hi:.5f}])")
    for kk, p in pv.items():
        print(f"  Welch {kk}: t={tv[kk]:+.2f}, p={p:.4g}")
    print("VERDICT:", verdict)
    return out


# ===========================================================================
# Conditional expansion (prereg: "full 100-seed + SNR {0.5,1,4}x if minimal
# is clean"; authorized by the coordinator 2026-07-15).
# ===========================================================================

EXPANSION_PRECOMMIT = {
    "recorded_before_expansion_runs": True,
    "snr_sweep_prediction": (
        "at 4x SNR the MLP monolith should match or beat the pinned arms "
        "(the inversion reproduces, ~60%); if instead retention keeps "
        "paying at high SNR under gradient descent, that's a genuine "
        "divergence from the linear result and must be reported at full "
        "prominence."),
    "expansion_100seed_prediction": (
        "inherits the minimal-battery E-X4 branches unchanged (Gamma>0 "
        "emerges vs Gamma~=0); no new researcher degrees of freedom."),
    "snr_mechanism": "mirrors run_experiments.e6(): cfg = SynthConfig("
                     "snr_mult=snr); snr_mult scales theta_r and gamma_"
                     "{r,e} (signal), noise untouched; same seed "
                     "conventions (schedule 1000+s, market 5000+s, arm "
                     "99*s+7).",
    "adjudication_rule_4x": (
        "primary metric post_react (Gamma convention), steady reported "
        "alongside. Let dA9 = paired per-seed A1-A9 and dA6 = paired "
        "A1-A6 post-react diffs at 4x. If either paired 95% CI has "
        "lower bound > 0 (a pinned arm still significantly beats the "
        "monolith) -> retention keeps paying -> DIVERGENCE at full "
        "prominence. Else if both CI upper bounds < 0 -> monolith BEATS "
        "the pinned arms (full inversion). Else -> monolith MATCHES the "
        "pinned arms (inversion reproduces in match form)."),
}


def _load_results() -> dict:
    f = RESULTS / "e_x4_mlp.json"
    with open(f) as fh:
        return json.load(fh)


def _save_results(d: dict):
    f = RESULTS / "e_x4_mlp.json"
    with open(f, "w") as fh:
        json.dump(d, fh, indent=1, default=float)
    print(f"[saved] {f.resolve()}")


def record_precommit():
    d = _load_results()
    if "expansion_precommit" in d:
        print("expansion_precommit already recorded; not overwriting.")
        return
    d["expansion_precommit"] = dict(EXPANSION_PRECOMMIT,
                                    recorded_utc=time.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    _save_results(d)
    print("expansion_precommit recorded.")


def run_battery(seeds: int, snr_mult: float, label: str) -> dict:
    """Same loop as main() / run_experiments.e1(), parameterized by SNR."""
    res = {a: {"overall": [], "post_react": [], "steady": []} for a in ARMS}
    t0 = time.time()
    for s in range(seeds):
        cfg = SynthConfig(snr_mult=snr_mult)
        rng = np.random.default_rng(1000 + s)
        sched = make_schedule(rng)
        for a in ARMS:
            mkt = SyntheticMarket(cfg, seed=5000 + s)
            arm = MLP_ARM_FACTORIES[a](cfg, np.random.default_rng(99 * s + 7))
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM)
            for key in ("overall", "post_react", "steady"):
                res[a][key].append(m[key])
        if s % 10 == 0 or s == seeds - 1:
            print(f"[{label}] seed {s} done ({time.time()-t0:.0f}s)",
                  flush=True)
    res["_runtime_sec"] = float(time.time() - t0)
    return res


def paired(res, a: str, b: str, metric: str) -> dict:
    xa = np.asarray(res[a][metric], dtype=float)
    xb = np.asarray(res[b][metric], dtype=float)
    ok = np.isfinite(xa) & np.isfinite(xb)
    diffs = (xa - xb)[ok]
    m, h = ci95(diffs)
    return {"definition": f"{a} - {b} {metric}, paired per seed",
            "mean": float(m), "ci95": float(h),
            "ci_lo": float(m - h), "ci_hi": float(m + h),
            "n": int(ok.sum()), "per_seed": [float(x) for x in diffs]}


def expand100(seeds: int = 100):
    d = _load_results()
    assert "expansion_precommit" in d, "record --precommit before running"
    assert "expansion_100seed" not in d, "expansion_100seed already present"
    res = run_battery(seeds, 1.0, "expand100")
    runtime = res.pop("_runtime_sec")
    g = paired(res, "A1-mlp", "A9-mlp", "post_react")
    pairs = [("A1-mlp", "A9-mlp"), ("A6-mlp", "A5-mlp"), ("A6-mlp", "A1-mlp")]
    pv, tv = {}, {}
    for a, b in pairs:
        t, p = welch(res[a]["post_react"], res[b]["post_react"])
        pv[f"{a} vs {b}"] = p
        tv[f"{a} vs {b}"] = t
    if g["ci_lo"] > 0.0:
        branch = "gamma_positive"
        verdict = ("Gamma-mlp > 0 at 100 seeds: paired 95% CI excludes 0 "
                   f"from above ([{g['ci_lo']:.5f}, {g['ci_hi']:.5f}]).")
    else:
        branch = "gamma_zero"
        verdict = ("Gamma-mlp not > 0 at 100 seeds (paired 95% CI "
                   f"[{g['ci_lo']:.5f}, {g['ci_hi']:.5f}]).")
    d["expansion_100seed"] = {
        "seeds": seeds, "snr_mult": 1.0,
        "protocol": "identical to the minimal battery (see config block); "
                    "seeds 0..99 under the same conventions",
        "post_react": summarize({a: res[a]["post_react"] for a in ARMS}),
        "overall": summarize({a: res[a]["overall"] for a in ARMS}),
        "steady": summarize({a: res[a]["steady"] for a in ARMS}),
        "gamma_mlp": g,
        "gamma_mlp_steady": paired(res, "A1-mlp", "A9-mlp", "steady"),
        "welch_t": tv, "welch_p": pv,
        "verdict": verdict, "verdict_branch": branch,
        "pre_committed_interpretation": VERDICT_INTERPRETATION[branch],
        "raw": res, "runtime_sec": runtime,
    }
    _save_results(d)
    print("expansion_100seed:", verdict)


def snr_sweep(seeds: int = 20):
    d = _load_results()
    assert "expansion_precommit" in d, "record --precommit before running"
    assert "snr_sweep" not in d, "snr_sweep already present"
    grid = (0.5, 1.0, 4.0)
    block = {"seeds": seeds, "snr_grid": list(grid),
             "snr_mechanism": EXPANSION_PRECOMMIT["snr_mechanism"],
             "prediction": EXPANSION_PRECOMMIT["snr_sweep_prediction"],
             "adjudication_rule_4x":
                 EXPANSION_PRECOMMIT["adjudication_rule_4x"],
             "per_snr": {}}
    for snr in grid:
        res = run_battery(seeds, snr, f"snr={snr}")
        runtime = res.pop("_runtime_sec")
        pv = {}
        for metric in ("post_react", "steady"):
            for a, b in (("A1-mlp", "A9-mlp"), ("A1-mlp", "A6-mlp")):
                _, p = welch(res[a][metric], res[b][metric])
                pv[f"{a} vs {b} ({metric})"] = p
        block["per_snr"][str(snr)] = {
            "post_react": summarize({a: res[a]["post_react"] for a in ARMS}),
            "overall": summarize({a: res[a]["overall"] for a in ARMS}),
            "steady": summarize({a: res[a]["steady"] for a in ARMS}),
            "gamma_A1_minus_A9_post_react":
                paired(res, "A1-mlp", "A9-mlp", "post_react"),
            "gamma_A1_minus_A6_post_react":
                paired(res, "A1-mlp", "A6-mlp", "post_react"),
            "gamma_A1_minus_A9_steady":
                paired(res, "A1-mlp", "A9-mlp", "steady"),
            "gamma_A1_minus_A6_steady":
                paired(res, "A1-mlp", "A6-mlp", "steady"),
            "welch_p": pv,
            "raw": res, "runtime_sec": runtime,
        }
    # ---- 4x adjudication per the pre-committed rule ----
    p4 = block["per_snr"]["4.0"]
    dA9 = p4["gamma_A1_minus_A9_post_react"]
    dA6 = p4["gamma_A1_minus_A6_post_react"]
    if dA9["ci_lo"] > 0.0 or dA6["ci_lo"] > 0.0:
        verdict4 = ("DIVERGENCE (full prominence): retention keeps paying "
                    "at 4x SNR under gradient descent -- a pinned arm "
                    "still significantly beats the monolith on post-react "
                    f"(A1-A9 CI [{dA9['ci_lo']:.5f}, {dA9['ci_hi']:.5f}]; "
                    f"A1-A6 CI [{dA6['ci_lo']:.5f}, {dA6['ci_hi']:.5f}]). "
                    "This diverges from the linear E6 inversion.")
        branch4 = "divergence_retention_pays"
    elif dA9["ci_hi"] < 0.0 and dA6["ci_hi"] < 0.0:
        verdict4 = ("INVERSION REPRODUCES (beat form): the monolith "
                    "significantly beats both pinned arms at 4x SNR on "
                    f"post-react (A1-A9 CI [{dA9['ci_lo']:.5f}, "
                    f"{dA9['ci_hi']:.5f}]; A1-A6 CI [{dA6['ci_lo']:.5f}, "
                    f"{dA6['ci_hi']:.5f}]).")
        branch4 = "inversion_beat"
    else:
        verdict4 = ("INVERSION REPRODUCES (match form): the monolith "
                    "matches the pinned arms at 4x SNR on post-react "
                    f"(A1-A9 CI [{dA9['ci_lo']:.5f}, {dA9['ci_hi']:.5f}]; "
                    f"A1-A6 CI [{dA6['ci_lo']:.5f}, {dA6['ci_hi']:.5f}]).")
        branch4 = "inversion_match"
    block["verdict_4x"] = verdict4
    block["verdict_4x_branch"] = branch4
    d = _load_results()          # reload in case expand100 saved meanwhile
    assert "snr_sweep" not in d
    d["snr_sweep"] = block
    _save_results(d)
    print("snr_sweep:", verdict4)


def pilot():
    """Single-seed sanity check (learning happens; runtime estimate).
    Not a tuning loop: pass/fail only."""
    s = 0
    cfg = SynthConfig()
    rng = np.random.default_rng(1000 + s)
    sched = make_schedule(rng)
    print(f"T={sched.T}")
    for a in ARMS:
        t0 = time.time()
        mkt = SyntheticMarket(cfg, seed=5000 + s)
        arm = MLP_ARM_FACTORIES[a](cfg, np.random.default_rng(99 * s + 7))
        m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=MIN_DORM)
        extra = ""
        if hasattr(arm, "pinned"):
            extra = f" pinned={dict(arm.pinned)}"
        print(f"{a}: post_react={m['post_react']:.5f} "
              f"overall={m['overall']:.5f} steady={m['steady']:.5f} "
              f"n_react={m['n_react']} [{time.time()-t0:.1f}s]{extra}")


if __name__ == "__main__":
    seeds = None
    action = "main"
    for i, a in enumerate(sys.argv):
        if a == "--seeds":
            seeds = int(sys.argv[i + 1])
        if a == "--pilot":
            action = "pilot"
        if a == "--precommit":
            action = "precommit"
        if a == "--expand100":
            action = "expand100"
        if a == "--snr":
            action = "snr"
    if action == "pilot":
        pilot()
    elif action == "precommit":
        record_precommit()
    elif action == "expand100":
        expand100(seeds=seeds or 100)
    elif action == "snr":
        snr_sweep(seeds=seeds or SEEDS)
    else:
        main(seeds=seeds or SEEDS)
