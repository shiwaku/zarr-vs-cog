#!/usr/bin/env bash
# Generate COG and Zarr v3 variants of the same source GeoTIFF at 4 chunk sizes.
# Compression is ZSTD level 9 on both sides; COG overviews are disabled so the
# byte counts compare like for like (Zarr has no built-in pyramid).
set -u
SRC='D:\GitHub@shiwaku\zarr-vs-cog\data\src\noto_subset.tif'
OUT='D:\GitHub@shiwaku\zarr-vs-cog\data\out'
G='C:\OSGeo4W\OSGeo4W.bat'
LOG=results/convert_times.tsv
echo -e "variant\tseconds\tbytes" > $LOG
for bs in 256 512 1024 2048; do
  for fmt in cog zarr; do
    name="${fmt}_${bs}"
    t0=$(date +%s.%N)
    if [ $fmt = cog ]; then
      cmd //c "$G gdal_translate -q -of COG -co BLOCKSIZE=$bs -co COMPRESS=ZSTD -co LEVEL=9 -co OVERVIEWS=NONE -co BIGTIFF=YES -co NUM_THREADS=ALL_CPUS $SRC $OUT\$name.tif"
      bytes=$(stat -c %s data/out/$name.tif)
    else
      cmd //c "$G gdal_translate -q -of Zarr -co FORMAT=ZARR_V3 -co BLOCKSIZE=$bs,$bs -co COMPRESS=ZSTD -co ZSTD_LEVEL=9 -co ARRAY_NAME=dem $SRC $OUT\$name.zarr"
      bytes=$(du -sb data/out/$name.zarr | cut -f1)
    fi
    t1=$(date +%s.%N)
    printf "%s\t%.1f\t%s\n" $name $(echo "$t1 - $t0" | bc) $bytes | tee -a $LOG
  done
done
# One Zarr v2 at 512 to compare the on-disk layout / metadata with v3.
t0=$(date +%s.%N)
cmd //c "$G gdal_translate -q -of Zarr -co FORMAT=ZARR_V2 -co BLOCKSIZE=512,512 -co COMPRESS=ZSTD -co ZSTD_LEVEL=9 -co ARRAY_NAME=dem $SRC $OUT\zarrv2_512.zarr"
t1=$(date +%s.%N)
printf "%s\t%.1f\t%s\n" zarrv2_512 $(echo "$t1 - $t0" | bc) $(du -sb data/out/zarrv2_512.zarr | cut -f1) | tee -a $LOG
echo DONE
