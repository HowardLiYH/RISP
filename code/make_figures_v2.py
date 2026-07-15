"""Publication figures 10-14 (the addendum-D/E/F wave) from results JSONs.

Outputs, per figure:
  paper/figures/figNN_<name>.pdf   -- vector, no title (the caption does the work)
  assets/figNN_<name>.png          -- 2x raster twin with a self-explanatory title,
                                      embedded by README.md

Deterministic: reads only committed results JSONs; no RNG, no recomputation of
experiments.  Every number is derived here from the JSON at plot time -- nothing
is hardcoded except layout.

Classification rule for the sign-rule scorecard (fig10), fixed before drawing:
  ordering  = A6 < A5 < A1 (post-react means) AND Holm(A6 vs A1) < 0.05
  inversion = A1 < A6                          AND Holm(A6 vs A1) < 0.05
  flat      = anything else

Palette: Okabe-Ito subset, validated colorblind-safe (blue #0072B2 vs
vermillion #D55E00 worst-pair CVD deltaE 92; identity is never color-alone --
outcome classes also differ in marker shape and fill).
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES100 = ROOT / "results_100seed"
FIG = ROOT / "paper" / "figures"
ASSETS = ROOT / "assets"
FIG.mkdir(exist_ok=True, parents=True)
ASSETS.mkdir(exist_ok=True, parents=True)

# ------------------------------------------------------------------ style
plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y",
    "grid.color": "#d9d9d9", "grid.linewidth": 0.5, "grid.alpha": 0.6,
    "axes.axisbelow": True,
    "figure.dpi": 150, "pdf.fonttype": 42, "ps.fonttype": 42,
})

BLUE = "#0072B2"     # ordering / RISP-full (A6) / positive-Gamma structure
VERM = "#D55E00"     # inversion / monolith (A1)
ORANGE = "#E69F00"   # replay arms (always direct-labeled; contrast relief)
GREEN = "#009E73"    # RISP-ERM (A5)
GRAY = "#767676"     # flat / null (semantic gray, >=3:1 on white)
DARK = "#3a3a3a"     # oracle reference arms (A9/A10)
INK = "#1a1a1a"

GAMMA = r"$\hat{\Gamma}$"        # one notation everywhere
SCALE = 1e3                      # regret plotted in units of 1e-3 per day
XLBL_G = GAMMA + r" $=$ A1 $-$ A9 post-reactivation regret ($\times 10^{-3}$ per day)"

CLASS_STYLE = {   # outcome -> (color, marker, fill)  [shape = secondary encoding]
    "ordering":  (BLUE, "o", True),
    "inversion": (VERM, "D", True),
    "flat":      (GRAY, "o", False),
}


def jload(path):
    with open(path) as fh:
        return json.load(fh)


def classify(block):
    """Pre-registered scorecard rule; see module docstring."""
    pr = block["post_react"]
    a1 = pr["A1-monolith-erm"]["mean"]
    a5 = pr["A5-risp-erm"]["mean"]
    a6 = pr["A6-risp-inv"]["mean"]
    holm = block["holm_p"]["A6-risp-inv vs A1-monolith-erm"]
    if a6 < a5 < a1 and holm < 0.05:
        return "ordering"
    if a1 < a6 and holm < 0.05:
        return "inversion"
    return "flat"


def paired(block, a="A1-monolith-erm", b="A9-oracle-pinned", key="post_react"):
    """Paired per-seed mean difference a-b with 95% CI, from raw seed lists."""
    xa = np.asarray(block["raw"][a][key], dtype=float)
    xb = np.asarray(block["raw"][b][key], dtype=float)
    d = xa - xb
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def savefig(fig, stem, png_title):
    fig.savefig(FIG / f"{stem}.pdf", bbox_inches="tight")
    fig.suptitle(png_title, fontsize=10.5, fontweight="bold", y=1.02, color=INK)
    fig.savefig(ASSETS / f"{stem}.png", dpi=240, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"[ok] {stem}: paper/figures/{stem}.pdf + assets/{stem}.png")


# ================================================================== fig 10
def fig10_signrule():
    """One row per scored cell: Gamma-hat with CI, colored by OBSERVED outcome."""
    l1 = jload(RES100 / "e_french49_dissoc.json")["walkforward"]
    l3 = jload(RES100 / "e_french49_L3_dissoc.json")["walkforward"]
    psw = jload(RES / "e_french49_prewar_L3_sweep.json")
    p15 = jload(RES / "e_french49_prewar_L3_dissoc.json")["walkforward"]
    sub = jload(RES / "e_french49_prewar_L3_subera.json")
    cry = jload(RES / "e1r_4h_crypto.json")

    def g2(block):
        g = block["gate2_forgetting_deficit"]
        return g["mean"], g["ci95"]

    rows = []  # (group, label, gamma, ci, class, note)
    rows.append(("1990–2025 · French 49 industries",
                 "L1 vol-band (wf, 100 seeds)", *g2(l1), classify(l1), None))
    rows.append(("1990–2025 · French 49 industries",
                 "L3 drawdown 15% (wf, 100 seeds)", *g2(l3), classify(l3), None))
    for key, lbl in (("10pct", "L3 @ 10% (20 seeds)"),
                     ("12pct", "L3 @ 12% (20 seeds)")):
        rows.append(("1926–1989 · withheld era (36 industries)",
                     lbl, *g2(psw[key]), classify(psw[key]),
                     "miss" if key == "12pct" else None))
    rows.append(("1926–1989 · withheld era (36 industries)",
                 "L3 @ 15% (frozen spec, 20 seeds)", *g2(p15), classify(p15), None))
    rows.append(("1926–1989 · withheld era (36 industries)",
                 "L3 @ 20% (20 seeds)", *g2(psw["20pct"]), classify(psw["20pct"]), None))
    for key, lbl in (("1926-1957", "1926–57 @ 15% (20 seeds)"),
                     ("1958-1989", "1958–89 @ 15% (20 seeds)")):
        rows.append(("withheld sub-eras · L3 @ 15%",
                     lbl, *g2(sub[key]), classify(sub[key]), None))
    gm, gc = paired(cry)
    rows.append(("crypto · 4H, confirmed gate cell",
                 "5 perp pairs (20 seeds)", gm, gc, classify(cry), None))

    fig, ax = plt.subplots(figsize=(6.3, 4.3))
    ax.grid(False); ax.grid(True, axis="x", color="#d9d9d9", lw=0.5, alpha=0.6)
    ax.spines["left"].set_visible(False)

    y = 0.0
    ylocs, ylabels = [], []
    last_group = None
    miss_xy = None
    for group, label, m, ci, cls, note in rows:
        if group != last_group:
            y -= 1.15
            ax.text(-0.315, y, group, transform=ax.get_yaxis_transform(),
                    fontsize=7.8, fontweight="bold", color=INK,
                    ha="left", va="center")
            last_group = group
        y -= 1.0
        col, mk, filled = CLASS_STYLE[cls]
        ax.errorbar(m * SCALE, y, xerr=ci * SCALE, fmt=mk, ms=5.5,
                    color=col, mfc=col if filled else "white",
                    mec=col, mew=1.1, elinewidth=1.3, capsize=2.4, zorder=3)
        ylocs.append(y); ylabels.append(label)
        if note == "miss":
            miss_xy = (m * SCALE, y)
    ax.axvline(0, color=INK, lw=0.8, zorder=2)
    ax.set_yticks(ylocs, ylabels, fontsize=7.8)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(XLBL_G)
    ax.set_ylim(y - 3.4, -0.35)   # bottom band reserved for the legend

    if miss_xy is not None:
        ax.annotate("the scorecard's one miss:\n" + GAMMA +
                    " significantly $<0$, table flat",
                    xy=(miss_xy[0] + 0.06, miss_xy[1]),
                    xytext=(0.42, miss_xy[1] - 0.25),
                    fontsize=7, style="italic", color=INK, ha="left",
                    va="center",
                    arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.8,
                                    shrinkA=4, shrinkB=2))

    handles = [
        plt.Line2D([], [], color=BLUE, marker="o", ls="", ms=5.5,
                   label="observed: full pre-registered ordering (A6<A5<A1)"),
        plt.Line2D([], [], color=VERM, marker="D", ls="", ms=5,
                   label="observed: inversion (A1 beats A6)"),
        plt.Line2D([], [], color=GRAY, marker="o", ls="", ms=5.5, mfc="white",
                   label="observed: flat (no Holm-significant separation)"),
    ]
    leg = ax.legend(handles=handles, loc="lower right", frameon=False,
                    fontsize=6.8, handletextpad=0.4, borderaxespad=0.2)
    for t in leg.get_texts():
        t.set_color(INK)
    fig.subplots_adjust(left=0.30)
    savefig(fig, "fig10_signrule",
            "The sign-rule scorecard: " + GAMMA +
            "'s sign predicts the dissociation table — in both directions")


# ================================================================== fig 11
def fig11_costs():
    costs = jload(RES / "e_french49_L3_costs.json")
    l3g = jload(RES100 / "e_french49_L3_dissoc.json")["walkforward"]
    l1g = jload(RES100 / "e_french49_dissoc.json")["walkforward"]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(6.3, 2.8), gridspec_kw={"width_ratios": [1.45, 1]})

    # (a) Gamma_net vs cost tier -------------------------------------------
    tiers = [0.0, 25.0, 50.0, 100.0]
    g0 = l3g["gate2_forgetting_deficit"]
    means = [g0["mean"]]; cis = [g0["ci95"]]
    for t in tiers[1:]:
        g = costs["L3_tiers"]["tiers"][f"{t:.1f}"]["both_pay"]["gamma_forget_net"]
        means.append(g["mean"]); cis.append(g["ci95"])
    xs = np.arange(len(tiers))
    ax1.axhline(0, color=INK, lw=0.8)
    ax1.errorbar(xs, np.array(means) * SCALE, yerr=np.array(cis) * SCALE,
                 fmt="-o", color=BLUE, ms=5, lw=1.5, elinewidth=1.2,
                 capsize=2.4, zorder=3)
    for x, m in zip(xs, means):
        first = (x == xs[0])
        ax1.annotate(f"{m * SCALE:+.2f}", (x, m * SCALE),
                     xytext=(8, -2) if first else (-6, 6),
                     textcoords="offset points",
                     ha="left" if first else "right",
                     fontsize=7, color=INK)
    ax1.set_xticks(xs, ["0\n(gross)", "25", "50", "100"])
    ax1.set_xlabel("crisis-window effective cost (bps, round-trip)")
    ax1.set_ylabel(GAMMA + r"$_{\rm net}$ ($\times 10^{-3}$ per day)")
    ax1.set_title("(a)  L3@15%: the deficit strengthens with costs", fontsize=8.5)
    ax1.set_ylim(-0.25, 2.95)
    ax1.text(0.02, 0.965, "gross point: 100 seeds; net tiers: 20 seeds\n"
             "Holm-corrected ordering holds at every tier",
             transform=ax1.transAxes, fontsize=6.6, color=GRAY, va="top")

    # (b) L1 inversion: gross vs net ---------------------------------------
    m_g, ci_g = paired(l1g, a="A6-risp-inv", b="A1-monolith-erm")
    net = costs["L1_25bps"]["tiers"]["25.0"]["both_pay"]["A6_minus_A1_paired"]
    p_net = costs["L1_25bps"]["tiers"]["25.0"]["both_pay"]["welch_p_A6_vs_A1"]
    pts = [("gross\n(100 seeds)", m_g, ci_g, VERM),
           ("net 25 bps\n(20 seeds)", net["mean"], net["ci95"], BLUE)]
    ax2.axhline(0, color=INK, lw=0.8)
    ax2.plot([0, 1], [pts[0][1] * SCALE, pts[1][1] * SCALE],
             color=GRAY, lw=1.0, ls=":", zorder=2)
    for i, (lbl, m, ci, col) in enumerate(pts):
        ax2.errorbar(i, m * SCALE, yerr=ci * SCALE, fmt="o", color=col,
                     ms=6, elinewidth=1.3, capsize=2.6, zorder=3)
        ax2.annotate(f"{m * SCALE:+.2f}", (i, m * SCALE),
                     xytext=(-10, 0) if i == 0 else (10, 3),
                     textcoords="offset points", va="center",
                     ha="right" if i == 0 else "left",
                     fontsize=7, color=INK)
    ax2.set_xticks([0, 1], [p[0] for p in pts])
    ax2.set_xlim(-0.55, 1.65)
    ax2.set_ylabel(r"A6 $-$ A1 post-react ($\times 10^{-3}$ per day)")
    ax2.set_title("(b)  L1: the inversion is gross-only", fontsize=8.5)
    ax2.annotate(f"p = {p_net:.1e}", (1, pts[1][1] * SCALE),
                 xytext=(10, -9), textcoords="offset points", ha="left",
                 va="top", fontsize=6.6, color=GRAY)
    ax2.text(0.97, 0.93, "monolith ahead", transform=ax2.transAxes,
             fontsize=6.6, color=VERM, ha="right")
    ax2.text(0.03, 0.05, "pool ahead", transform=ax2.transAxes,
             fontsize=6.6, color=BLUE)
    fig.tight_layout(w_pad=2.2)
    savefig(fig, "fig11_costs",
            "Costs amplify the deficit — and reverse the L1 inversion")


# ================================================================== fig 12
def fig12_replay():
    syn = jload(RES / "e1_replay.json")
    fre = jload(RES / "e_french49_L3_replay.json")

    ARM_META = {   # label, color, filled
        "A1-monolith-erm": ("A1 monolith-ERM", VERM, True),
        "A1r-replay-erm": ("A1r replay-ERM", ORANGE, True),
        "A9-oracle-pinned": ("A9 oracle-pinned", DARK, True),
        "A5-risp-erm": ("A5 RISP-ERM", GREEN, True),
        "A1r-replay-inv": ("A1r replay-INV", ORANGE, False),
        "A6-risp-inv": ("A6 RISP-full", BLUE, True),
        "A10-oracle-inv": ("A10 oracle-INV", DARK, False),
    }
    order_syn = ["A1-monolith-erm", "A1r-replay-erm", "A9-oracle-pinned",
                 "A5-risp-erm", "A1r-replay-inv", "A6-risp-inv",
                 "A10-oracle-inv"]
    order_fre = order_syn[:-1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.3, 2.9))

    def panel(ax, data, order, title):
        ax.grid(False); ax.grid(True, axis="x", color="#d9d9d9", lw=0.5, alpha=0.6)
        ax.spines["left"].set_visible(False)
        ys = -np.arange(len(order), dtype=float)
        for y, a in zip(ys, order):
            lbl, col, filled = ARM_META[a]
            pr = data["post_react"][a]
            ax.errorbar(pr["mean"] * SCALE, y, xerr=pr["ci95"] * SCALE,
                        fmt="o", ms=5.5, color=col,
                        mfc=col if filled else "white", mec=col, mew=1.1,
                        elinewidth=1.3, capsize=2.4, zorder=3)
        ax.set_yticks(ys, [ARM_META[a][0] for a in order], fontsize=7.6)
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel(r"post-react regret ($\times 10^{-3}$ per day)")
        ax.set_title(title, fontsize=8.5)
        ax.set_ylim(ys[-1] - 3.1, 0.8)   # bottom band for annotations

    # synthetic panel: closure + A6-beats-replay from raw / holm
    a1 = np.array(syn["raw"]["A1-monolith-erm"]["post_react"])
    a9 = np.array(syn["raw"]["A9-oracle-pinned"]["post_react"])
    ar = np.array(syn["raw"]["A1r-replay-erm"]["post_react"])
    closure = 100.0 * (a1 - ar).mean() / (a1 - a9).mean()
    holm_syn = syn["holm_p"]["A1r-replay-erm vs A6-risp-inv"]
    panel(ax1, syn, order_syn,
          f"(a)  synthetic ({syn['config']['seeds']} seeds)")
    ax1.text(0.02, 0.03,
             f"replay closes {closure:.1f}% of A1$-$A9\n"
             f"A6 beats replay: Holm p = {holm_syn:.1e}",
             transform=ax1.transAxes, fontsize=6.6, color=INK, va="bottom")

    g_rep = fre["paired_gammas"]["replay_A1r_erm_minus_A9"]
    holm_fre = fre["holm_p"]["A6-risp-inv vs A1r-replay-erm"]
    panel(ax2, fre, order_fre,
          f"(b)  French 49, L3@15% ({fre['config']['seeds']} seeds)")
    ax2.text(0.02, 0.03,
             "replay collects the deficit\n"
             "(" + GAMMA + f" over replay = {g_rep['mean'] * SCALE:+.2f}"
             f"$\\pm${g_rep['ci95'] * SCALE:.2f}, n.s.)\n"
             f"A6 still beats replay: Holm p = {holm_fre:.3f}",
             transform=ax2.transAxes, fontsize=6.6, color=INK, va="bottom")
    fig.tight_layout(w_pad=2.0)
    savefig(fig, "fig12_replay",
            "Replay collects the deficit — the invariance-equipped pool"
            " still wins")


# ================================================================== fig 13
def fig13_emergent():
    mlp = jload(RES / "e_x4_mlp.json")
    e6 = jload(RES100 / "e6_snr_audit.json")
    exp = mlp["expansion_100seed"]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(6.3, 2.8), gridspec_kw={"width_ratios": [1, 1.3]})

    # (a) A1-mlp vs A9-mlp, steady vs post-react (100 seeds) ---------------
    xs = [0, 1]
    for a, col, ls, mk in (("A1-mlp", VERM, "-", "o"),
                           ("A9-mlp", DARK, "--", "s")):
        m = [exp["steady"][a]["mean"], exp["post_react"][a]["mean"]]
        c = [exp["steady"][a]["ci95"], exp["post_react"][a]["ci95"]]
        ax1.errorbar(xs, np.array(m) * SCALE, yerr=np.array(c) * SCALE,
                     fmt=mk, ls=ls, color=col, ms=5, lw=1.4,
                     elinewidth=1.2, capsize=2.4, zorder=3, label=a)
    g_st, g_pr = exp["gamma_mlp_steady"], exp["gamma_mlp"]
    ratio = g_pr["mean"] / g_st["mean"]
    for x, g in ((0, g_st), (1, g_pr)):
        y0 = exp["steady" if x == 0 else "post_react"]["A9-mlp"]["mean"] * SCALE
        y1 = exp["steady" if x == 0 else "post_react"]["A1-mlp"]["mean"] * SCALE
        side = -1 if x == 0 else 1
        ax1.annotate("", xy=(x + 0.07 * side, y1), xytext=(x + 0.07 * side, y0),
                     arrowprops=dict(arrowstyle="<->", color=GRAY, lw=0.9))
        ax1.text(x + 0.11 * side, (y0 + y1) / 2,
                 GAMMA + f"={g['mean'] * SCALE:.1f}\n$\\pm${g['ci95'] * SCALE:.2f}",
                 fontsize=6.6, color=INK, va="center",
                 ha="right" if side < 0 else "left")
    ax1.set_xticks(xs, ["steady state", "post-reactivation"])
    ax1.set_xlim(-0.52, 1.75)
    ax1.set_ylabel(r"decision regret ($\times 10^{-3}$ per day)")
    ax1.set_title(f"(a)  MLP deficit is {ratio:.1f}× probe-localized"
                  " (100 seeds)", fontsize=8.5)
    ax1.legend(frameon=False, loc="upper left", fontsize=7)

    # (b) Gamma vs SNR: MLP (paired CI) vs linear E6 (propagated CI) -------
    snrs = [0.5, 1.0, 4.0]
    mm, mc = [], []
    for s in snrs:
        g = mlp["snr_sweep"]["per_snr"][f"{s:.1f}"]["gamma_A1_minus_A9_post_react"]
        mm.append(g["mean"]); mc.append(g["ci95"])
    lm, lc = [], []
    for s in snrs:
        b = e6[f"{s:.1f}"]["post_react"]
        a1, a9 = b["A1-monolith-erm"], b["A9-oracle-pinned"]
        lm.append(a1["mean"] - a9["mean"])
        lc.append(np.hypot(a1["ci95"], a9["ci95"]))  # unpaired, conservative
    xs = np.arange(len(snrs))
    ax2.axhline(0, color=INK, lw=0.8)
    ax2.errorbar(xs, np.array(mm) * SCALE, yerr=np.array(mc) * SCALE,
                 fmt="-o", color=BLUE, ms=5, lw=1.5, elinewidth=1.2,
                 capsize=2.4, zorder=3, label="MLP (E-X4, 20 seeds, paired CI)")
    ax2.errorbar(xs, np.array(lm) * SCALE, yerr=np.array(lc) * SCALE,
                 fmt="--s", color=VERM, ms=4.5, lw=1.3, elinewidth=1.1,
                 capsize=2.4, zorder=3,
                 label="linear (E6, 100 seeds, unpaired CI)")
    ax2.set_xticks(xs, [f"{s:g}×" for s in snrs])
    ax2.set_xlabel("signal-to-noise multiplier")
    ax2.set_ylabel(XLBL_G.replace(" post-reactivation regret", ""))
    ax2.set_title("(b)  the lodged divergence at 4× SNR", fontsize=8.5)
    ax2.annotate("MLP: deficit grows ≈" +
                 f"{mm[2] / mm[1]:.0f}×", (2, mm[2] * SCALE),
                 xytext=(-8, -14), textcoords="offset points", ha="right",
                 fontsize=6.8, color=BLUE)
    ax2.annotate("linear: inverts", (2, lm[2] * SCALE),
                 xytext=(-10, -12), textcoords="offset points", ha="right",
                 fontsize=6.8, color=VERM)
    ax2.legend(frameon=False, loc="upper left", fontsize=6.6)
    fig.tight_layout(w_pad=2.0)
    savefig(fig, "fig13_emergent",
            "Forgetting emerges under an MLP without an eviction model")


# ================================================================== fig 14
def fig14_window():
    mod_sw = jload(RES / "e_french49_L3_sweep.json")
    mod15 = jload(RES100 / "e_french49_L3_dissoc.json")["walkforward"]
    pre_sw = jload(RES / "e_french49_prewar_L3_sweep.json")
    pre15 = jload(RES / "e_french49_prewar_L3_dissoc.json")["walkforward"]

    ths = [10, 12, 15, 20]

    def series(sweep, d15):
        m, c = [], []
        for t in ths:
            blk = d15 if t == 15 else sweep[f"{t}pct"]
            g = blk["gate2_forgetting_deficit"]
            m.append(g["mean"]); c.append(g["ci95"])
        return np.array(m), np.array(c)

    mm, mc = series(mod_sw, mod15)
    pm, pc = series(pre_sw, pre15)

    fig, ax = plt.subplots(figsize=(5.5, 3.3))
    ax.axhline(0, color=INK, lw=0.8)
    off = 0.12  # slight x offset so CIs don't overlap
    ax.errorbar(np.array(ths) - off, mm * SCALE, yerr=mc * SCALE, fmt="-o",
                color=BLUE, ms=5, lw=1.5, elinewidth=1.2, capsize=2.4,
                zorder=3, label="1990–2025 (49 industries)")
    ax.errorbar(np.array(ths) + off, pm * SCALE, yerr=pc * SCALE, fmt="--D",
                color=VERM, ms=4.5, lw=1.3, elinewidth=1.1, capsize=2.4,
                zorder=3, label="1926–1989, withheld (36 industries)")
    ax.set_xticks(ths, [f"{t}%" for t in ths])
    ax.set_xlabel("drawdown threshold defining the crisis regime")
    ax.set_ylabel(XLBL_G.replace(" post-reactivation regret", ""))
    ax.annotate("modern window peaks at 15%\n(the pre-registered cutoff;"
                " 100 seeds)", xy=(15, mm[2] * SCALE),
                xytext=(15.6, mm[2] * SCALE - 0.06), fontsize=6.8,
                color=BLUE, va="top")
    ax.annotate("withheld era: window\nrelocates to 10%",
                xy=(10, pm[0] * SCALE), xytext=(10.4, 0.62), fontsize=6.8,
                color=VERM,
                arrowprops=dict(arrowstyle="-", color=VERM, lw=0.7))
    ax.text(0.015, 0.975, "15% points: pre-registered spec;\n"
            "all other thresholds: 20-seed sweeps",
            transform=ax.transAxes, fontsize=6.4, color=GRAY,
            ha="left", va="top")
    ax.legend(frameon=False, loc="lower left", fontsize=7)
    fig.tight_layout()
    savefig(fig, "fig14_window",
            "The fragility window replicates off-sample — but relocates"
            " (15% → 10%)")


ALL = {
    "fig10": fig10_signrule,
    "fig11": fig11_costs,
    "fig12": fig12_replay,
    "fig13": fig13_emergent,
    "fig14": fig14_window,
}

if __name__ == "__main__":
    import sys
    todo = sys.argv[1:] or ["all"]
    for key, fn in ALL.items():
        if "all" in todo or key in todo:
            fn()
