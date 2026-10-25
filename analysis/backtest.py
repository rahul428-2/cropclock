#!/usr/bin/env python3
"""
CropClock — Tier A backtest.

Compares a fixed-rota agricultural feeder schedule against a CropClock schedule
over real seasons, using only observed weather. No behavioural assumption enters
this file; every saving follows from rainfall, reference ET and irradiance.

  A-1  Rain-skip.  Two identical FAO-56 soil-water balances. The baseline
       irrigates on depletion alone. CropClock defers when meaningful rain is
       expected within 48 h, discounted for real forecast skill.

  A-2  Solar coincidence.  A feeder pumps more or less continuously through its
       supply window whenever the command area is under irrigation. Baseline
       window is the rota's 06:00-14:00; CropClock's is 08:00-18:00. Measured
       hourly irradiance gives the feeder's own solar output, and hour-by-hour
       min(load, generation) gives the share of pump energy that never has to be
       bought from the grid.

Both kharif and rabi are run, because the two levers do not have the same value
in the two seasons — which is itself a finding.

Data: Open-Meteo historical archive (ERA5-Land). Free, no API key.
"""

import json
import urllib.parse
import urllib.request
from datetime import date, datetime

# --------------------------------------------------------------------------
# Site and feeder
# --------------------------------------------------------------------------

SITE_NAME = "Solapur district, Maharashtra"
LAT, LON = 17.66, 75.90

# Pumpset: 7.5 HP submersible on a ~50 m borewell, at the wire-to-water
# efficiency typical of unregulated Indian agricultural pumps.
PUMP_KW = 5.60
HEAD_M = 50.0
PUMP_EFF = 0.40

PUMPS_PER_FEEDER = 250
HA_PER_PUMP = 2.0
DIVERSITY = 0.70            # share of connected pumps drawing at any moment
FEEDER_SOLAR_MW = 1.0       # MSKVY plant on the feeder
PERFORMANCE_RATIO = 0.80

# Soil: medium-deep Vertisol (black cotton), Solapur plateau.
TAW_MM = 160.0
DEPLETION_FRAC = 0.50
RAW_MM = TAW_MM * DEPLETION_FRAC

IRRIG_EFFICIENCY = 0.60
EFFECTIVE_RAIN_FRAC = 0.80

BASELINE_WINDOW = (6, 14)
CROPCLOCK_WINDOW = (8, 18)
RAIN_SKIP_MM = 15.0
FORECAST_SKILL = 0.75
COST_OF_SUPPLY_PER_KWH = 7.50

AREA_HA = PUMPS_PER_FEEDER * HA_PER_PUMP
COINCIDENT_LOAD_KW = PUMPS_PER_FEEDER * PUMP_KW * DIVERSITY

# Discharge and specific energy follow from head and efficiency.
Q_M3_PER_H = PUMP_EFF * (PUMP_KW * 1000.0) / (1000.0 * 9.81 * HEAD_M) * 3600.0
KWH_PER_M3 = PUMP_KW / Q_M3_PER_H

SEASONS = {
    "kharif": {
        "fetch": ("2025-06-01", "2025-11-05"),
        "sowing": date(2025, 6, 20),
        "crop": "Soybean",
        "stages": {"ini": 20, "dev": 30, "mid": 60, "late": 25},
        "kc": {"ini": 0.40, "mid": 1.15, "end": 0.50},
    },
    "rabi": {
        "fetch": ("2025-10-01", "2026-03-20"),
        "sowing": date(2025, 10, 15),
        "crop": "Rabi sorghum (jowar)",
        "stages": {"ini": 20, "dev": 35, "mid": 40, "late": 30},
        "kc": {"ini": 0.30, "mid": 1.05, "end": 0.55},
    },
}


def fetch_weather(start, end):
    base = "https://archive-api.open-meteo.com/v1/archive"
    q = {
        "latitude": LAT, "longitude": LON,
        "start_date": start, "end_date": end,
        "daily": "precipitation_sum,et0_fao_evapotranspiration",
        "hourly": "shortwave_radiation",
        "timezone": "Asia/Kolkata",
    }
    with urllib.request.urlopen(base + "?" + urllib.parse.urlencode(q), timeout=90) as r:
        return json.load(r)


def kc_for(day_index, stages, kc):
    ini, dev, mid, late = stages["ini"], stages["dev"], stages["mid"], stages["late"]
    if day_index < 0:
        return 0.0
    if day_index < ini:
        return kc["ini"]
    if day_index < ini + dev:
        return kc["ini"] + (day_index - ini) / dev * (kc["mid"] - kc["ini"])
    if day_index < ini + dev + mid:
        return kc["mid"]
    if day_index < ini + dev + mid + late:
        f = (day_index - ini - dev - mid) / late
        return kc["mid"] + f * (kc["end"] - kc["mid"])
    return 0.0


