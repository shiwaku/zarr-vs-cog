"""Show what a Zarr store and a COG actually look like on disk.

usage: python scripts/inspect_layout.py data/out/zarr_512.zarr data/out/cog_512.tif
"""
import json, sys
from collections import Counter
from pathlib import Path

def inspect_zarr(p: Path):
    files = [f for f in p.rglob("*") if f.is_file()]
    sizes = [f.stat().st_size for f in files]
    meta = [f for f in files if f.name in ("zarr.json", ".zarray", ".zgroup", ".zattrs", ".zmetadata")]
    chunks = [f for f in files if f not in meta]
    print(f"== {p.name}")
    print(f"  files: {len(files)}  (metadata {len(meta)}, chunks {len(chunks)})  total {sum(sizes)/1e6:.1f} MB")
    if chunks:
        cs = sorted(f.stat().st_size for f in chunks)
        print(f"  chunk bytes: min {cs[0]/1e3:.1f} KB  median {cs[len(cs)//2]/1e3:.1f} KB  max {cs[-1]/1e3:.1f} KB")
        print(f"  example chunk key: {chunks[0].relative_to(p).as_posix()}")
    depth = Counter(len(f.relative_to(p).parts) for f in files)
    print(f"  path depth histogram: {dict(sorted(depth.items()))}")
    for m in sorted(meta, key=lambda f: len(f.parts)):
        txt = m.read_text()
        print(f"  -- {m.relative_to(p).as_posix()} ({len(txt)} bytes)")
        try:
            j = json.loads(txt)
            # trim big attribute blobs for display
            s = json.dumps(j, indent=2, ensure_ascii=False)
            print("     " + s.replace("\n", "\n     ")[:2500])
        except Exception:
            print(txt[:800])

def inspect_cog(p: Path):
    import rasterio
    print(f"== {p.name}")
    print(f"  files: 1   total {p.stat().st_size/1e6:.1f} MB")
    with rasterio.open(p) as ds:
        print(f"  driver {ds.driver}  size {ds.width}x{ds.height}  dtype {ds.dtypes[0]}  block {ds.block_shapes[0]}  compress {ds.profile.get('compress')}")
        print(f"  overviews: {ds.overviews(1)}   tags(IMAGE_STRUCTURE): {ds.tags(ns='IMAGE_STRUCTURE')}")
        print(f"  crs: {ds.crs.to_string()[:40]}  transform: {tuple(round(x,3) for x in ds.transform[:6])}")
    # Byte layout of the tile index: read TIFF tags with tifffile-free approach via GDAL metadata
    with rasterio.open(p) as ds:
        try:
            from rasterio._io import DatasetReaderBase
        except Exception:
            pass
        md = ds.tags()
        lay = {k: v for k, v in md.items() if "LAYOUT" in k or "COG" in k}
        if lay: print(f"  tags: {lay}")
    # header size: where does the first tile start? (COG keeps IFD + tile offsets up front)
    with p.open("rb") as f:
        head = f.read(16)
    print(f"  magic: {head[:4]!r}  ({'BigTIFF' if head[2:4] in (b'+\x00', b'\x00+') else 'classic TIFF'})")

for a in sys.argv[1:]:
    p = Path(a)
    if p.is_dir(): inspect_zarr(p)
    else: inspect_cog(p)
    print()
