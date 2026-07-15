"""100-seed replication battery.

Reruns E0-E6 at 100 seeds into results_100seed/ (the committed results/
directory keeps the original 20-seed run; seeds 0-19 are bit-identical by
construction since seeding is deterministic in s). Order: cheapest first so
partial results are usable early.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_experiments as R

R.RESULTS = Path(__file__).resolve().parent / ".." / "results_100seed"
R.RESULTS.mkdir(exist_ok=True)

SEEDS = 100
t0 = time.time()
for name, fn in [("e0", R.e0), ("e1", R.e1), ("e1s", R.e1s),
                 ("e4", R.e4), ("e3", R.e3), ("e6", R.e6),
                 ("e5", R.e5), ("e2", R.e2)]:
    t = time.time()
    print(f"=== {name} @ {SEEDS} seeds ===", flush=True)
    try:
        fn(seeds=SEEDS)
    except Exception as e:  # keep the battery going; report at the end
        print(f"!!! {name} FAILED: {e!r}", flush=True)
    print(f"=== {name} done in {(time.time()-t)/60:.1f} min "
          f"(total {(time.time()-t0)/60:.1f} min) ===", flush=True)
print("BATTERY COMPLETE", flush=True)
