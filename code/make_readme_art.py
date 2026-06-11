"""Generate README artwork for the RISP repo -> ../assets/*.png"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (Circle, Ellipse, FancyBboxPatch, Polygon,
                                Rectangle, Wedge, FancyArrowPatch, Arc)
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
ASSETS.mkdir(exist_ok=True)

# palette
CALM_SKY = "#FDF6E3"
STORM_SKY = "#4A5568"
SUN = "#F6C453"
ORANGE = "#E28C3C"
BLUE = "#5A82C8"
DBLUE = "#3D6BBF"
GREEN = "#3C915A"
RED = "#C83C3C"
INK = "#2D3748"
BOOK1, BOOK2, BOOK3 = "#C86A4A", "#7A9E7E", "#8C5AC8"


def blob(ax, x, y, r, color, mood="happy", sleep=False, sweat=False,
         cap=False, zlift=1.0):
    """A round character with a face."""
    body = Circle((x, y), r, fc=color, ec=INK, lw=2, zorder=5)
    ax.add_patch(body)
    ex, ey = 0.35 * r, 0.25 * r
    if sleep:
        for sx in (-ex, ex):
            ax.plot([x + sx - 0.16 * r, x + sx + 0.16 * r],
                    [y + ey, y + ey], color=INK, lw=2.2, zorder=6,
                    solid_capstyle="round")
        ax.add_patch(Arc((x, y - 0.15 * r), 0.5 * r, 0.3 * r, theta1=200,
                         theta2=340, color=INK, lw=2.2, zorder=6))
        for i, (dx, dy, s) in enumerate([(1.25, 1.15, 9), (1.6, 1.5, 12),
                                         (2.0, 1.9, 15)]):
            ax.text(x + dx * r, y + dy * r * zlift, "z", fontsize=s,
                    color=INK, style="italic", zorder=6, fontweight="bold")
    else:
        for sx in (-ex, ex):
            ax.add_patch(Circle((x + sx, y + ey), 0.09 * r, fc=INK,
                                zorder=6))
        if mood == "happy":
            ax.add_patch(Arc((x, y - 0.1 * r), 0.7 * r, 0.55 * r,
                             theta1=200, theta2=340, color=INK, lw=2.4,
                             zorder=6))
        elif mood == "panic":
            ax.add_patch(Ellipse((x, y - 0.32 * r), 0.34 * r, 0.42 * r,
                                 fc="white", ec=INK, lw=2, zorder=6))
            for sx in (-ex, ex):  # worried brows
                ax.plot([x + sx - 0.15 * r, x + sx + 0.13 * r],
                        [y + ey + 0.28 * r, y + ey + 0.16 * r],
                        color=INK, lw=2.2, zorder=6,
                        solid_capstyle="round")
    if sweat:
        for dx, dy in [(-1.25, 0.7), (1.2, 0.95), (-0.9, 1.25)]:
            ax.add_patch(Ellipse((x + dx * r, y + dy * r), 0.16 * r,
                                 0.26 * r, fc="#7EC8E3", ec=DBLUE, lw=1,
                                 zorder=6))
    if cap:  # graduation cap
        cx, cy = x, y + 0.95 * r
        ax.add_patch(Polygon([(cx - 0.75 * r, cy), (cx, cy + 0.4 * r),
                              (cx + 0.75 * r, cy), (cx, cy - 0.25 * r)],
                             fc=INK, ec=INK, zorder=7))
        ax.plot([cx + 0.65 * r, cx + 0.8 * r], [cy, cy - 0.45 * r],
                color="#F6C453", lw=2, zorder=7)
        ax.add_patch(Circle((cx + 0.8 * r, cy - 0.5 * r), 0.08 * r,
                            fc="#F6C453", zorder=7))


def book(ax, x, y, w, h, color, label="", fs=8, rot=0):
    bb = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                        boxstyle="round,pad=0.01,rounding_size=0.02",
                        fc=color, ec=INK, lw=1.8, zorder=4)
    if rot:
        from matplotlib import transforms
        tr = transforms.Affine2D().rotate_deg_around(x, y, rot) + ax.transData
        bb.set_transform(tr)
    ax.add_patch(bb)
    if label:
        ax.text(x, y, label, ha="center", va="center", fontsize=fs,
                fontweight="bold", color="white", zorder=5, rotation=rot)


def cover():
    fig, ax = plt.subplots(figsize=(16, 5.6), dpi=160)
    ax.set_xlim(0, 16); ax.set_ylim(0, 5.6); ax.axis("off")
    # skies: calm left, storm right
    ax.add_patch(Rectangle((0, 0), 10.4, 5.6, fc=CALM_SKY, zorder=0))
    ax.add_patch(Rectangle((10.4, 0), 5.6, 5.6, fc=STORM_SKY, zorder=0))
    # sun
    ax.add_patch(Circle((1.3, 4.7), 0.55, fc=SUN, ec="#E0A33C", lw=2, zorder=1))
    for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        ax.plot([1.3 + 0.75 * np.cos(a), 1.3 + 1.0 * np.cos(a)],
                [4.7 + 0.75 * np.sin(a), 4.7 + 1.0 * np.sin(a)],
                color="#E0A33C", lw=2.5, zorder=1, solid_capstyle="round")
    # storm cloud + lightning + rain
    for cx, cy, r in [(12.3, 4.9, 0.5), (12.9, 5.05, 0.62), (13.6, 4.9, 0.5),
                      (14.3, 5.0, 0.55), (15.0, 4.85, 0.45)]:
        ax.add_patch(Circle((cx, cy), r, fc="#2D3748", ec="#1A202C", lw=1.5,
                            zorder=2))
    ax.add_patch(Polygon([(13.1, 4.45), (12.7, 3.6), (13.05, 3.6),
                          (12.6, 2.75), (13.45, 3.4), (13.1, 3.4),
                          (13.5, 4.2)], fc=SUN, ec="#E0A33C", lw=1.5,
                         zorder=3))
    rng = np.random.default_rng(7)
    for _ in range(26):
        rx = rng.uniform(10.7, 15.9); ry = rng.uniform(0.5, 4.2)
        ax.plot([rx, rx - 0.1], [ry, ry - 0.3], color="#A8C4E0", lw=1.6,
                alpha=0.7, zorder=1, solid_capstyle="round")
    # regime ribbon
    ax.text(5.2, 5.36, "CALM MARKETS   (crisis dormant ~300 days)",
            ha="center", fontsize=11.5, color="#8A6D1B", fontweight="bold")
    ax.text(13.2, 2.45, "THE REGIME\nRETURNS", ha="center", fontsize=15,
            color="white", fontweight="bold", zorder=3)
    # divider
    ax.plot([10.4, 10.4], [0, 5.6], color=INK, lw=2, ls=(0, (6, 4)), zorder=3)
    # lane divider
    ax.plot([0.2, 10.2], [2.78, 2.78], color="#CBB98A", lw=1.5,
            ls=(0, (2, 3)), zorder=1)

    # ---- top lane: reward chaser ----
    ax.text(0.35, 4.95, "the reward-chasing allocator", fontsize=12.5,
            color=ORANGE, fontweight="bold", style="italic")
    blob(ax, 4.0, 3.9, 0.52, ORANGE, mood="happy")
    # juggled books
    book(ax, 3.1, 4.6, 0.78, 0.34, BOOK1, "TREND", 7.5, rot=12)
    book(ax, 4.15, 4.88, 0.78, 0.34, BOOK2, "RANGE", 7.5, rot=-8)
    book(ax, 5.0, 4.55, 0.72, 0.34, BOOK3, "VOL", 7.5, rot=18)
    # trash bin with CRISIS book
    ax.add_patch(Polygon([(6.6, 3.35), (7.5, 3.35), (7.38, 4.25),
                          (6.72, 4.25)], fc="#9AA5B1", ec=INK, lw=2, zorder=4))
    ax.plot([6.55, 7.55], [4.27, 4.27], color=INK, lw=2.5, zorder=4,
            solid_capstyle="round")
    book(ax, 7.05, 4.05, 0.85, 0.36, RED, "CRISIS", 8, rot=-25)
    ax.text(7.05, 3.0, "“no P&L,\nno desk”", ha="center", fontsize=9.5,
            color=INK, style="italic")
    ax.annotate("", xy=(6.6, 4.45), xytext=(5.4, 4.35),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6,
                                connectionstyle="arc3,rad=-0.3"))
    # storm side: panic
    blob(ax, 12.0, 3.9, 0.52, ORANGE, mood="panic", sweat=True)
    ax.text(13.55, 4.35, "relearning the crisis\nDURING the crisis…",
            fontsize=10.5, color="#FFD7D7", fontweight="bold", ha="left")
    # jagged red regret line
    xs = np.linspace(12.8, 15.6, 9)
    ys = 3.45 + np.array([0, .45, .1, .5, .2, .42, .12, .3, .05])
    ax.plot(xs, ys, color="#FF6B6B", lw=2.5, zorder=3)

    # ---- bottom lane: risp ----
    ax.text(0.35, 2.42, "the RISP specialist pool", fontsize=12.5,
            color=DBLUE, fontweight="bold", style="italic")
    # busy specialists on active regimes
    blob(ax, 1.8, 1.1, 0.4, "#7A9E7E", mood="happy")
    book(ax, 1.8, 0.45, 0.85, 0.3, BOOK2, "RANGE", 7)
    blob(ax, 3.3, 1.1, 0.4, "#C86A4A", mood="happy")
    book(ax, 3.3, 0.45, 0.85, 0.3, BOOK1, "TREND", 7)
    # the sleeping crisis specialist on its books
    book(ax, 6.4, 0.42, 1.9, 0.3, "#A0522D", "CRISIS  ’08", 8)
    book(ax, 6.4, 0.74, 1.9, 0.3, "#B05A36", "CRISIS  ’20", 8)
    book(ax, 6.4, 1.06, 1.9, 0.3, RED, "CRISIS  ’22", 8)
    blob(ax, 6.4, 1.78, 0.5, BLUE, sleep=True, zlift=0.55)
    ax.text(8.6, 1.6, "retained by\nidentity,\nnot P&L", fontsize=10,
            color=DBLUE, ha="center", style="italic", fontweight="bold")
    # storm side: calm executor
    blob(ax, 12.0, 1.5, 0.52, BLUE, mood="happy", cap=True)
    book(ax, 12.0, 0.62, 1.7, 0.32, GREEN, "INVARIANT PLAYBOOK", 7.5)
    ax.text(13.6, 1.85, "calibrated from day 1 —\nand trained to generalize\nacross  ’08 ≠ ’20 ≠ ’22",
            fontsize=10.5, color="#D7FFE3", fontweight="bold", ha="left")
    xs = np.linspace(13.55, 15.7, 9)
    ys = 0.78 + np.array([0, .06, .03, .1, .05, .12, .08, .14, .12])
    ax.plot(xs, ys, color="#7BE3A0", lw=2.5, zorder=3)
    fig.tight_layout(pad=0.3)
    fig.savefig(ASSETS / "cover.png", facecolor="white")
    plt.close(fig)


def mechanism():
    fig, ax = plt.subplots(figsize=(14, 3.6), dpi=160)
    ax.set_xlim(0, 14); ax.set_ylim(0, 3.6); ax.axis("off")
    panels = [(0.2, "1 · COMPETE", "#FFF7EA"), (4.95, "2 · PIN", "#EEF4FF"),
              (9.7, "3 · RETAIN + GENERALIZE", "#EFFAF2")]
    for x0, title, bg in panels:
        ax.add_patch(FancyBboxPatch((x0, 0.15), 4.1, 3.1,
                     boxstyle="round,pad=0.02,rounding_size=0.12",
                     fc=bg, ec=INK, lw=2))
        ax.text(x0 + 2.05, 3.0, title, ha="center", fontsize=13,
                fontweight="bold", color=INK)
    # P1: four blobs race on window regret
    for i, c in enumerate(["#C86A4A", "#7A9E7E", BLUE, "#8C5AC8"]):
        blob(ax, 0.85 + i * 0.95, 1.7, 0.3, c,
             mood="happy" if i == 2 else "happy")
    ax.add_patch(Polygon([(2.75, 2.35), (2.6, 2.75), (2.9, 2.75)],
                         fc=SUN, ec=INK, lw=1.2))
    ax.text(2.25, 0.62, "20-day windows of decision regret;\nwinner takes the niche (EG update)",
            ha="center", fontsize=9.5, color=INK)
    # P2: lock the map
    maps = [("trend", "#C86A4A"), ("range", "#7A9E7E"), ("vol", "#8C5AC8"),
            ("crisis", BLUE)]
    for i, (r, c) in enumerate(maps):
        y = 2.45 - i * 0.5
        ax.text(5.6, y, r, fontsize=10, color=INK, ha="left",
                fontweight="bold")
        ax.annotate("", xy=(7.6, y + 0.05), xytext=(6.6, y + 0.05),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=2.2))
        blob(ax, 7.95, y + 0.04, 0.21, c)
    ax.text(8.6, 1.62, "$\\alpha \\geq 0.95$\n$\\Rightarrow$ pinned\n(reward-\nindependent)",
            fontsize=9.5, color=INK, ha="center")
    # P3: sleep + formula
    blob(ax, 10.85, 2.0, 0.42, BLUE, sleep=True, zlift=0.8)
    book(ax, 10.85, 1.2, 1.5, 0.3, RED, "episode library", 7.5)
    ax.text(12.6, 2.1, "dormant $\\Rightarrow$ idle\n$\\Rightarrow$ zero foreign\nupdates",
            fontsize=9.5, ha="center", color=INK)
    ax.text(11.75, 0.55,
            "train on  $\\mathrm{Var}_e[\\ell_e] + \\beta\\,\\mathbb{E}_e[\\ell_e]$  across episodes",
            fontsize=10.5, ha="center", color=GREEN, fontweight="bold")
    for x in (4.42, 9.17):
        ax.annotate("", xy=(x + 0.5, 1.7), xytext=(x, 1.7),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=3))
    fig.tight_layout(pad=0.3)
    fig.savefig(ASSETS / "mechanism.png", facecolor="white")
    plt.close(fig)


def results_2x2():
    import json
    res = json.load(open(Path(__file__).resolve().parents[1] /
                         "results" / "e1_synth.json"))
    pr = {a: v["mean"] for a, v in res["post_react"].items()}
    M = np.array([[pr["A1-monolith-erm"], pr["A7-monolith-inv"]],
                  [pr["A5-risp-erm"], pr["A6-risp-inv"]]])
    fig, ax = plt.subplots(figsize=(8.2, 5.2), dpi=160)
    im = ax.imshow(M, cmap="RdYlGn_r", vmin=M.min() * 0.985,
                   vmax=M.max() * 1.015)
    labels = [["monolith (ERM)\n0.0342", "monolith (INV)\n0.0344\n← inert! p=0.88"],
              ["RISP-ERM\n0.0321\n(−6.1%, p=1.3e−3)",
               "RISP-full\n0.0307\n(−10.3%, p=9.2e−7)"]]
    for i in range(2):
        for j in range(2):
            ax.text(j, i, labels[i][j], ha="center", va="center",
                    fontsize=11.5, fontweight="bold", color=INK)
    ax.set_xticks([0, 1], ["ERM training", "Invariant training"], fontsize=12)
    ax.set_yticks([0, 1], ["reward-driven\nallocation",
                           "reward-independent\nallocation"], fontsize=12)
    ax.set_title("Post-reactivation decision regret — the 2×2 dissociation\n"
                 "(20 seeds; an objective cannot help a head that was evicted)",
                 fontsize=12.5)
    fig.colorbar(im, shrink=0.75)
    fig.tight_layout()
    fig.savefig(ASSETS / "results_2x2.png", facecolor="white")
    plt.close(fig)


def honest_audit():
    import json
    root = Path(__file__).resolve().parents[1]
    e6 = json.load(open(root / "results" / "e6_snr_audit.json"))
    snrs = [0.5, 1.0, 2.0, 4.0, 8.0]
    adv = []
    for s in snrs:
        a1 = e6[str(s)]["post_react"]["A1-monolith-erm"]["mean"]
        a6 = e6[str(s)]["post_react"]["A6-risp-inv"]["mean"]
        adv.append(100 * (a1 - a6) / a1)
    e0 = json.load(open(root / "results" / "e0_structure_diagnostic.json"))
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.0), dpi=160)
    ax = axes[0]
    ax.axhspan(-55, 0, color="#FBE9E9", zorder=0)
    ax.axhspan(0, 14, color="#EAF6EE", zorder=0)
    ax.plot(snrs, adv, "-o", color=DBLUE, lw=2.5, ms=6, zorder=3)
    ax.axhline(0, color=INK, lw=1)
    ax.set_xscale("log"); ax.set_xticks(snrs, [f"{s:g}×" for s in snrs])
    ax.set_ylabel("RISP advantage vs monolith (%)")
    ax.set_xlabel("within-regime signal-to-noise")
    ax.text(0.55, 8, "mechanism pays", fontsize=11, color=GREEN,
            fontweight="bold")
    ax.text(3.1, -38, "mechanism inverts:\nchase episodes instead",
            fontsize=11, color=RED, fontweight="bold", ha="center")
    ax.set_title("Audit E6: we measured where our own method loses")
    ax.spines[["top", "right"]].set_visible(False)
    ax = axes[1]
    doms = [("crypto", "L1"), ("crypto", "L2"),
            ("commodities", "L1"), ("commodities", "L2")]
    xs = np.arange(4)
    real = [e0[d][l]["real_mean_regret"] for d, l in doms]
    shuf = [e0[d][l]["shuffled_mean_regret"] for d, l in doms]
    ax.bar(xs - 0.18, real, 0.36, label="true regime labels", color=DBLUE)
    ax.bar(xs + 0.18, shuf, 0.36, label="shuffled labels", color="#B9C4D6")
    ax.set_xticks(xs, [f"{d}\n{l}" for d, l in doms], fontsize=9)
    ax.set_ylabel("decision regret (oracle conditioning)")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("Gate E0: no regime structure in our real panels —\nso we shipped the null, not a backtest")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "honest_audit.png", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    cover(); print("cover.png")
    mechanism(); print("mechanism.png")
    results_2x2(); print("results_2x2.png")
    honest_audit(); print("honest_audit.png")
