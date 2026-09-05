"""Write a Zarr v3 array with zarr-python directly, using the sharding codec.

GDAL's Zarr driver cannot write shards, so this is the one variant built in
Python.  Shards of 2048x2048 hold 8x8 inner chunks of 256x256: the object
count on disk is that of the 2048 variant, while a small read still decodes
only a 256 chunk (fetched via a Range request into the shard).

usage: python scripts/make_sharded.py [--chunk 256] [--shard 2048]
"""
import argparse, time
from pathlib import Path
import numpy as np, rasterio, zarr
from rasterio.windows import Window
from zarr.codecs import BytesCodec, ZstdCodec

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--chunk", type=int, default=256)
ap.add_argument("--shard", type=int, default=2048)
ap.add_argument("--src", default=str(ROOT / "data/out/cog_2048.tif"))
a = ap.parse_args()
dst = ROOT / f"data/out/zarrsh_{a.shard}_{a.chunk}.zarr"

t0 = time.perf_counter()
with rasterio.open(a.src) as ds:
    H, W = ds.height, ds.width
    g = zarr.open_group(str(dst), mode="w", zarr_format=3)
    arr = g.create_array(
        "dem", shape=(H, W), dtype="float32",
        chunks=(a.chunk, a.chunk), shards=(a.shard, a.shard),
        compressors=ZstdCodec(level=9), serializer=BytesCodec(endian="little"),
        fill_value=np.float32(ds.nodata), dimension_names=("y", "x"),
        attributes={"_ARRAY_DIMENSIONS": ["y", "x"], "crs_wkt": ds.crs.to_wkt(),
                    "transform": list(ds.transform)[:6], "nodata": float(ds.nodata)},
    )
    # write shard-aligned blocks so no shard is ever rewritten
    n = 0
    for r in range(0, H, a.shard):
        for c in range(0, W, a.shard):
            h, w = min(a.shard, H - r), min(a.shard, W - c)
            arr[r:r + h, c:c + w] = ds.read(1, window=Window(c, r, w, h))
            n += 1
        print(f"row {r // a.shard + 1}/{-(-H // a.shard)}", flush=True)
files = [f for f in dst.rglob("*") if f.is_file()]
print(f"{dst.name}: {n} shards written, {len(files)} files, {sum(f.stat().st_size for f in files)/1e6:.1f} MB, {time.perf_counter()-t0:.0f} s")
print(arr.info)