def run_balance(days, rain, et0, cfg, use_forecast):
    """Daily root-zone balance. Returns (events, percolation_mm)."""
    depletion = RAW_MM * 0.5
    events, percolation = [], 0.0
    for i, d in enumerate(days):
        di = (d - cfg["sowing"]).days
        k = kc_for(di, cfg["stages"], cfg["kc"])
        depletion += k * et0[i] - rain[i] * EFFECTIVE_RAIN_FRAC
        if depletion < 0:
            percolation += -depletion
            depletion = 0.0
        if depletion >= RAW_MM and k > 0:
            if use_forecast:
                ahead = sum(rain[i + 1:i + 3]) * EFFECTIVE_RAIN_FRAC
                if ahead >= RAIN_SKIP_MM * EFFECTIVE_RAIN_FRAC:
                    continue        # rain is coming — defer
            events.append((d, depletion, depletion / IRRIG_EFFICIENCY))
            depletion = 0.0
    return events, percolation


CALENDAR_INTERVAL_DAYS = 12
CALENDAR_NET_MM = 60.0


def run_calendar(days, rain, et0, cfg, use_forecast):
    """
    Defensive irrigation: the farmer waters on a fixed cycle and applies a fixed
    depth, because the supply window is unpredictable and a missed turn cannot
    be recovered. Anything above field capacity drains away.

    This is the Tier B baseline. It is how irrigation actually happens; the
    ET-optimal balance above is how it would happen with perfect information.
    """
    depletion = RAW_MM * 0.5
    events, percolation, since = [], 0.0, CALENDAR_INTERVAL_DAYS
    for i, d in enumerate(days):
        di = (d - cfg["sowing"]).days
        k = kc_for(di, cfg["stages"], cfg["kc"])
        depletion += k * et0[i] - rain[i] * EFFECTIVE_RAIN_FRAC
        if depletion < 0:
            percolation += -depletion
            depletion = 0.0
        since += 1
        if k > 0 and since >= CALENDAR_INTERVAL_DAYS:
            if use_forecast:
                ahead = sum(rain[i + 1:i + 3]) * EFFECTIVE_RAIN_FRAC
                if ahead >= RAIN_SKIP_MM * EFFECTIVE_RAIN_FRAC:
                    continue        # deferred; cycle resumes next check
            applied = CALENDAR_NET_MM
            if applied > depletion:
                percolation += applied - depletion   # over-application drains
            events.append((d, applied, applied / IRRIG_EFFICIENCY))
            depletion = max(0.0, depletion - applied)
            since = 0
    return events, percolation


def pump_days(events):
    """
    Turn irrigation events into the days the feeder is actually pumping.

    One event waters the whole command area, but a feeder cannot do that in a
    day: at COINCIDENT_LOAD_KW the area is covered over an irrigation round of
    several days. Returns {date: kWh drawn that day}.
    """
    load = {}
    window_h = BASELINE_WINDOW[1] - BASELINE_WINDOW[0]
    daily_capacity_kwh = COINCIDENT_LOAD_KW * window_h
    for d, _net, gross in events:
        total_kwh = gross * 10.0 * KWH_PER_M3 * AREA_HA   # 1 mm/ha = 10 m3
        remaining, offset = total_kwh, 0
        while remaining > 0 and offset < 30:
            day = date.fromordinal(d.toordinal() + offset)
            take = min(remaining, daily_capacity_kwh)
            load[day] = load.get(day, 0.0) + take
            remaining -= take
            offset += 1
    return load


def solar_share(load_by_day, hourly_time, hourly_rad, window):
    """Hour-by-hour min(load, feeder solar generation) across the season."""
    start_h, end_h = window
    hours = end_h - start_h
    rad = {}
    for t, g in zip(hourly_time, hourly_rad):
        if g is None:
            continue
        dt = datetime.fromisoformat(t)
        rad.setdefault(dt.date(), {})[dt.hour] = g

    served = total = 0.0
    for day, kwh in load_by_day.items():
        # A day's energy is drawn across the window, capped by coincident load.
        per_hour = min(kwh / hours, COINCIDENT_LOAD_KW)
        day_rad = rad.get(day, {})
        for h in range(start_h, end_h):
            gen_kw = FEEDER_SOLAR_MW * 1000.0 * (day_rad.get(h, 0.0) / 1000.0) * PERFORMANCE_RATIO
            served += min(per_hour, gen_kw)
            total += per_hour
    return served, total


