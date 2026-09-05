"""Benchmark random-window reads on COG vs Zarr v3, locally or over HTTP.

For every variant and window size, read N random square windows and record
wall time, chunks touched (analytic), and -- in HTTP mode -- the number of
HTTP requests the read cost (from the range_server log).

Readers:
  cog/gdal   : rasterio (GDAL, C++)               -> the usual COG path
  zarr/py    : zarr-python 3 (pure Python store)  -> the usual Zarr path
  zarr/gdal  : rasterio + GDAL Zarr driver        -> same format, C++ reader
The third one isolates "format" from "reader implementation", which is the
question session #30 at FOSS4G Hiroshima 2026 left open.

usage: python scripts/bench.py [local|http] [--sizes 64,512,2048,8192] [--n 8]
"""
import argparse, json, math, os, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/out"
LOG = ROOT / "results/http_requests.log"
BASE_URL = "http://127.0.0.1:8765"  # not "localhost": IPv6 fallback cost aiohttp ~10 s on Windows
CHUNKS = (256, 512, 1024, 2048)
W = H = 24000

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["local", "http"], nargs="?", default="local")
ap.add_argument("--sizes", default="64,512,2048,8192")
ap.add_argument("--n", type=int, default=8)
ap.add_argument("--readers", default="cog/gdal,zarr/py,zarr/gdal")
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--tag", default="", help="suffix for the results file, e.g. mt")
args = ap.parse_args()
SIZES = [int(s) for s in args.sizes.split(",")]
READERS = args.readers.split(",")

# GDAL: no directory listing on open, no read cache across reads so each window is a cold read.
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_NON_CACHED", f"{BASE_URL}/")
os.environ.setdefault("GDAL_CACHEMAX", "64")
os.environ.setdefault("VSI_CACHE", "FALSE")
os.environ.setdefault("GDAL_HTTP_MULTIRANGE", "YES")
os.environ.setdefault("GDAL_INGESTED_BYTES_AT_OPEN", "32768")
os.environ.setdefault("GDAL_PAM_ENABLED", "NO")  # no .aux.xml probing over HTTP

import rasterio
from rasterio.windows import Window
import zarr

def log_lines():
    return sum(1 for _ in LOG.open()) if LOG.exists() else 0

def chunks_touched(row, col, size, cs):
    r0, r1 = row // cs, (row + size - 1) // cs
    c0, c1 = col // cs, (col + size - 1) // cs
    return (r1 - r0 + 1) * (c1 - c0 + 1)

def path_for(kind, cs, gdal=False):
    if args.mode == "local":
        p = OUT / (f"cog_{cs}.tif" if kind == "cog" else f"zarr_{cs}.zarr")
        return str(p)
    url = f"{BASE_URL}/" + (f"cog_{cs}.tif" if kind == "cog" else f"zarr_{cs}.zarr")
    return ("/vsicurl/" + url) if gdal else url

def open_reader(reader, cs):
    kind, impl = reader.split("/")
    if impl == "gdal":
        p = path_for(kind, cs, gdal=True)
        if kind == "zarr":
            p = f'ZARR:"{p}":/dem'
        ds = rasterio.open(p)
        def read(row, col, size):
            return ds.read(1, window=Window(col, row, size, size))
        return read, ds.close
    else:  # zarr-python
        p = path_for(kind, cs)
        arr = zarr.open_array(p, mode="r", path="dem", zarr_format=3) if args.mode == "local" else zarr.open_array(p + "/dem", mode="r", zarr_format=3)
        def read(row, col, size):
            return arr[row:row + size, col:col + size]
        return read, (lambda: None)

rng = np.random.default_rng(args.seed)
# same windows for every variant: (row, col) per (size, i)
windows = {s: [(int(rng.integers(0, H - s)), int(rng.integers(0, W - s))) for _ in range(args.n)] for s in SIZES}

rows = []
print(f"mode={args.mode} sizes={SIZES} n={args.n} readers={READERS}", flush=True)
print(f"{'reader':10s} {'chunk':>5s} {'win':>6s} {'ms_med':>8s} {'ms_p95':>8s} {'chunks':>7s} {'reqs':>5s} {'MB_read':>8s}", flush=True)
for reader in READERS:
    kind = reader.split("/")[0]
    for cs in CHUNKS:
        try:
            read, close = open_reader(reader, cs)
        except Exception as e:
            print(f"{reader:10s} {cs:5d}  OPEN FAILED: {e}", flush=True); continue
        # warm the metadata once so timings are per-window, not per-open
        read(0, 0, 8)
        for s in SIZES:
            ts, reqs, mbs, chk = [], [], [], []
            for (r, c) in windows[s]:
                l0 = log_lines() if args.mode == "http" else 0
                t0 = time.perf_counter()
                a = read(r, c, s)
                dt = (time.perf_counter() - t0) * 1000
                assert a.shape == (s, s), a.shape
                ts.append(dt); chk.append(chunks_touched(r, c, s, cs))
                if args.mode == "http":
                    time.sleep(0.05)  # let the server flush its log lines
                    lines = LOG.open().read().splitlines()[l0:]
                    reqs.append(len(lines))
                    mbs.append(sum(int(x.split("\t")[5]) for x in lines if int(x.split("\t")[5]) > 0) / 1e6)
            row = dict(mode=args.mode, reader=reader, chunk=cs, win=s,
                       ms_med=float(np.median(ts)), ms_p95=float(np.percentile(ts, 95)),
                       chunks=float(np.mean(chk)),
                       reqs=float(np.mean(reqs)) if reqs else None,
                       mb=float(np.mean(mbs)) if mbs else None)
            rows.append(row)
            print(f"{reader:10s} {cs:5d} {s:6d} {row['ms_med']:8.1f} {row['ms_p95']:8.1f} {row['chunks']:7.1f} "
                  f"{(row['reqs'] if row['reqs'] is not None else float('nan')):5.1f} "
                  f"{(row['mb'] if row['mb'] is not None else float('nan')):8.2f}", flush=True)
        close()

out = ROOT / f"results/bench_{args.mode}{'_' + args.tag if args.tag else ''}.json"
out.write_text(json.dumps(rows, indent=1))
print("saved", out)
