"""
RISP experiment driver.  Usage:  python run_experiments.py e0|e1|e1s|e2|e3|e4|e5 [--seeds N]

Writes JSON to ../results/.  Every number cited in the papers traces here.
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np

from risp import (SynthConfig, SyntheticMarket, make_schedule,
                      make_dormancy_schedule, run_arm, ARM_FACTORIES,
                      EXTRA_ARM_FACTORIES,
                      RISPArm, RISPTriggerArm, MonolithArm, welch, holm,
                      ci95, regret, solve_topk)

RESULTS = Path(__file__).resolve().parents[0] / ".." / "results"
RESULTS.mkdir(exist_ok=True)

SEEDS = 20
PROBE = 15
MIN_DORM = 90


def save(name: str, obj):
    f = RESULTS / f"{name}.json"
    with open(f, "w") as fh:
        json.dump(obj, fh, indent=1, default=float)
    print(f"[saved] {f.resolve()}")


def summarize(per_arm_metric: dict) -> dict:
    out = {}
    for arm, xs in per_arm_metric.items():
        xs = [x for x in xs if np.isfinite(x)]
        m, h = ci95(xs)
        out[arm] = {"mean": m, "ci95": h, "n": len(xs)}
    return out


# ============================================================================
# E1 — headline 2x2 dissociation, synthetic
# ============================================================================

def e1(seeds=SEEDS, K=2, het=1.0, memory="hard", tag="e1_synth",
       arms=None):
    arms = arms or list(ARM_FACTORIES.keys())
    factories = {**ARM_FACTORIES, **EXTRA_ARM_FACTORIES}
    res = {a: {"overall": [], "post_react": [], "steady": []} for a in arms}
    t0 = time.time()
    for s in range(seeds):
        cfg = SynthConfig(het=het)
        rng = np.random.default_rng(1000 + s)
        sched = make_schedule(rng)
        for a in arms:
            mkt = SyntheticMarket(cfg, seed=5000 + s)   # same data per arm
            arm = factories[a](cfg, np.random.default_rng(99 * s + 7), K, memory)
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=MIN_DORM)
            for key in ("overall", "post_react", "steady"):
                res[a][key].append(m[key])
        if s == 0:
            print(f"seed 0 done in {time.time()-t0:.1f}s; "
                  f"n_react={m['n_react']}, T={sched.T}")
    out = {"config": {"seeds": seeds, "K": K, "het": het, "memory": memory,
                      "probe": PROBE, "min_dormancy": MIN_DORM},
           "post_react": summarize({a: res[a]["post_react"] for a in arms}),
           "overall": summarize({a: res[a]["overall"] for a in arms}),
           "steady": summarize({a: res[a]["steady"] for a in arms}),
           "raw": {a: res[a] for a in arms}}
    # key pairwise tests on post-reactivation regret
    pairs = [("A6-risp-inv", "A5-risp-erm"),
             ("A6-risp-inv", "A1-monolith-erm"),
             ("A5-risp-erm", "A1-monolith-erm"),
             ("A5-risp-erm", "A2-router"),
             ("A6-risp-inv", "A7-monolith-inv"),
             ("A7-monolith-inv", "A1-monolith-erm"),
             ("A6-risp-inv", "A9-oracle-pinned"),
             ("A6-risp-inv", "A10-oracle-inv"),
             ("A5-risp-erm", "A4-randomfixed"),
             ("A6-risp-inv", "A8b-hedge-learn"),
             ("A2-router", "A1-monolith-erm"),
             # PREREG D1 replay pairs -- only enter the family when the
             # replay arms are actually in `arms` (guard below), so every
             # existing run's welch/holm output is unchanged.
             ("A1r-replay-erm", "A9-oracle-pinned"),
             ("A1r-replay-erm", "A6-risp-inv"),
             ("A1r-replay-erm", "A1-monolith-erm"),
             ("A1r-replay-inv", "A6-risp-inv"),
             ("A1r-replay-inv", "A9-oracle-pinned"),
             ("A1r-replay-inv", "A10-oracle-inv"),
             ("A1r-replay-inv", "A1r-replay-erm"),
             # PREREG D4 A3' pairs -- same guard: they only enter the family
             # when A3p-shadowtrain is actually in `arms`, so every existing
             # run's welch/holm output is unchanged.
             ("A3p-shadowtrain", "A3-recentperf"),
             ("A3p-shadowtrain", "A5-risp-erm"),
             ("A3p-shadowtrain", "A1-monolith-erm"),
             ("A3p-shadowtrain", "A9-oracle-pinned")]
    pv = {}
    for a, b in pairs:
        if a in res and b in res:
            _, p = welch(res[a]["post_react"], res[b]["post_react"])
            pv[f"{a} vs {b}"] = p
    out["welch_p"] = pv
    out["holm_p"] = holm(pv)
    save(tag, out)
    return out


# ============================================================================
# E2 — capacity sweep
# ============================================================================

def e2(seeds=SEEDS):
    arms = ["A1-monolith-erm", "A2-router", "A4-randomfixed",
            "A5-risp-erm", "A6-risp-inv", "A9-oracle-pinned"]
    out = {}
    for memory in ("hard", "soft"):
        out[memory] = {}
        for K in (1, 2, 3, 4):
            r = e1(seeds=seeds, K=K, memory=memory,
                   tag=f"e2_K{K}_{memory}", arms=arms)
            out[memory][K] = {"post_react": r["post_react"],
                              "overall": r["overall"]}
    save("e2_capacity_sweep", out)
    return out


# ============================================================================
# E3 — dormancy sweep (synthetic schedules with controlled dormancy)
# ============================================================================

def e3(seeds=SEEDS, K=2):
    arms = ["A1-monolith-erm", "A2-router", "A3-recentperf",
            "A5-risp-erm", "A6-risp-inv"]
    Ds = [21, 63, 126, 252, 504]
    out = {}
    for D in Ds:
        res = {a: [] for a in arms}
        res_steady = {a: [] for a in arms}
        for s in range(seeds):
            cfg = SynthConfig()
            rng = np.random.default_rng(3000 + s)
            sched = make_dormancy_schedule(rng, D=D)
            for a in arms:
                mkt = SyntheticMarket(cfg, seed=7000 + s)
                arm = ARM_FACTORIES[a](cfg, np.random.default_rng(13 * s + 5),
                                       K, "hard")
                m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                            min_dormancy=min(D - 1, MIN_DORM))
                res[a].append(m["post_react"])
                res_steady[a].append(m["steady"])
        out[D] = {"post_react": summarize(res), "steady": summarize(res_steady)}
        print(f"D={D} done")
    save("e3_dormancy_sweep", out)
    return out


# ============================================================================
# E4 — episode-heterogeneity sweep (allocation fixed; ERM vs INV)
# ============================================================================

def e4(seeds=SEEDS, K=2):
    arms = ["A5-risp-erm", "A6-risp-inv", "A9-oracle-pinned"]
    hets = [0.0, 0.5, 1.0, 1.5, 2.0]
    out = {}
    for het in hets:
        r = e1(seeds=seeds, K=K, het=het, tag=f"e4_het{het}", arms=arms)
        out[het] = {"post_react": r["post_react"], "overall": r["overall"]}
    save("e4_heterogeneity_sweep", out)
    return out


# ============================================================================
# E5 — ablations
# ============================================================================

def e5(seeds=SEEDS, K=2):
    out = {}

    # (a) beta sweep + variance-only control for the INV objective
    def run_custom(mode, beta, Wc=20, lam=0.3, pin=True, tag=""):
        post = []
        for s in range(seeds):
            cfg = SynthConfig()
            rng = np.random.default_rng(1000 + s)
            sched = make_schedule(rng)
            mkt = SyntheticMarket(cfg, seed=5000 + s)
            arm = RISPArm(cfg, np.random.default_rng(99 * s + 7), K=K,
                              mode=mode, beta=beta, Wc=Wc, lam=lam, pin=pin)
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                        min_dormancy=MIN_DORM)
            post.append(m["post_react"])
        mean, h = ci95([x for x in post if np.isfinite(x)])
        return {"mean": mean, "ci95": h, "raw": post}

    out["beta_sweep"] = {str(b): run_custom("inv", beta=b)
                         for b in (0.0, 0.25, 1.0, 4.0, 16.0)}
    # beta=0 is the variance-only control (Inv-PnCO Table-7 analogue)

    # (b) competition-window sweep
    out["Wc_sweep"] = {str(w): run_custom("inv", beta=1.0, Wc=w)
                       for w in (1, 5, 20, 60)}

    # (c) lambda (niche bonus) on/off
    out["lambda"] = {str(l): run_custom("inv", beta=1.0, lam=l)
                     for l in (0.0, 0.3)}

    # (d) pinned vs never-pinned
    out["pinning"] = {"pinned": run_custom("inv", beta=1.0, pin=True),
                      "never": run_custom("inv", beta=1.0, pin=False)}
    save("e5_ablations", out)
    return out


# ============================================================================
# E6 — audit: SNR sweep (when is retention worthless?)
# Found during development: at high within-regime SNR a fresh learner
# recalibrates within days and retention buys nothing.  We quantify the
# break-even relearning speed.
# ============================================================================

def e6(seeds=SEEDS, K=2):
    arms = ["A1-monolith-erm", "A6-risp-inv", "A9-oracle-pinned"]
    out = {}
    for snr in (0.5, 1.0, 2.0, 4.0, 8.0):
        res = {a: {"post_react": [], "steady": []} for a in arms}
        for s in range(seeds):
            cfg = SynthConfig(snr_mult=snr)
            rng = np.random.default_rng(1000 + s)
            sched = make_schedule(rng)
            for a in arms:
                mkt = SyntheticMarket(cfg, seed=5000 + s)
                arm = ARM_FACTORIES[a](cfg, np.random.default_rng(99 * s + 7),
                                       K, "hard")
                m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                            min_dormancy=MIN_DORM)
                res[a]["post_react"].append(m["post_react"])
                res[a]["steady"].append(m["steady"])
        out[snr] = {k: summarize({a: res[a][k] for a in arms})
                    for k in ("post_react", "steady")}
        print(f"snr={snr} done")
    save("e6_snr_audit", out)
    return out


# ============================================================================
# E6t — staleness-trigger remedy for the E6 high-SNR inversion
# Same SNR sweep, same seeds/schedules/markets as e6(); compares the fresh
# monolith (A1), pin-forever RISP (A6) and RISP + GAUSE-style staleness
# trigger (A6t).  A6t is registered LOCALLY, not in ARM_FACTORIES, so that
# e1()'s default arm list — and every existing result file — is untouched.
# ============================================================================

def e6t(seeds=SEEDS, K=2):
    arms = ["A1-monolith-erm", "A6-risp-inv", "A6t-risp-trigger"]
    factories = dict(ARM_FACTORIES)
    factories["A6t-risp-trigger"] = (
        lambda cfg, rng, K, mem: RISPTriggerArm(cfg, rng, K=K, memory=mem))
    trig_defaults = {"Wt": 20, "stale_k": 3, "stale_margin": 0.25,
                     "z_thresh": 2.0, "probe_burn": 5,
                     "fire_action": "unpin; soften owner affinity row to "
                                    "0.5*alpha + 0.5/R; reset owner beliefs "
                                    "for r to the recalibration probe (head "
                                    "copy) and drop stale episode buffer to "
                                    "the current episode; probation until "
                                    "re-pin (serving leader trains daily). "
                                    "See RISPTriggerArm docstring."}
    out = {"config": {"seeds": seeds, "K": K, "probe": PROBE,
                      "min_dormancy": MIN_DORM, "trigger": trig_defaults}}
    t0 = time.time()
    for snr in (0.5, 1.0, 2.0, 4.0, 8.0):
        res = {a: {"post_react": [], "steady": []} for a in arms}
        unpins = []
        for s in range(seeds):
            cfg = SynthConfig(snr_mult=snr)
            rng = np.random.default_rng(1000 + s)
            sched = make_schedule(rng)
            for a in arms:
                mkt = SyntheticMarket(cfg, seed=5000 + s)
                arm = factories[a](cfg, np.random.default_rng(99 * s + 7),
                                   K, "hard")
                m = run_arm(arm, mkt, sched, cfg, probe=PROBE,
                            min_dormancy=MIN_DORM)
                res[a]["post_react"].append(m["post_react"])
                res[a]["steady"].append(m["steady"])
                if a == "A6t-risp-trigger":
                    unpins.append(getattr(arm, "n_unpins", 0))
        pv = {}
        for metric in ("post_react", "steady"):
            for a, b in (("A6t-risp-trigger", "A6-risp-inv"),
                         ("A6t-risp-trigger", "A1-monolith-erm")):
                _, p = welch(res[a][metric], res[b][metric])
                pv[f"{a} vs {b} ({metric})"] = p
        out[snr] = {k: summarize({a: res[a][k] for a in arms})
                    for k in ("post_react", "steady")}
        out[snr]["welch_p"] = pv
        out[snr]["mean_unpins_per_run"] = float(np.mean(unpins))
        out[snr]["raw"] = {a: res[a] for a in arms}
        print(f"snr={snr} done ({time.time()-t0:.0f}s); "
              f"A6t unpins/run={np.mean(unpins):.2f}")
    save("e6_trigger", out)
    return out


# ============================================================================
# E0 — structure diagnostic on real data (decision-regret metric)
# ============================================================================

def e0(seeds=SEEDS):
    sys.path.insert(0, str(Path(__file__).parent))
    from realdata import (load_crypto_panel, load_commodity_panel, build_xy,
                          label_L1, label_L2)
    out = {}
    for dom, panel, k in (("crypto", load_crypto_panel(), 2),
                          ("commodities", load_commodity_panel(), 1)):
        X, Y, idx = build_xy(panel)
        labs = {"L1": label_L1(panel)[idx], "L2": label_L2(panel)[idx]}
        n = X.shape[1]
        w_max = 0.5 if k == 1 else 0.25
        T = len(X)
        split = T // 2
        dom_out = {}
        for lname, lab in labs.items():
            lab = np.nan_to_num(lab, nan=0).astype(int)
            rng = np.random.default_rng(42)
            # oracle regime-conditioned ridge vs shuffled-label control,
            # walk-forward refit every 60d, evaluated on decision regret
            def regimewise_regret(labels):
                regs = np.zeros(T - split)
                models = {}
                for t in range(split, T):
                    if (t - split) % 60 == 0:
                        models = {}
                        for r in set(labels[:t].tolist()):
                            m_idx = np.where(labels[:t] == r)[0]
                            if len(m_idx) < 30:
                                continue
                            Xtr = np.vstack([X[i] for i in m_idx])
                            ytr = np.concatenate([Y[i] for i in m_idx])
                            A = Xtr.T @ Xtr + 10.0 * np.eye(X.shape[2])
                            models[r] = np.linalg.solve(A, Xtr.T @ ytr)
                    r = labels[t]
                    w = models.get(r)
                    if w is None:
                        yh = np.zeros(n)
                    else:
                        yh = X[t] @ w
                    regs[t - split] = regret(yh, Y[t], k, w_max)
                return regs

            real_reg = regimewise_regret(lab)
            sh_regs = []
            for s in range(10):
                perm_lab = block_shuffle(lab, rng)
                sh_regs.append(regimewise_regret(perm_lab).mean())
            # pooled (unconditioned) baseline
            pooled = np.full(T, 0)
            pooled_reg = regimewise_regret(pooled)
            _, p = welch_vec(real_reg, sh_regs)
            dom_out[lname] = {
                "real_mean_regret": float(real_reg.mean()),
                "shuffled_mean_regret": float(np.mean(sh_regs)),
                "shuffled_sd": float(np.std(sh_regs)),
                "pooled_mean_regret": float(pooled_reg.mean()),
                "gap_pct": float(100 * (np.mean(sh_regs) - real_reg.mean())
                                 / (np.mean(sh_regs) + 1e-12)),
                "z_vs_shuffled": float((np.mean(sh_regs) - real_reg.mean())
                                       / (np.std(sh_regs) + 1e-12)),
                "n_days_eval": int(T - split),
                "regime_counts": {int(r): int((lab == r).sum())
                                  for r in set(lab.tolist())},
            }
            print(dom, lname, dom_out[lname]["gap_pct"], "% gap")
        out[dom] = dom_out
    save("e0_structure_diagnostic", out)
    return out


def block_shuffle(lab, rng, R=4):
    """Permute the regime identity of each contiguous block (preserves block
    structure, destroys label->structure alignment)."""
    lab = lab.copy()
    t = 0
    while t < len(lab):
        t1 = t
        while t1 + 1 < len(lab) and lab[t1 + 1] == lab[t]:
            t1 += 1
        lab[t:t1 + 1] = rng.integers(0, R)
        t = t1 + 1
    return lab


def welch_vec(a_vec, b_means):
    from scipy import stats
    return stats.ttest_1samp(b_means, a_vec.mean())


# ============================================================================
# E1s — semi-synthetic stitched real data
# ============================================================================

def e1s(seeds=SEEDS, K=2):
    sys.path.insert(0, str(Path(__file__).parent))
    from realdata import (load_crypto_panel, build_xy, label_L1, BlockLibrary,
                          StitchedMarket)
    panel = load_crypto_panel()
    X, Y, idx = build_xy(panel)
    lab = np.nan_to_num(label_L1(panel)[idx], nan=-1)
    lib = BlockLibrary(X, Y, lab, np.arange(len(idx)))
    print("block counts:", lib.counts())

    class CfgReal:
        n_assets, d, k, w_max, R = X.shape[1], X.shape[2], 2, 0.25, 4

    cfg = CfgReal()
    arms = ["A1-monolith-erm", "A2-router", "A3-recentperf", "A4-randomfixed",
            "A5-risp-erm", "A6-risp-inv", "A7-monolith-inv",
            "A8a-hedge-fixed", "A8b-hedge-learn", "A9-oracle-pinned"]
    res = {a: {"overall": [], "post_react": []} for a in arms}
    for s in range(seeds):
        rng = np.random.default_rng(2000 + s)
        # schedule: regimes 0..2 cycle; regime 3 (vol-down) dormant ~200d
        seq = []
        for cyc in range(16):
            for r in rng.permutation([0, 1, 2]):
                seq.append((int(r), int(rng.integers(20, 45))))
            if cyc % 3 == 2:
                seq.append((3, int(rng.integers(15, 30))))
        mkt = StitchedMarket(lib, rng)
        sched = mkt.materialize(seq)
        for a in arms:
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(55 * s + 3),
                                   K, "hard")
            m = run_arm(arm, mkt, sched, cfg, probe=PROBE, min_dormancy=80)
            res[a]["overall"].append(m["overall"])
            res[a]["post_react"].append(m["post_react"])
    pairs = [("A6-risp-inv", "A5-risp-erm"),
             ("A6-risp-inv", "A1-monolith-erm"),
             ("A5-risp-erm", "A2-router"),
             ("A5-risp-erm", "A1-monolith-erm"),
             ("A6-risp-inv", "A8b-hedge-learn"),
             ("A6-risp-inv", "A9-oracle-pinned")]
    pv = {}
    for a, b in pairs:
        _, p = welch(res[a]["post_react"], res[b]["post_react"])
        pv[f"{a} vs {b}"] = p
    out = {"config": {"seeds": seeds, "K": K, "probe": PROBE,
                      "min_dormancy": 80, "block_counts": lib.counts()},
           "post_react": summarize({a: res[a]["post_react"] for a in arms}),
           "overall": summarize({a: res[a]["overall"] for a in arms}),
           "welch_p": pv, "holm_p": holm(pv),
           "raw": res}
    save("e1s_stitched_crypto", out)
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "e1"
    seeds = SEEDS
    for i, a in enumerate(sys.argv):
        if a == "--seeds":
            seeds = int(sys.argv[i + 1])
    {"e0": e0, "e1": e1, "e1s": e1s, "e2": e2,
     "e3": e3, "e4": e4, "e5": e5, "e6": e6, "e6t": e6t}[which](seeds=seeds)
