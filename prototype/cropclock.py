#!/usr/bin/env python3
"""
CropClock — feeder scheduler and season backtest.

Eight agricultural feeders on one substation, each with a 1 MW MSKVY solar
plant, run through rabi 2025-26 day by day under three strategies:

  rota       MSEDCL practice: 8 h a day, feeders 1-4 on 08-16 and 5-8 on 22-06,
             swapping every week.
  scheduler  CropClock without rain-skip: same 8 h/day guarantee and the same
             4-feeder substation cap, but hours go to the feeders whose fields
             need water, in the sunniest forecast hours first.
  cropclock  scheduler + rain-skip on the day-ahead forecast.

Crop water demand per feeder comes from Sentinel-2 (ndvi.py), not a stage
calendar. Rain-skip is scored on archived 1- and 2-day-ahead forecasts against
what actually fell, so a false alarm costs the crop a day of waiting.

Data: out/ndvi.json, Open-Meteo archive (ERA5) + previous-runs forecast API.
Out:  out/sim.json (rabi on Sentinel-2 Kc; kharif on FAO-56 stages, monsoon cloud)
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "analysis"))
from backtest import (AREA_HA, CALENDAR_INTERVAL_DAYS, CALENDAR_NET_MM,  # noqa: E402
                      COINCIDENT_LOAD_KW, COST_OF_SUPPLY_PER_KWH, EFFECTIVE_RAIN_FRAC, FEEDER_SOLAR_MW, IRRIG_EFFICIENCY,
                      KWH_PER_M3, PERFORMANCE_RATIO, RAIN_SKIP_MM, RAW_MM, SEASONS, TAW_MM, kc_for)

HOURS_PER_DAY = 8          # MERC guarantee to agricultural feeders
MAX_ON = 4                 # substation transformer: 4 feeders at full load
STRESS_OVERRIDE = 0.75     # never defer for rain past 75% of TAW
SUN_HOURS = range(7, 18)   # CropClock prefers these; uses night only if it must

# 1 mm over the command area, gross, in kWh at the pump.
KWH_PER_MM = 10.0 * KWH_PER_M3 * AREA_HA
FEEDER_KWH_PER_H = COINCIDENT_LOAD_KW


def kc(ndvi):
    """Linear NDVI->Kc (Kamble, Kilic & Hubbard 2013). Linear, so Kc of the
    feeder's mean NDVI is the area average of per-pixel Kc."""
    return float(np.clip(1.457 * ndvi - 0.1725, 0.15, 1.15))


def get(url, **q):
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(q), timeout=120) as r:
        return json.load(r)


def weather(lat, lon, start, end):
    loc = dict(latitude=lat, longitude=lon, start_date=start, end_date=end,
               timezone="Asia/Kolkata")
    obs = get("https://archive-api.open-meteo.com/v1/archive", **loc,
              daily="precipitation_sum,et0_fao_evapotranspiration",
              hourly="shortwave_radiation")
    fc = get("https://previous-runs-api.open-meteo.com/v1/forecast", **loc,
             hourly="precipitation_previous_day1,precipitation_previous_day2,"
                    "shortwave_radiation_previous_day1")
    n = len(obs["daily"]["time"])
    day = lambda xs: np.nan_to_num(np.array(xs[:n * 24], float)).reshape(n, 24)
    h = fc["hourly"]
    return {
        "days": [date.fromisoformat(t) for t in obs["daily"]["time"]],
        "rain": np.nan_to_num(np.array(obs["daily"]["precipitation_sum"], float)),
        "et0": np.nan_to_num(np.array(obs["daily"]["et0_fao_evapotranspiration"], float)),
        "rad": day(obs["hourly"]["shortwave_radiation"]),           # what happened
        "rad_fc": day(h["shortwave_radiation_previous_day1"]),      # what was forecast
        "rain_fc1": day(h["precipitation_previous_day1"]).sum(1),   # issued the day before
        "rain_fc2": day(h["precipitation_previous_day2"]).sum(1),   # issued two days before
    }


