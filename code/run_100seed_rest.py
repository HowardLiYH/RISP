"""Finish the 100-seed battery: the two experiments the killed run missed."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_experiments as R

R.RESULTS = Path(__file__).resolve().parent / ".." / "results_100seed"
R.RESULTS.mkdir(exist_ok=True)

t0 = time.time()
for name, fn in [("e5", R.e5), ("e2", R.e2)]:
    t = time.time()
    print(f"=== {name} @ 100 seeds ===", flush=True)
    try:
        fn(seeds=100)
    except Exception as e:
        print(f"!!! {name} FAILED: {e!r}", flush=True)
    print(f"=== {name} done in {(time.time()-t)/60:.1f} min "
          f"(total {(time.time()-t0)/60:.1f} min) ===", flush=True)
print("REST COMPLETE", flush=True)