def run_season(name, cfg):
    data = fetch_weather(*cfg["fetch"])
    days = [date.fromisoformat(s) for s in data["daily"]["time"]]
    rain = [x or 0.0 for x in data["daily"]["precipitation_sum"]]
    et0 = [x or 0.0 for x in data["daily"]["et0_fao_evapotranspiration"]]

    base_ev, base_perc = run_balance(days, rain, et0, cfg, False)
    cc_ev, _ = run_balance(days, rain, et0, cfg, True)

    base_gross = sum(e[2] for e in base_ev)
    cc_gross = sum(e[2] for e in cc_ev)
    mm_saved = (base_gross - cc_gross) * FORECAST_SKILL

    kwh_per_ha = lambda mm: mm * 10.0 * KWH_PER_M3
    base_kwh_ha = kwh_per_ha(base_gross)
    saved_kwh_feeder = kwh_per_ha(mm_saved) * AREA_HA

    load = pump_days(base_ev)
    b_served, b_total = solar_share(load, data["hourly"]["time"],
                                    data["hourly"]["shortwave_radiation"], BASELINE_WINDOW)
    c_served, c_total = solar_share(load, data["hourly"]["time"],
                                    data["hourly"]["shortwave_radiation"], CROPCLOCK_WINDOW)
    b_share = b_served / b_total if b_total else 0.0
    c_share = c_served / c_total if c_total else 0.0
    displaced = (c_share - b_share) * b_total

    # Tier B: the same rain-skip, but against how irrigation actually happens.
    cal_ev, cal_perc = run_calendar(days, rain, et0, cfg, False)
    cal_cc_ev, cal_cc_perc = run_calendar(days, rain, et0, cfg, True)
    cal_gross = sum(e[2] for e in cal_ev)
    cal_cc_gross = sum(e[2] for e in cal_cc_ev)
    cal_mm_saved = (cal_gross - cal_cc_gross) * FORECAST_SKILL
    cal_kwh_saved = kwh_per_ha(cal_mm_saved) * AREA_HA

    combined = saved_kwh_feeder + displaced
    return {
        "tier_B_defensive_baseline": {
            "note": "fixed 12-day cycle, fixed 60 mm net application",
            "irrigations": len(cal_ev),
            "gross_applied_mm": round(cal_gross, 1),
            "over_application_lost_mm": round(cal_perc, 1),
            "excess_over_ET_optimal_mm": round(cal_gross - base_gross, 1),
            "irrigations_deferred_by_forecast": len(cal_ev) - len(cal_cc_ev),
            "water_saved_mm_per_ha": round(cal_mm_saved, 1),
            "feeder_energy_saved_mwh": round(cal_kwh_saved / 1000.0, 1),
            "pct_of_defensive_baseline": round(100 * cal_mm_saved / cal_gross, 1)
            if cal_gross else 0.0,
        },
        "season": name,
        "crop": cfg["crop"],
        "window": f'{cfg["fetch"][0]} to {cfg["fetch"][1]}',
        "rainfall_mm": round(sum(rain), 1),
        "reference_ET_mm": round(sum(et0), 1),
        "baseline": {
            "irrigations": len(base_ev),
            "gross_applied_mm": round(base_gross, 1),
            "deep_percolation_mm": round(base_perc, 1),
            "energy_kwh_per_ha": round(base_kwh_ha),
            "feeder_energy_mwh": round(base_kwh_ha * AREA_HA / 1000.0, 1),
            "pumping_days": len(load),
        },
        "A1_rain_skip": {
            "irrigations_deferred": len(base_ev) - len(cc_ev),
            "water_saved_mm_per_ha": round(mm_saved, 1),
            "feeder_energy_saved_mwh": round(saved_kwh_feeder / 1000.0, 1),
            "pct_of_baseline": round(100 * mm_saved / base_gross, 1) if base_gross else 0.0,
        },
        "A2_solar_coincidence": {
            "baseline_solar_share_pct": round(100 * b_share, 1),
            "cropclock_solar_share_pct": round(100 * c_share, 1),
            "grid_mwh_displaced": round(displaced / 1000.0, 1),
            "pct_of_baseline": round(100 * displaced / (base_kwh_ha * AREA_HA), 1)
            if base_kwh_ha else 0.0,
        },
        "combined": {
            "grid_mwh_avoided_per_feeder": round(combined / 1000.0, 1),
            "pct_of_baseline": round(100 * combined / (base_kwh_ha * AREA_HA), 1)
            if base_kwh_ha else 0.0,
            "subsidy_avoided_lakh_rs": round(combined * COST_OF_SUPPLY_PER_KWH / 1e5, 2),
        },
    }


def main():
    out = {
        "site": SITE_NAME,
        "coords": [LAT, LON],
        "feeder": {
            "pumps": PUMPS_PER_FEEDER,
            "pump_kw": PUMP_KW,
            "head_m": HEAD_M,
            "pump_efficiency": PUMP_EFF,
            "discharge_m3_per_h": round(Q_M3_PER_H, 1),
            "specific_energy_kwh_per_m3": round(KWH_PER_M3, 3),
            "command_area_ha": AREA_HA,
            "coincident_load_kw": round(COINCIDENT_LOAD_KW),
            "solar_mw": FEEDER_SOLAR_MW,
        },
        "seasons": [run_season(n, c) for n, c in SEASONS.items()],
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
