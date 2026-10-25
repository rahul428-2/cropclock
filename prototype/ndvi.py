#!/usr/bin/env python3
"""
CropClock — satellite crop-stage layer.

Pulls every usable Sentinel-2 L2A pass over the feeder command areas for the
rabi season, masks cloud with the scene classification layer, and writes the
mean NDVI of each feeder for each date. NDVI becomes a crop coefficient in
cropclock.py, so crop water demand is observed rather than taken from a
textbook stage calendar.

Data: Element84 Earth Search (Sentinel-2 COGs on AWS). Free, no account.
Out:  out/ndvi.json, out/ndvi/<date>.png (map overlays for the dashboard)
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pystac_client import Client
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

SEASON = "2025-10-01/2026-03-20"
TILE = "MGRS-43QEV"
MAX_CLOUD = 30

# 8 feeders, 4 x 2 grid of 500 ha squares, farmland west of Solapur city.
CELL_KM = 500 ** 0.5 / 10                 # 2.236 km
LON0, LAT0 = 75.640, 17.645
DLON = CELL_KM / (111.32 * np.cos(np.radians(LAT0 + 0.02)))
DLAT = CELL_KM / 110.57
COLS, ROWS = 4, 2
BBOX = [LON0, LAT0, LON0 + COLS * DLON, LAT0 + ROWS * DLAT]

# SCL classes that are not ground: no-data, saturated, shadow, cloud, cirrus.
BAD_SCL = {0, 1, 3, 8, 9, 10}
MIN_VALID = 0.6
# Rabi gets ~100 mm of rain against ~840 mm of ET0: a pixel still green in the
# dry season is being irrigated. Its NDVI sets the crop coefficient.
CROP_NDVI = 0.4


def feeders():
    out = []
    for r in range(ROWS):
        for c in range(COLS):
            w, s = LON0 + c * DLON, LAT0 + (ROWS - 1 - r) * DLAT
            out.append({"id": f"F{r * COLS + c + 1}", "bounds": [w, s, w + DLON, s + DLAT]})
    return out


def read(item, asset):
    with rasterio.open(item.assets[asset].href) as src:
        b = transform_bounds("EPSG:4326", src.crs, *BBOX)
        win = from_bounds(*b, src.transform)
        if asset == "scl":                # 20 m band, resample to the 10 m grid
            h, w = round(win.height * 2), round(win.width * 2)
            return src.read(1, window=win, out_shape=(h, w), resampling=Resampling.nearest)
        return src.read(1, window=win).astype("float32")


def scene(item):
    red, nir, scl = read(item, "red"), read(item, "nir"), read(item, "scl")
    h, w = min(red.shape[0], scl.shape[0]), min(red.shape[1], scl.shape[1])
    red, nir, scl = red[:h, :w], nir[:h, :w], scl[:h, :w]
    ndvi = (nir - red) / (nir + red + 1e-6)
    ndvi[np.isin(scl, list(BAD_SCL))] = np.nan
    return item.datetime.date().isoformat(), ndvi


def main():
    os.makedirs(os.path.join(OUT, "ndvi"), exist_ok=True)
    items = Client.open("https://earth-search.aws.element84.com/v1").search(
        collections=["sentinel-2-l2a"], bbox=BBOX, datetime=SEASON,
        query={"eo:cloud_cover": {"lt": MAX_CLOUD}}).items()
    by_date = {}
    for it in items:                      # one item per date on our tile
        if it.properties.get("grid:code") == TILE:
            by_date.setdefault(it.datetime.date(), it)
    print(f"{len(by_date)} scenes")

    # ponytail: 4 threads keeps the laptop cool; I/O bound so more barely helps
    with ThreadPoolExecutor(4) as ex:
        scenes = sorted(ex.map(scene, by_date.values()), key=lambda s: s[0])

    fs = feeders()
    dates = []
    series = {k: {f["id"]: [] for f in fs} for k in ("ndvi", "crop_frac", "crop_ndvi")}
    for d, ndvi in scenes:
        h, w = ndvi.shape
        vals = {}
        for i, f in enumerate(fs):
            r, c = divmod(i, COLS)
            block = ndvi[r * h // ROWS:(r + 1) * h // ROWS, c * w // COLS:(c + 1) * w // COLS]
            valid = np.isfinite(block).mean()
            if valid < MIN_VALID:
                vals[f["id"]] = None
                continue
            crop = block[block > CROP_NDVI]
            vals[f["id"]] = (float(np.nanmean(block)), crop.size / np.isfinite(block).sum(),
                             float(crop.mean()) if crop.size else 0.0)
        if all(v is None for v in vals.values()):
            continue
        dates.append(d)
        for fid, v in vals.items():
            for j, k in enumerate(("ndvi", "crop_frac", "crop_ndvi")):
                series[k][fid].append(None if v is None else round(v[j], 4))
        plt.imsave(os.path.join(OUT, "ndvi", f"{d}.png"),
                   np.nan_to_num(ndvi, nan=0), cmap="RdYlGn", vmin=0, vmax=0.8)

    json.dump({"bbox": BBOX, "feeders": fs, "dates": dates, **series,
               "crop_ndvi_threshold": CROP_NDVI,
               "source": f"Sentinel-2 L2A {TILE}, Element84 Earth Search, cloud<{MAX_CLOUD}%"},
              open(os.path.join(OUT, "ndvi.json"), "w"), indent=1)
    print(f"{len(dates)} usable dates -> out/ndvi.json")


if __name__ == "__main__":
    main()
