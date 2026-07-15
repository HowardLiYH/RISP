"""Seed-parity runs (PREREG D6): French batteries at 100 seeds.
Writes to results_100seed/ so the committed 20-seed provenance is preserved."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e_french, e_french_L3

dest = Path(__file__).resolve().parent / ".." / "results_100seed"
dest.mkdir(exist_ok=True)
e_french.RESULTS = dest
e_french_L3.RESULTS = dest
print("=== e_french @ 100 seeds ===", flush=True)
e_french.main(seeds=100)
print("=== e_french_L3 @ 100 seeds ===", flush=True)
e_french_L3.main(seeds=100)
print("SEED PARITY COMPLETE", flush=True)