def rota_hours(fi, day_i):
    day_group = (fi < 4) == ((day_i // 7) % 2 == 0)
    return list(range(8, 16)) if day_group else [22, 23, 0, 1, 2, 3, 4, 5]


def plan_day(need_kwh, rad_fc, priority):
    """
    Greedy: walk the day's hours sunniest-first and give each to up to MAX_ON
    feeders, most water-stressed first, until each feeder's need or its 8 h is
    met. Night hours are only reached when daylight is full.
    """
    # overflow goes to the hours nearest daylight, not to midnight
    dark = lambda h: min((h - SUN_HOURS.stop) % 24, (SUN_HOURS.start - 1 - h) % 24)
    hours = sorted(SUN_HOURS, key=lambda h: -rad_fc[h]) + \
        sorted((h for h in range(24) if h not in SUN_HOURS), key=dark)
    left = [min(np.ceil(k / FEEDER_KWH_PER_H), HOURS_PER_DAY) for k in need_kwh]
    on = [[] for _ in need_kwh]
    order = sorted(range(len(need_kwh)), key=lambda f: -priority[f])
    for h in hours:
        slots = MAX_ON
        for f in order:
            if slots and left[f] > 0:
                on[f].append(h)
                left[f] -= 1
                slots -= 1
    return on


def simulate(strategy, w, kc_daily, farmer="et"):
    """
    farmer="et":        irrigates when depletion reaches RAW, refills to field
                        capacity (Tier A: no behaviour assumed).
    farmer="defensive": waters every 12 days with a fixed 60 mm because supply
                        can't be predicted (Tier B, same as analysis/backtest.py).
    """
    nf, nd = kc_daily.shape
    D = np.full(nf, RAW_MM * 0.25)          # soil just after the monsoon
    owed = np.zeros(nf)                     # net mm still to deliver this round
    # farmers sowed on different days: stagger their cycles across the feeders
    since = CALENDAR_INTERVAL_DAYS - np.arange(nf) * CALENDAR_INTERVAL_DAYS // nf
    log = {k: np.zeros((nd, nf)) for k in ("depletion", "kwh")}
    sched = np.zeros((nd, 24), int)         # bitmask of energised feeders per hour
    load = np.zeros((nd, 24))
    perc = stress = 0.0
    deferrals = []

    for i, d in enumerate(w["days"]):
        D += kc_daily[:, i] * w["et0"][i] - w["rain"][i] * EFFECTIVE_RAIN_FRAC
        perc += -D[D < 0].sum()
        D = np.maximum(D, 0)
        since += 1

        for f in range(nf):
            due = (since[f] >= CALENDAR_INTERVAL_DAYS and kc_daily[f, i] > 0
                   if farmer == "defensive" else D[f] >= RAW_MM)
            if owed[f] > 0 or not due:
                continue
            ahead = w["rain_fc1"][i + 1] + w["rain_fc2"][i + 2] if i + 2 < nd else 0
            if (strategy == "cropclock" and ahead >= RAIN_SKIP_MM
                    and D[f] < STRESS_OVERRIDE * TAW_MM):
                came = w["rain"][i + 1:i + 3].sum()
                deferrals.append({"date": d.isoformat(), "feeder": f"F{f + 1}",
                                  "forecast_mm": round(float(ahead), 1),
                                  "observed_mm": round(float(came), 1),
                                  "hit": bool(came >= RAIN_SKIP_MM / 2)})
                continue
            owed[f] = CALENDAR_NET_MM if farmer == "defensive" else D[f]
            since[f] = 0
        if farmer == "et":                  # top up to field capacity, not to a stale target
            owed = np.where(owed > 0, D, 0.0)

        need = owed / IRRIG_EFFICIENCY * KWH_PER_MM
        if strategy == "rota":
            on = [rota_hours(f, i) if need[f] > 0 else [] for f in range(nf)]
        else:
            on = plan_day(need, w["rad_fc"][i], D / RAW_MM)

        for f, hrs in enumerate(on):
            kwh = rem = min(need[f], len(hrs) * FEEDER_KWH_PER_H)
            for h in hrs:                   # full load until the need is met
                sched[i, h] |= 1 << f
                take = min(FEEDER_KWH_PER_H, rem)
                load[i, h] += take
                rem -= take
            net = kwh / KWH_PER_MM * IRRIG_EFFICIENCY
            owed[f] = 0.0 if owed[f] - net <= 1e-6 else owed[f] - net
            D[f] -= net
            if D[f] < 0:                    # over-application drains away
                perc += -D[f]
                D[f] = 0.0
            log["kwh"][i, f] = kwh
        stress += (D > RAW_MM).sum()
        log["depletion"][i] = D

    gen = FEEDER_SOLAR_MW * 1000 * nf * w["rad"] / 1000 * PERFORMANCE_RATIO
    solar = np.minimum(load, gen).sum()
    total = load.sum()
    night = load[:, [h for h in range(24) if h < 6 or h >= 19]].sum()
    return {
        "summary": {
            "pump_mwh": round(float(total) / 1000, 1),
            "solar_share_pct": round(float(100 * solar / total), 1),
            "grid_mwh": round(float(total - solar) / 1000, 1),
            "night_share_pct": round(float(100 * night / total), 1),
            "peak_substation_mw": round(float(load.max()) / 1000, 2),
            "stress_feeder_days": int(stress),
            "deep_percolation_mm": round(float(perc) / nf, 1),
            "deferrals": len(deferrals),
            "deferral_hits": sum(x["hit"] for x in deferrals),
        },
        "deferrals": deferrals,
        "schedule": sched.tolist(),
        "load_kw": load.round().astype(int).tolist(),
        "depletion_frac": (log["depletion"] / RAW_MM).round(3).tolist(),
    }


def kc_from_ndvi(nd, days):
    """NDVI only exists on clear days: interpolate each feeder to daily."""
    t = np.array([(date.fromisoformat(x) - days[0]).days for x in nd["dates"]])
    out = []
    for f in nd["feeders"]:
        s = np.array([np.nan if v is None else v for v in nd["ndvi"][f["id"]]], float)
        ok = np.isfinite(s)
        out.append([kc(v) for v in np.interp(np.arange(len(days)), t[ok], s[ok])])
    return np.array(out)


def kc_from_calendar(cfg, days, nf):
    """Monsoon cloud leaves ~3 clear Sentinel-2 passes: fall back to FAO-56 stages."""
    row = [kc_for((d - cfg["sowing"]).days, cfg["stages"], cfg["kc"]) for d in days]
    return np.tile(row, (nf, 1))


def run_season(name, nd, start, end, kc_source, farmer):
    b = nd["bbox"]
    w = weather((b[1] + b[3]) / 2, (b[0] + b[2]) / 2, start, end)
    nf = len(nd["feeders"])
    kc_daily = (kc_from_ndvi(nd, w["days"]) if kc_source == "ndvi"
                else kc_from_calendar(SEASONS[name], w["days"], nf))
    runs = {s: simulate(s, w, kc_daily, farmer) for s in ("rota", "scheduler", "cropclock")}
    r, c = runs["rota"]["summary"], runs["cropclock"]["summary"]
    saved = r["grid_mwh"] - c["grid_mwh"]
    print(name)
    for s, v in runs.items():
        print(f"  {s:10s}", json.dumps(v["summary"]))
    dfr = runs["cropclock"]["deferrals"]
    if dfr:
        print(f"   rain-skip: {len(dfr)} deferrals {dfr[0]['date']}..{dfr[-1]['date']}, "
              f"{sum(x['hit'] for x in dfr)} followed by rain")
    return {
        "kc_source": kc_source,
        "farmer": farmer,
        "days": [d.isoformat() for d in w["days"]],
        "rain_mm": w["rain"].round(1).tolist(),
        "rain_fc_mm": (w["rain_fc1"]).round(1).tolist(),
        "et0_mm": w["et0"].round(2).tolist(),
        "kc": kc_daily.round(3).tolist(),
        "solar_kw": (FEEDER_SOLAR_MW * 1000 * nf * w["rad"] / 1000
                     * PERFORMANCE_RATIO).round().astype(int).tolist(),
        "headline": {
            "grid_mwh_saved": round(saved, 1),
            "grid_pct_saved": round(100 * saved / r["grid_mwh"], 1),
            "subsidy_saved_lakh_rs": round(saved * 1000 * COST_OF_SUPPLY_PER_KWH / 1e5, 2),
        },
        **runs,
    }


def main():
    nd = json.load(open(os.path.join(HERE, "out", "ndvi.json")))
    out = {
        "feeders": [f["id"] for f in nd["feeders"]],
        "feeder_bounds": [f["bounds"] for f in nd["feeders"]],
        "bbox": nd["bbox"],
        "params": {"hours_per_day": HOURS_PER_DAY, "max_on": MAX_ON,
                   "feeder_kw": round(FEEDER_KWH_PER_H), "solar_mw_per_feeder": FEEDER_SOLAR_MW,
                   "raw_mm": RAW_MM, "rain_skip_mm": RAIN_SKIP_MM,
                   "cost_of_supply_rs_kwh": COST_OF_SUPPLY_PER_KWH},
        "rabi": run_season("rabi", nd, nd["dates"][0], nd["dates"][-1], "ndvi", "et"),
        "kharif": run_season("kharif", nd, "2025-06-20", "2025-10-11", "calendar", "defensive"),
    }
    json.dump(out, open(os.path.join(HERE, "out", "sim.json"), "w"))


if __name__ == "__main__":
    main()
