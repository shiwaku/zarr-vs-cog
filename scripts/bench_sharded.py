"""Compare the sharded Zarr (2048 shards / 256 inner chunks) against plain 256 and 2048
Zarr, all read with zarr-python, same random windows as bench.py.

usage: python scripts/bench_sharded.py [local|http] [--n 8]
"""
import argparse, json, time, os
from pathlib import Path
import numpy as np, zarr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/out"; LOG = ROOT / "results/http_requests.log"
BASE_URL = "http://127.0.0.1:8765"
ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["local", "http"], nargs="?", default="local")
ap.add_argument("--n", type=int, default=8); ap.add_argument("--sizes", default="64,512,2048,8192"); ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args(); SIZES = [int(s) for s in args.sizes.split(",")]
W = H = 24000
VARIANTS = [("zarr_256", 256), ("zarrsh_2048_256", 256), ("zarr_2048", 2048)]

def loglines(): return open(LOG).read().splitlines() if LOG.exists() else []
def chunks_touched(row, col, size, cs):
    return ((row + size - 1) // cs - row // cs + 1) * ((col + size - 1) // cs - col // cs + 1)

rng = np.random.default_rng(args.seed)
windows = {s: [(int(rng.integers(0, H - s)), int(rng.integers(0, W - s))) for _ in range(args.n)] for s in SIZES}
rows = []
print(f"mode={args.mode}  {'variant':16s} {'win':>6s} {'ms_med':>8s} {'ms_p95':>8s} {'chunks':>7s} {'reqs':>6s} {'MB':>7s}")
for name, cs in VARIANTS:
    p = str(OUT / f"{name}.zarr") if args.mode == "local" else f"{BASE_URL}/{name}.zarr"
    arr = zarr.open_array(p, mode="r", path="dem", zarr_format=3) if args.mode == "local" else zarr.open_array(p + "/dem", mode="r", zarr_format=3)
    arr[0:8, 0:8]
    for s in SIZES:
        ts, reqs, mbs, chk = [], [], [], []
        for r, c in windows[s]:
            l0 = len(loglines()) if args.mode == "http" else 0
            t0 = time.perf_counter(); a = arr[r:r + s, c:c + s]; dt = (time.perf_counter() - t0) * 1000
            assert a.shape == (s, s)
            ts.append(dt); chk.append(chunks_touched(r, c, s, cs))
            if args.mode == "http":
                time.sleep(0.05); L = loglines()[l0:]
                reqs.append(len(L)); mbs.append(sum(int(x.split("\t")[5]) for x in L if int(x.split("\t")[5]) > 0) / 1e6)
        row = dict(mode=args.mode, variant=name, win=s, ms_med=float(np.median(ts)), ms_p95=float(np.percentile(ts, 95)),
                   chunks=float(np.mean(chk)), reqs=float(np.mean(reqs)) if reqs else None, mb=float(np.mean(mbs)) if mbs else None)
        rows.append(row)
        print(f"{'':11s}{name:16s} {s:6d} {row['ms_med']:8.1f} {row['ms_p95']:8.1f} {row['chunks']:7.1f} "
              f"{(row['reqs'] if row['reqs'] is not None else float('nan')):6.1f} {(row['mb'] if row['mb'] is not None else float('nan')):7.2f}", flush=True)
    if args.mode == "http" and name.startswith("zarrsh"):
        # show what the shard reads look like: Range requests into shard objects
        for x in loglines()[-3:]:
            t, m, pth, rg, st, b = x.split("\t"); print(f"{'':11s}  e.g. {m} {pth.split('/')[-3:]} {rg} -> {b} bytes")
out = ROOT / f"results/bench_sharded_{args.mode}.json"; out.write_text(json.dumps(rows, indent=1)); print("saved", out)
