"""Generate all RISP paper figures from results JSONs -> paper/figures/*.pdf"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = ROOT / "paper" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10,
                     "axes.labelsize": 9, "figure.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False})

C = {"rewdriven": "#E28C3C", "rewindep": "#5A82C8", "inv": "#3C915A",
     "oracle": "#444444", "bad": "#C83C3C"}

ARM_LABELS = {
    "A1-monolith-erm": "A1 monolith (ERM)",
    "A2-router": "A2 MoE router",
    "A3-recentperf": "A3 recent-perf alloc.",
    "A4-randomfixed": "A4 random fixed",
    "A5-risp-erm": "A5 RISP-ERM",
    "A6-risp-inv": "A6 RISP-full",
    "A7-monolith-inv": "A7 monolith (INV)",
    "A8a-hedge-fixed": "A8a Hedge (fixed)",
    "A8b-hedge-learn": "A8b Hedge (learners)",
    "A9-oracle-pinned": "A9 oracle pinned",
}


def jload(name):
    with open(RES / f"{name}.json") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- fig 1: 2x2
def fig1_2x2():
    d = jload("e1_synth")["post_react"]
    cells = {("reward-driven", "ERM"): "A1-monolith-erm",
             ("reward-driven", "INV"): "A7-monolith-inv",
             ("reward-indep.", "ERM"): "A5-risp-erm",
             ("reward-indep.", "INV"): "A6-risp-inv"}
    M = np.array([[d[cells[("reward-driven", "ERM")]]["mean"],
                   d[cells[("reward-driven", "INV")]]["mean"]],
                  [d[cells[("reward-indep.", "ERM")]]["mean"],
                   d[cells[("reward-indep.", "INV")]]["mean"]]])
    E = np.array([[d[cells[("reward-driven", "ERM")]]["ci95"],
                   d[cells[("reward-driven", "INV")]]["ci95"]],
                  [d[cells[("reward-indep.", "ERM")]]["ci95"],
                   d[cells[("reward-indep.", "INV")]]["ci95"]]])
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    im = ax.imshow(M, cmap="RdYlGn_r",
                   vmin=M.min() * 0.97, vmax=M.max() * 1.03)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{M[i, j]:.4f}\n±{E[i, j]:.4f}",
                    ha="center", va="center", fontsize=10, fontweight="bold")
    ax.set_xticks([0, 1], ["ERM", "Invariant"])
    ax.set_yticks([0, 1], ["reward-driven", "reward-indep."])
    ax.set_xlabel("specialist training")
    ax.set_ylabel("capacity allocation")
    ax.set_title("Post-reactivation decision regret")
    fig.colorbar(im, shrink=0.8)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_2x2.pdf")
    plt.close(fig)


# ----------------------------------------------------- fig: all-arm bar chart
def fig_arms(name="e1_synth", out="fig2_arms.pdf",
             title="Post-reactivation regret by arm (synthetic, 20 seeds)"):
    d = jload(name)["post_react"]
    order = ["A9-oracle-pinned", "A6-risp-inv", "A5-risp-erm",
             "A4-randomfixed", "A8a-hedge-fixed", "A8b-hedge-learn",
             "A2-router", "A3-recentperf", "A7-monolith-inv",
             "A1-monolith-erm"]
    order = [a for a in order if a in d]
    means = [d[a]["mean"] for a in order]
    errs = [d[a]["ci95"] for a in order]
    cols = []
    for a in order:
        if "oracle" in a: cols.append(C["oracle"])
        elif "risp-inv" in a: cols.append(C["inv"])
        elif a in ("A5-risp-erm", "A4-randomfixed", "A8a-hedge-fixed"):
            cols.append(C["rewindep"])
        else: cols.append(C["rewdriven"])
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ypos = np.arange(len(order))[::-1]
    ax.barh(ypos, means, xerr=errs, color=cols, height=0.65,
            error_kw={"lw": 0.9})
    ax.set_yticks(ypos, [ARM_LABELS[a] for a in order])
    ax.set_xlabel("post-reactivation decision regret (mean ± 95% CI)")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(FIG / out)
    plt.close(fig)


# ------------------------------------------------------- fig: capacity sweep
def fig_capacity():
    d = jload("e2_capacity_sweep")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), sharey=True)
    arms = ["A1-monolith-erm", "A2-router", "A5-risp-erm",
            "A6-risp-inv", "A9-oracle-pinned"]
    cols = {"A1-monolith-erm": C["rewdriven"], "A2-router": C["bad"],
            "A5-risp-erm": C["rewindep"], "A6-risp-inv": C["inv"],
            "A9-oracle-pinned": C["oracle"]}
    for ax, mem in zip(axes, ("hard", "soft")):
        Ks = sorted(int(k) for k in d[mem].keys())
        for a in arms:
            m = [d[mem][str(K)]["post_react"][a]["mean"] for K in Ks]
            e = [d[mem][str(K)]["post_react"][a]["ci95"] for K in Ks]
            ax.errorbar(Ks, m, yerr=e, marker="o", ms=3, lw=1.2,
                        label=ARM_LABELS[a], color=cols[a],
                        ls="--" if "oracle" in a else "-")
        ax.set_xlabel("per-specialist capacity $K$")
        ax.set_xticks(Ks)
        ax.set_title(f"{mem} memory model")
    axes[0].set_ylabel("post-reactivation regret")
    axes[0].legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_capacity.pdf")
    plt.close(fig)


# ------------------------------------------------------- fig: dormancy sweep
def fig_dormancy():
    d = jload("e3_dormancy_sweep")
    Ds = sorted(int(k) for k in d.keys())
    arms = ["A1-monolith-erm", "A2-router", "A3-recentperf",
            "A5-risp-erm", "A6-risp-inv"]
    cols = {"A1-monolith-erm": C["rewdriven"], "A2-router": C["bad"],
            "A3-recentperf": "#8C5AC8",
            "A5-risp-erm": C["rewindep"], "A6-risp-inv": C["inv"]}
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    for a in arms:
        m = [d[str(D)]["post_react"][a]["mean"] for D in Ds]
        e = [d[str(D)]["post_react"][a]["ci95"] for D in Ds]
        ax.errorbar(Ds, m, yerr=e, marker="o", ms=3, lw=1.2,
                    label=ARM_LABELS[a], color=cols[a])
    ax.set_xscale("log")
    ax.set_xticks(Ds, [str(D) for D in Ds])
    ax.set_xlabel("dormancy length $D$ (trading days)")
    ax.set_ylabel("post-reactivation regret")
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_dormancy.pdf")
    plt.close(fig)


# -------------------------------------------------- fig: heterogeneity sweep
def fig_het():
    d = jload("e4_heterogeneity_sweep")
    hets = sorted(float(k) for k in d.keys())
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    for a, c in (("A5-risp-erm", C["rewindep"]),
                 ("A6-risp-inv", C["inv"])):
        m = [d[str(h)]["post_react"][a]["mean"] for h in hets]
        e = [d[str(h)]["post_react"][a]["ci95"] for h in hets]
        ax.errorbar(hets, m, yerr=e, marker="o", ms=3, lw=1.2,
                    label=ARM_LABELS[a], color=c)
    ax.set_xlabel("episode heterogeneity (spurious-loading scale)")
    ax.set_ylabel("post-reactivation regret")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig5_heterogeneity.pdf")
    plt.close(fig)


# ------------------------------------------------------------- fig: SNR audit
def fig_snr():
    d = jload("e6_snr_audit")
    snrs = sorted(float(k) for k in d.keys())
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    for a, c in (("A1-monolith-erm", C["rewdriven"]),
                 ("A6-risp-inv", C["inv"]),
                 ("A9-oracle-pinned", C["oracle"])):
        rel = []
        err = []
        for s in snrs:
            pr = d[str(s)]["post_react"][a]
            st = d[str(s)]["steady"][a]
            rel.append(pr["mean"] / max(st["mean"], 1e-12))
            err.append(pr["ci95"] / max(st["mean"], 1e-12))
        ax.errorbar(snrs, rel, yerr=err, marker="o", ms=3, lw=1.2,
                    label=ARM_LABELS[a], color=c,
                    ls="--" if "oracle" in a else "-")
    ax.axhline(1.0, color="gray", lw=0.7, ls=":")
    ax.set_xscale("log")
    ax.set_xticks(snrs, [str(s) for s in snrs])
    ax.set_xlabel("signal-to-noise multiplier")
    ax.set_ylabel("post-react / steady regret")
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("Audit: relearning penalty vanishes at high SNR")
    fig.tight_layout()
    fig.savefig(FIG / "fig6_snr_audit.pdf")
    plt.close(fig)


# ------------------------------------------------------- fig: retention trace
def fig_trace():
    """Regret around reactivations: mean daily regret aligned on reactivation
    day, A1 vs A6 vs A9 (re-run quickly, 8 seeds, store traces)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from risp import (SynthConfig, SyntheticMarket, make_schedule,
                          run_arm, ARM_FACTORIES)
    arms = ["A1-monolith-erm", "A6-risp-inv", "A9-oracle-pinned"]
    win = (-10, 40)
    traces = {a: [] for a in arms}
    for s in range(8):
        cfg = SynthConfig()
        rng = np.random.default_rng(1000 + s)
        sched = make_schedule(rng)
        for a in arms:
            mkt = SyntheticMarket(cfg, seed=5000 + s)
            arm = ARM_FACTORIES[a](cfg, np.random.default_rng(99 * s + 7),
                                   2, "hard")
            m = run_arm(arm, mkt, sched, cfg)
            for t0 in m["react_days"]:
                lo, hi = t0 + win[0], t0 + win[1]
                if lo >= 0 and hi < len(m["daily"]):
                    traces[a].append(m["daily"][lo:hi])
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    xs = np.arange(win[0], win[1])
    cols = {"A1-monolith-erm": C["rewdriven"], "A6-risp-inv": C["inv"],
            "A9-oracle-pinned": C["oracle"]}
    for a in arms:
        T = np.array(traces[a])
        mu = T.mean(axis=0)
        se = 1.96 * T.std(axis=0) / np.sqrt(len(T))
        # 5-day smoothing
        ker = np.ones(5) / 5
        mu_s = np.convolve(mu, ker, mode="same")
        ax.plot(xs, mu_s, color=cols[a], lw=1.4, label=ARM_LABELS[a],
                ls="--" if "oracle" in a else "-")
        ax.fill_between(xs, mu_s - se, mu_s + se, color=cols[a], alpha=0.15)
    ax.axvline(0, color="k", lw=0.7, ls=":")
    ax.text(0.5, ax.get_ylim()[1] * 0.97, "reactivation", fontsize=7,
            va="top")
    ax.set_xlabel("days since regime reactivation")
    ax.set_ylabel("daily decision regret (5d MA)")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig7_trace.pdf")
    plt.close(fig)


