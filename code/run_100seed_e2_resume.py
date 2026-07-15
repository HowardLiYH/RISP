"""Resumable 100-seed E2: skips (K, memory) cells whose JSON already exists,
then assembles e2_capacity_sweep.json from the per-cell files."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_experiments as R

R.RESULTS = Path(__file__).resolve().parent / ".." / "results_100seed"
R.RESULTS.mkdir(exist_ok=True)

ARMS = ["A1-monolith-erm", "A2-router", "A4-randomfixed",
        "A5-risp-erm", "A6-risp-inv", "A9-oracle-pinned"]

t0 = time.time()
out = {}
for memory in ("hard", "soft"):
    out[memory] = {}
    for K in (1, 2, 3, 4):
        tag = f"e2_K{K}_{memory}"
        f = R.RESULTS / f"{tag}.json"
        if f.exists():
            r = json.load(open(f))
            print(f"[skip] {tag} already done", flush=True)
        else:
            print(f"[run ] {tag} ({(time.time()-t0)/60:.1f} min elapsed)",
                  flush=True)
            r = R.e1(seeds=100, K=K, memory=memory, tag=tag, arms=ARMS)
        out[memory][K] = {"post_react": r["post_react"],
                          "overall": r["overall"]}
R.save("e2_capacity_sweep", out)
print("E2 COMPLETE", flush=True)
