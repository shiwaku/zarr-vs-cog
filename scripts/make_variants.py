"""Generate COG and Zarr v3 variants of the same GeoTIFF at 4 chunk sizes.

Both sides use ZSTD level 9.  COG overviews are disabled so the byte counts
compare like for like (Zarr has no built-in pyramid).  Uses the OSGeo4W GDAL
(3.13) because it ships the Zarr driver with ZARR_V3 support.
"""
import os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/src/noto_subset.tif"
OUT = ROOT / "data/out"
LOG = ROOT / "results/convert_times.tsv"
O4W = r"C:\OSGeo4W\OSGeo4W.bat"

def du(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

def run(name, args, dst: Path):
    if dst.exists():
        print(f"skip {name} (exists)"); return
    t0 = time.perf_counter()
    cmd = ["cmd", "/c", O4W, "gdal_translate", "-q", *args, str(SRC), str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    if r.returncode != 0 or not dst.exists():
        print(f"FAIL {name}: rc={r.returncode}\n{r.stdout}\n{r.stderr}", flush=True); return
    line = f"{name}\t{dt:.1f}\t{du(dst)}"
    print(line, flush=True)
    with LOG.open("a") as f: f.write(line + "\n")

if not LOG.exists():
    LOG.write_text("variant\tseconds\tbytes\n")
for bs in (256, 512, 1024, 2048):
    run(f"cog_{bs}", ["-of", "COG", "-co", f"BLOCKSIZE={bs}", "-co", "COMPRESS=ZSTD", "-co", "LEVEL=9",
                      "-co", "OVERVIEWS=NONE", "-co", "BIGTIFF=YES", "-co", "NUM_THREADS=ALL_CPUS"],
        OUT / f"cog_{bs}.tif")
    run(f"zarr_{bs}", ["-of", "Zarr", "-co", "FORMAT=ZARR_V3", "-co", f"BLOCKSIZE={bs},{bs}",
                       "-co", "COMPRESS=ZSTD", "-co", "ZSTD_LEVEL=9", "-co", "ARRAY_NAME=dem"],
        OUT / f"zarr_{bs}.zarr")
# One Zarr v2 at 512 to compare on-disk layout / metadata with v3.
run("zarrv2_512", ["-of", "Zarr", "-co", "FORMAT=ZARR_V2", "-co", "BLOCKSIZE=512,512",
                   "-co", "COMPRESS=ZSTD", "-co", "ZSTD_LEVEL=9", "-co", "ARRAY_NAME=dem"],
    OUT / "zarrv2_512.zarr")
print("DONE")