# ------------------------------------------------------------- fig: ablations
def fig_ablations():
    d = jload("e5_ablations")
    fig, axes = plt.subplots(1, 3, figsize=(8.6, 2.8))
    bs = sorted(float(b) for b in d["beta_sweep"])
    m = [d["beta_sweep"][str(b)]["mean"] for b in bs]
    e = [d["beta_sweep"][str(b)]["ci95"] for b in bs]
    axes[0].errorbar(np.arange(len(bs)), m, yerr=e, marker="o", ms=3,
                     color=C["inv"])
    axes[0].set_xticks(np.arange(len(bs)), [f"{b:g}" for b in bs])
    axes[0].set_xlabel(r"$\beta$ (mean-loss weight)")
    axes[0].set_title(r"$\beta$ sweep ($\beta{=}0$: variance-only)")
    ws = sorted(int(w) for w in d["Wc_sweep"])
    m = [d["Wc_sweep"][str(w)]["mean"] for w in ws]
    e = [d["Wc_sweep"][str(w)]["ci95"] for w in ws]
    axes[1].errorbar(np.arange(len(ws)), m, yerr=e, marker="o", ms=3,
                     color=C["rewindep"])
    axes[1].set_xticks(np.arange(len(ws)), [str(w) for w in ws])
    axes[1].set_xlabel("competition window $W_c$ (days)")
    axes[1].set_title("batching the competition")
    keys = ["pinned", "never"]
    m = [d["pinning"][k]["mean"] for k in keys]
    e = [d["pinning"][k]["ci95"] for k in keys]
    axes[2].bar([0, 1], m, yerr=e, color=[C["inv"], C["rewdriven"]],
                width=0.5)
    axes[2].set_xticks([0, 1], ["pinned", "never pinned"])
    axes[2].set_title("assignment pinning")
    for ax in axes:
        ax.set_ylabel("post-react regret")
    fig.tight_layout()
    fig.savefig(FIG / "fig8_ablations.pdf")
    plt.close(fig)


if __name__ == "__main__":
    import sys
    todo = sys.argv[1:] or ["all"]
    if "all" in todo:
        for f in (fig1_2x2, fig_arms, fig_capacity, fig_dormancy, fig_het,
                  fig_snr, fig_trace, fig_ablations):
            try:
                f()
                print(f"[ok] {f.__name__}")
            except FileNotFoundError as ex:
                print(f"[skip] {f.__name__}: {ex}")
        # stitched real-data bar chart
        try:
            fig_arms("e1s_stitched_crypto", "fig9_stitched.pdf",
                     "Post-reactivation regret (regime-stitched crypto)")
            print("[ok] fig9")
        except FileNotFoundError as ex:
            print(f"[skip] fig9: {ex}")
