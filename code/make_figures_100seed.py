"""Regenerate paper figures from the 100-seed replication.

Monkeypatches make_figures.RES to results_100seed/ (same pattern as
run_100seed_battery.py monkeypatches run_experiments.RESULTS) and rebuilds
every JSON-driven figure into paper/figures/ under the same filenames.

fig7_trace is intentionally NOT rerun: it re-simulates its own fixed
8-seed traces and does not read the results directory, so it is unchanged
by the 100-seed promotion.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_figures as MF

MF.RES = Path(__file__).resolve().parents[1] / "results_100seed"

if __name__ == "__main__":
    MF.fig1_2x2()
    print("[ok] fig1_2x2")
    MF.fig_arms(title="Post-reactivation regret by arm (synthetic, 100 seeds)")
    print("[ok] fig2_arms")
    MF.fig_capacity()
    print("[ok] fig3_capacity")
    MF.fig_dormancy()
    print("[ok] fig4_dormancy")
    MF.fig_het()
    print("[ok] fig5_heterogeneity")
    MF.fig_snr()
    print("[ok] fig6_snr_audit")
    MF.fig_ablations()
    print("[ok] fig8_ablations")
    MF.fig_arms("e1s_stitched_crypto", "fig9_stitched.pdf",
                "Post-reactivation regret (regime-stitched crypto, 100 seeds)")
    print("[ok] fig9_stitched")
