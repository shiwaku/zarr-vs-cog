# Zarr vs COG: results

## Storage (same 24000x24000 float32 DEM, ZSTD level 9, no overviews)

| variant | files | MB | write s |
|---|---:|---:|---:|
| cog_256 | 1 | 1,028 | 48.3 |
| cog_512 | 1 | 995 | 41.4 |
| cog_1024 | 1 | 973 | 19.5 |
| cog_2048 | 1 | 970 | 20.6 |
| zarr_256 | 8,842 | 1,020 | 591.9 |
| zarr_512 | 2,215 | 995 | 193.5 |
| zarr_1024 | 582 | 973 | 86.7 |
| zarr_2048 | 150 | 971 | 66.8 |
| zarrsh_2048_256 | 146 | 1,020 | 33 |
| zarrv2_512 | 2,219 | 995 | - |

## LOCAL reads: median ms per random window (window px along top)

| reader | chunk | 64 | 512 | 2048 | 8192 |
|---|---:|---:|---:|---:|---:|
| cog/gdal | 256 | 0.5 | 3.8 | 34.3 | 477.1 |
| cog/gdal | 512 | 1.5 | 6.2 | 40.9 | 490.7 |
| cog/gdal | 1024 | 8.6 | 11.6 | 54.9 | 544.9 |
| cog/gdal | 2048 | 24.3 | 26.8 | 102.0 | 693.6 |
| zarr/py | 256 | 2.3 | 4.5 | 38.8 | 515.4 |
| zarr/py | 512 | 2.4 | 4.6 | 21.4 | 250.9 |
| zarr/py | 1024 | 8.7 | 9.9 | 21.6 | 238.3 |
| zarr/py | 2048 | 27.2 | 28.5 | 54.5 | 261.9 |
| zarr/gdal | 256 | 0.8 | 6.7 | 39.5 | 540.6 |
| zarr/gdal | 512 | 1.4 | 5.9 | 40.0 | 489.6 |
| zarr/gdal | 1024 | 5.7 | 11.2 | 54.6 | 531.0 |
| zarr/gdal | 2048 | 23.5 | 23.9 | 95.9 | 658.1 |

### local: speedup 256 -> 2048 chunk, and Zarr/COG ratio at 2048

- window 64: cog/gdal: x0.02; zarr/py: x0.08; zarr/gdal: x0.03; zarr-py/cog @2048 = 1.12; zarr-gdal/cog @2048 = 0.97
- window 512: cog/gdal: x0.14; zarr/py: x0.16; zarr/gdal: x0.28; zarr-py/cog @2048 = 1.06; zarr-gdal/cog @2048 = 0.89
- window 2048: cog/gdal: x0.34; zarr/py: x0.71; zarr/gdal: x0.41; zarr-py/cog @2048 = 0.53; zarr-gdal/cog @2048 = 0.94
- window 8192: cog/gdal: x0.69; zarr/py: x1.97; zarr/gdal: x0.82; zarr-py/cog @2048 = 0.38; zarr-gdal/cog @2048 = 0.95

## LOCAL_MT reads: median ms per random window (window px along top)

| reader | chunk | 64 | 512 | 2048 | 8192 |
|---|---:|---:|---:|---:|---:|
| cog/gdal | 256 | 0.5 | 1.5 | 9.5 | 122.7 |
| cog/gdal | 512 | 1.5 | 2.9 | 10.7 | 116.5 |
| cog/gdal | 1024 | 6.0 | 7.8 | 17.7 | 147.4 |
| cog/gdal | 2048 | 24.9 | 27.0 | 53.8 | 208.5 |
| zarr/gdal | 256 | 0.5 | 4.2 | 41.7 | 551.3 |
| zarr/gdal | 512 | 1.4 | 5.9 | 42.4 | 498.4 |
| zarr/gdal | 1024 | 5.5 | 11.2 | 55.7 | 541.5 |
| zarr/gdal | 2048 | 22.2 | 24.1 | 97.8 | 667.2 |

### local_mt: speedup 256 -> 2048 chunk, and Zarr/COG ratio at 2048

- window 64: cog/gdal: x0.02; zarr/gdal: x0.02; zarr-gdal/cog @2048 = 0.89
- window 512: cog/gdal: x0.06; zarr/gdal: x0.17; zarr-gdal/cog @2048 = 0.89
- window 2048: cog/gdal: x0.18; zarr/gdal: x0.43; zarr-gdal/cog @2048 = 1.82
- window 8192: cog/gdal: x0.59; zarr/gdal: x0.83; zarr-gdal/cog @2048 = 3.20

## HTTP reads: median ms per random window (window px along top)

