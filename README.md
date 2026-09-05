# zarr-vs-cog

FOSS4G Hiroshima 2026 の #30「Serverless Watershed Extraction: Benchmarking Zarr vs COG」を
手元データで再現する実験。同じ GeoTIFF から COG と Zarr v3 をチャンクサイズ 4 種で生成し、
ランダムウィンドウ読み出しの速度・チャンク数・HTTP リクエスト数を比べる。

- 元データ: 林野庁 能登 2024 DEM（0.5 m, JGD2011 / 平面直角 VII, Float32）から 24000×24000 px（12 km 角）を切り出し
- 生成: OSGeo4W GDAL 3.13（Zarr ドライバ, ZARR_V3）。圧縮は両者 ZSTD level 9、COG はオーバービューなし
- 読み出し: rasterio（COG）, zarr-python 3（Zarr）, rasterio + GDAL Zarr ドライバ（Zarr を C++ で読む対照）

```
scripts/make_variants.py     変換（data/out に cog_*.tif / zarr_*.zarr）
scripts/inspect_layout.py    ディスク上の構造を見る
scripts/range_server.py      Range 対応・リクエスト記録つきの静的 HTTP サーバー
scripts/bench.py [local|http] ベンチマーク（results/bench_*.json）
```

## 結果の要点（2026-09-05, 詳細は results/REPORT.md）

- **サイズは同じ**。同一データ・同一 ZSTD(9) なら COG と Zarr の総バイト数は 1% 以内で一致する。
- **書き出しは GDAL の Zarr ドライバが極端に遅い**（256 チャンク 8,838 ファイルで 592 秒、COG は 48 秒）。
  zarr-python なら並列エンコードで 33 秒（シャーディング版）。
- **HTTP 越しのリクエスト数は「1 チャンク = 1 GET」の Zarr が COG の数倍〜十数倍**。COG は GDAL が隣接タイルの
  Range を結合するため、81 タイル読みが 9 リクエントで済む。#30 の言う「リクエスト数を数えろ」はここ。
- **Zarr v3 のシャーディング（2048 シャード × 256 チャンク）で COG と同じ挙動になる**。シャード内インデックスを
  suffix Range で 1 回引き、チャンクを Range で結合取得する。512 px 窓で 9 → 3.2 リクエスト、転送量は 2048 チャンクの 1/6。
- **zarr-python 3.3 に「GET 前の存在確認」は無い**。#30 の 251 vs 114 リクエストは当時の実装依存と見てよい。
- **リーダー実装差が支配的**。ローカルでは GDAL_NUM_THREADS=ALL_CPUS の COG が最速、zarr-python が次、
  GDAL Zarr ドライバは並列化されず 4 倍遅い。HTTP では GDAL /vsicurl の受信スループットが loopback で伸びず COG が不利に見えるが、
  これはテストサーバー環境の性質（Caveats 参照）。

## 環境

- Windows 11, OSGeo4W GDAL 3.13.3（変換）, uv venv: zarr 3.3.0 / rasterio 1.5.1 (GDAL 3.12.4) / xarray / rioxarray
- `data/` は git 管理外（約 9.3 GB）
