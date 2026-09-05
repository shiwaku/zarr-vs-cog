"""Render results/*.json + convert_times.tsv into results/REPORT.md (markdown tables)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
out = ["# Zarr vs COG: results\n"]

# --- storage
tsv = (R / "convert_times.tsv").read_text().splitlines()[1:]
conv = {l.split("\t")[0]: l.split("\t")[1:] for l in tsv if l.strip()}
def nfiles(name):
    p = ROOT / "data/out" / (name + (".tif" if name.startswith("cog") else ".zarr"))
    if not p.exists(): return 0
    return 1 if p.is_file() else sum(1 for f in p.rglob("*") if f.is_file())
out.append("## Storage (same 24000x24000 float32 DEM, ZSTD level 9, no overviews)\n")
out.append("| variant | files | MB | write s |\n|---|---:|---:|---:|")
for k in sorted(conv, key=lambda k: (k.split("_")[0], int(k.split("_")[1]))):
    sec, byt = conv[k]
    out.append(f"| {k} | {nfiles(k):,} | {int(byt)/1e6:,.0f} | {sec} |")
out.append("")

# --- benchmarks
SECTIONS = [("local", "bench_local.json", "LOCAL reads (warm OS cache; GDAL single-threaded decode)"),
            ("local_mt", "bench_local_mt.json", "LOCAL reads with GDAL_NUM_THREADS=ALL_CPUS (GDAL readers only)"),
            ("http", "bench_http.json", "HTTP reads via local Range server (loopback, ~1 ms/request)"),
            ("http_lat40", "bench_http_lat40ms.json", "HTTP reads with an accidental ~40 ms per-request server delay (S3-like latency)")]
for mode, fname, title in SECTIONS:
    f = R / fname
    if not f.exists(): continue
    rows = json.loads(f.read_text())
    sizes = sorted({r["win"] for r in rows}); chunks = sorted({r["chunk"] for r in rows}); readers = list(dict.fromkeys(r["reader"] for r in rows))
    out.append(f"## {mode.upper()} reads: median ms per random window (window px along top)\n")
    hdr = "| reader | chunk | " + " | ".join(str(s) for s in sizes) + " |"
    out.append(hdr); out.append("|---|---:|" + "---:|" * len(sizes))
    for rd in readers:
        for cs in chunks:
            cells = []
            for s in sizes:
                m = [r for r in rows if r["reader"] == rd and r["chunk"] == cs and r["win"] == s]
                cells.append(f"{m[0]['ms_med']:.1f}" if m else "-")
            out.append(f"| {rd} | {cs} | " + " | ".join(cells) + " |")
    out.append("")
    if mode.startswith("http"):
        out.append("### HTTP requests per window (mean)  /  MB transferred per window\n")
        out.append(hdr); out.append("|---|---:|" + "---:|" * len(sizes))
        for rd in readers:
            for cs in chunks:
                cells = []
                for s in sizes:
                    m = [r for r in rows if r["reader"] == rd and r["chunk"] == cs and r["win"] == s]
                    cells.append(f"{m[0]['reqs']:.1f} / {m[0]['mb']:.2f}" if m and m[0]["reqs"] is not None else "-")
                out.append(f"| {rd} | {cs} | " + " | ".join(cells) + " |")
        out.append("")
    # chunk-size speedup like session #30: largest window, 256 -> 2048
    out.append(f"### {mode}: speedup 256 -> 2048 chunk, and Zarr/COG ratio at 2048\n")
    for s in sizes:
        line = []
        for rd in readers:
            a = [r for r in rows if r["reader"] == rd and r["chunk"] == 256 and r["win"] == s]
            b = [r for r in rows if r["reader"] == rd and r["chunk"] == 2048 and r["win"] == s]
            if a and b: line.append(f"{rd}: x{a[0]['ms_med']/b[0]['ms_med']:.2f}")
        cog = [r for r in rows if r["reader"] == "cog/gdal" and r["chunk"] == 2048 and r["win"] == s]
        zpy = [r for r in rows if r["reader"] == "zarr/py" and r["chunk"] == 2048 and r["win"] == s]
        zg = [r for r in rows if r["reader"] == "zarr/gdal" and r["chunk"] == 2048 and r["win"] == s]
        if cog and zpy: line.append(f"zarr-py/cog @2048 = {zpy[0]['ms_med']/cog[0]['ms_med']:.2f}")
        if cog and zg: line.append(f"zarr-gdal/cog @2048 = {zg[0]['ms_med']/cog[0]['ms_med']:.2f}")
        out.append(f"- window {s}: " + "; ".join(line))
    out.append("")
for mode in ("local", "http"):
    f = R / f"bench_sharded_{mode}.json"
    if not f.exists(): continue
    rows = json.loads(f.read_text()); sizes = sorted({r["win"] for r in rows}); variants = list(dict.fromkeys(r["variant"] for r in rows))
    out.append(f"## Sharded Zarr v3 ({mode}, zarr-python): 2048 shards x 256 inner chunks vs plain 256 / 2048\n")
    out.append("| variant | " + " | ".join(f"{s} px ms" for s in sizes) + (" | reqs / MB @" + " / ".join(str(s) for s in sizes) if mode == "http" else "") + " |")
    out.append("|---|" + "---:|" * len(sizes) + ("---|" if mode == "http" else ""))
    for v in variants:
        m = {r["win"]: r for r in rows if r["variant"] == v}
        line = f"| {v} | " + " | ".join(f"{m[s]['ms_med']:.1f}" for s in sizes)
        if mode == "http": line += " | " + " / ".join(f"{m[s]['reqs']:.0f}r {m[s]['mb']:.1f}MB" for s in sizes)
        out.append(line + " |")
    out.append("")
out.append("""## Caveats

- Writer: COG variants were written by GDAL 3.13 with NUM_THREADS=ALL_CPUS; Zarr variants by GDAL's Zarr driver
  (single-threaded ZSTD), except `zarrsh_2048_256`, written by zarr-python 3.3 (parallel encode).
- Local reads hit the OS page cache, so they measure decode + per-chunk overhead, not disk. `cog/gdal` in the
  first LOCAL table decodes single-threaded; LOCAL_MT sets GDAL_NUM_THREADS=ALL_CPUS. zarr-python decodes
  chunks concurrently by default. The GDAL Zarr driver does not parallelise.
- HTTP server is a Python http.server on loopback. GDAL's /vsicurl pulls large Range responses from it at only
  ~20 MB/s (curl CLI and aiohttp exceed 1 GB/s against the same server), so COG timings for windows that move
  many MB are pessimistic. Request counts and bytes are reliable; compare those across formats.
- `zarr/gdal` request counts in the HTTP_LAT40 table are undercounted (log lines lagged behind parallel
  fetches in that run). The counts in the HTTP table are exact.
- HTTP_LAT40 came from a server bug (re-opening the log file per request cost ~40 ms). It is kept because a
  uniform ~40 ms per request is close to real S3 latency, which is exactly when 1-chunk-per-request Zarr hurts.
""")
(R / "REPORT.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