| reader | chunk | 64 | 512 | 2048 | 8192 |
|---|---:|---:|---:|---:|---:|
| cog/gdal | 256 | 1.4 | 6.0 | 58.2 | 1692.4 |
| cog/gdal | 512 | 2.5 | 9.1 | 153.6 | 2815.0 |
| cog/gdal | 1024 | 19.6 | 59.4 | 387.0 | 4109.7 |
| cog/gdal | 2048 | 268.9 | 334.0 | 1165.5 | 8138.5 |
| zarr/py | 256 | 1.8 | 6.4 | 53.7 | 718.5 |
| zarr/py | 512 | 3.3 | 6.7 | 33.1 | 401.0 |
| zarr/py | 1024 | 9.2 | 16.1 | 35.5 | 377.3 |
| zarr/py | 2048 | 41.8 | 44.1 | 81.3 | 417.6 |
| zarr/gdal | 256 | 3.0 | 17.3 | 156.5 | 2159.0 |
| zarr/gdal | 512 | 3.8 | 13.1 | 84.2 | 1000.8 |
| zarr/gdal | 1024 | 11.0 | 25.7 | 122.6 | 1022.4 |
| zarr/gdal | 2048 | 32.0 | 53.1 | 153.0 | 1101.8 |

### HTTP requests per window (mean)  /  MB transferred per window

| reader | chunk | 64 | 512 | 2048 | 8192 |
|---|---:|---:|---:|---:|---:|
| cog/gdal | 256 | 1.5 / 0.16 | 3.0 / 1.11 | 9.2 / 9.53 | 165.2 / 157.75 |
| cog/gdal | 512 | 1.0 / 0.44 | 2.0 / 1.88 | 6.8 / 12.05 | 85.0 / 168.03 |
| cog/gdal | 1024 | 1.0 / 1.72 | 1.4 / 3.92 | 5.9 / 17.84 | 46.2 / 165.12 |
| cog/gdal | 2048 | 1.0 / 6.71 | 1.6 / 9.21 | 4.4 / 29.76 | 25.2 / 192.08 |
| zarr/py | 256 | 1.5 / 0.14 | 9.0 / 1.11 | 81.0 / 9.44 | 1089.0 / 131.24 |
| zarr/py | 512 | 1.0 / 0.42 | 4.0 / 1.88 | 25.0 / 11.35 | 289.0 / 135.74 |
| zarr/py | 1024 | 1.0 / 1.71 | 2.1 / 3.91 | 9.0 / 15.98 | 81.0 / 148.78 |
| zarr/py | 2048 | 1.0 / 6.70 | 1.2 / 9.18 | 4.0 / 28.05 | 25.0 / 180.77 |
| zarr/gdal | 256 | 1.5 / 0.14 | 9.0 / 1.11 | 81.0 / 9.44 | 1089.0 / 131.24 |
| zarr/gdal | 512 | 1.0 / 0.42 | 4.0 / 1.88 | 25.0 / 11.35 | 289.0 / 135.74 |
| zarr/gdal | 1024 | 2.0 / 3.42 | 4.2 / 7.82 | 17.8 / 31.51 | 114.6 / 210.22 |
| zarr/gdal | 2048 | 2.0 / 13.40 | 2.5 / 18.36 | 7.5 / 52.60 | 33.2 / 237.51 |

### http: speedup 256 -> 2048 chunk, and Zarr/COG ratio at 2048

- window 64: cog/gdal: x0.01; zarr/py: x0.04; zarr/gdal: x0.09; zarr-py/cog @2048 = 0.16; zarr-gdal/cog @2048 = 0.12
- window 512: cog/gdal: x0.02; zarr/py: x0.15; zarr/gdal: x0.33; zarr-py/cog @2048 = 0.13; zarr-gdal/cog @2048 = 0.16
- window 2048: cog/gdal: x0.05; zarr/py: x0.66; zarr/gdal: x1.02; zarr-py/cog @2048 = 0.07; zarr-gdal/cog @2048 = 0.13
- window 8192: cog/gdal: x0.21; zarr/py: x1.72; zarr/gdal: x1.96; zarr-py/cog @2048 = 0.05; zarr-gdal/cog @2048 = 0.14

## HTTP_LAT40 reads: median ms per random window (window px along top)

| reader | chunk | 64 | 512 | 2048 | 8192 |
|---|---:|---:|---:|---:|---:|
| cog/gdal | 256 | 8.1 | 93.1 | 339.0 | 7545.0 |
| cog/gdal | 512 | 2.8 | 33.0 | 318.5 | 4911.4 |
| cog/gdal | 1024 | 32.6 | 61.9 | 457.1 | 4393.9 |
| cog/gdal | 2048 | 269.6 | 340.5 | 1178.3 | 8204.7 |
| zarr/py | 256 | 1.8 | 330.9 | 3352.2 | 47874.1 |
| zarr/py | 512 | 3.2 | 113.5 | 1121.4 | 12750.8 |
| zarr/py | 1024 | 15.5 | 14.9 | 314.4 | 3426.6 |
| zarr/py | 2048 | 33.3 | 37.0 | 85.2 | 1017.6 |
| zarr/gdal | 256 | 2.3 | 17.5 | 166.1 | 2376.5 |
| zarr/gdal | 512 | 3.3 | 13.2 | 84.8 | 1033.4 |
| zarr/gdal | 1024 | 10.1 | 25.0 | 114.1 | 1075.3 |
| zarr/gdal | 2048 | 45.9 | 44.6 | 137.6 | 1003.4 |

### HTTP requests per window (mean)  /  MB transferred per window

| reader | chunk | 64 | 512 | 2048 | 8192 |
|---|---:|---:|---:|---:|---:|
| cog/gdal | 256 | 1.5 / 0.16 | 2.9 / 1.06 | 8.6 / 8.83 | 166.0 / 158.49 |
| cog/gdal | 512 | 1.0 / 0.44 | 2.0 / 1.88 | 6.6 / 11.99 | 85.0 / 168.03 |
| cog/gdal | 1024 | 1.0 / 1.72 | 1.4 / 3.92 | 5.9 / 17.84 | 46.2 / 165.12 |
| cog/gdal | 2048 | 1.0 / 6.71 | 1.6 / 9.21 | 4.4 / 29.76 | 25.2 / 192.08 |
| zarr/py | 256 | 1.1 / 0.10 | 8.5 / 1.04 | 80.9 / 9.45 | 1089.0 / 131.22 |
| zarr/py | 512 | 1.2 / 0.24 | 3.6 / 1.62 | 25.0 / 11.42 | 289.0 / 135.69 |
| zarr/py | 1024 | 1.6 / 1.69 | 1.2 / 2.25 | 8.9 / 15.91 | 81.0 / 148.61 |
| zarr/py | 2048 | 1.9 / 7.75 | 1.2 / 9.18 | 2.9 / 20.23 | 24.9 / 179.95 |
| zarr/gdal | 256 | 1.4 / 0.12 | 1.9 / 0.24 | 5.2 / 0.63 | 57.2 / 6.87 |
| zarr/gdal | 512 | 1.2 / 0.46 | 1.5 / 0.74 | 3.5 / 1.63 | 25.2 / 11.45 |
| zarr/gdal | 1024 | 1.1 / 1.63 | 2.0 / 3.67 | 4.0 / 7.17 | 23.5 / 43.35 |
| zarr/gdal | 2048 | 1.1 / 7.27 | 1.2 / 9.18 | 4.0 / 28.05 | 23.9 / 172.97 |

### http_lat40: speedup 256 -> 2048 chunk, and Zarr/COG ratio at 2048

- window 64: cog/gdal: x0.03; zarr/py: x0.05; zarr/gdal: x0.05; zarr-py/cog @2048 = 0.12; zarr-gdal/cog @2048 = 0.17
- window 512: cog/gdal: x0.27; zarr/py: x8.95; zarr/gdal: x0.39; zarr-py/cog @2048 = 0.11; zarr-gdal/cog @2048 = 0.13
- window 2048: cog/gdal: x0.29; zarr/py: x39.36; zarr/gdal: x1.21; zarr-py/cog @2048 = 0.07; zarr-gdal/cog @2048 = 0.12
- window 8192: cog/gdal: x0.92; zarr/py: x47.05; zarr/gdal: x2.37; zarr-py/cog @2048 = 0.12; zarr-gdal/cog @2048 = 0.12

## Sharded Zarr v3 (local, zarr-python): 2048 shards x 256 inner chunks vs plain 256 / 2048

| variant | 64 px ms | 512 px ms | 2048 px ms | 8192 px ms |
|---|---:|---:|---:|---:|
| zarr_256 | 1.1 | 3.8 | 33.2 | 443.7 |
| zarrsh_2048_256 | 1.7 | 4.1 | 32.0 | 412.0 |
| zarr_2048 | 27.2 | 28.3 | 55.9 | 264.5 |

## Sharded Zarr v3 (http, zarr-python): 2048 shards x 256 inner chunks vs plain 256 / 2048

| variant | 64 px ms | 512 px ms | 2048 px ms | 8192 px ms | reqs / MB @64 / 512 / 2048 / 8192 |
|---|---:|---:|---:|---:|---|
| zarr_256 | 1.7 | 6.1 | 47.0 | 734.5 | 2r 0.1MB / 9r 1.1MB / 81r 9.4MB / 1089r 131.2MB |
| zarrsh_2048_256 | 2.9 | 6.6 | 48.1 | 594.6 | 2r 0.1MB / 3r 1.6MB / 9r 12.7MB / 47r 142.4MB |
| zarr_2048 | 42.1 | 41.5 | 71.3 | 424.8 | 1r 6.7MB / 1r 9.2MB / 4r 28.0MB / 25r 180.8MB |

## Caveats

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
