# CropClock — Tier A backtest results

**Run:** 2026-09-08 · `backtest.py` · raw output in `results.json`
**Site:** Solapur district, Maharashtra (17.66 N, 75.90 E)
**Weather:** Open-Meteo historical archive (ERA5-Land), observed — not modelled

**Feeder modelled:** 250 × 7.5 HP pumps (5.6 kW) on a 50 m borewell at 40%
wire-to-water efficiency → 16.4 m³/h, **0.341 kWh/m³**. 500 ha command area,
980 kW coincident load, 1 MW MSKVY solar plant.

---

## Headline

| | Rabi 2025-26 | Kharif 2025 | Year |
|---|---|---|---|
| Rainfall | 101 mm | 1,112 mm | |
| Reference ET | 839 mm | 657 mm | |
| Baseline pumping energy | 1,175 MWh | 235 MWh | 1,410 MWh |
| **Tier A — solar coincidence** | **106.7 MWh** | **21.5 MWh** | **128.2 MWh** |
| Solar share of pump energy | 35.2% → **48.6%** | 21.9% → **31.1%** | |
| **Tier A subsidy avoided** | ₹8.01 lakh | ₹1.61 lakh | **₹9.62 lakh** |

Tier A is **9.1%** of baseline pumping energy in both seasons, independently.

Scaled against the **2,269 MW of MSKVY 2.0 already tariff-approved** (MERC, Aug
2026), at 1 MW of solar per modelled feeder: **≈291 GWh/year avoided, ≈₹218
crore/year**. At the full 16,000 MW target: ≈2,051 GWh/year, ≈₹1,538 crore/year.
*(Scaling assumes one 1 MW plant per 500 ha feeder; MSKVY plants range 0.5–25 MW
and may serve several feeders, so treat the extrapolation as indicative.)*

---

## The finding that changed the pitch

**The lever is different in each season, and rain-skip is not the headline.**

- **Rabi is dry.** 101 mm of rain against 839 mm of reference ET. Under an
  ET-optimal baseline there were **zero** irrigations worth deferring for rain.
  The entire Tier A saving in rabi comes from *solar alignment*.
- **Kharif is the opposite.** 1,112 mm of rain, only one ET-optimal irrigation
  all season — but rain-skip against *realistic* irrigation behaviour saves
  **255.5 MWh**, more than the whole rabi solar saving.

This was not the assumption the deck was originally built on. The first draft
led with rain-skip as the assumption-free Tier A number; the data says that is
only true in the monsoon season.

## Tier B — what defensive irrigation actually costs

Modelled as a fixed 12-day cycle with a fixed 60 mm application, which is how
irrigation happens when the supply window cannot be predicted:

| | Rabi | Kharif |
|---|---|---|
| Defensive application | 1,100 mm | 1,200 mm |
| ET-optimal requirement | 690 mm | 138 mm |
| **Excess** | **+410 mm/ha** | **+1,062 mm/ha** |
| Lost below the root zone | 260 mm | 1,092 mm |
| Rain-skip recovers | 0 MWh | 255.5 MWh |

In kharif, defensive irrigation applies nearly **nine times** the water the crop
needs, and almost all of the excess drains past the root zone. That gap — not
the scheduling arithmetic — is the largest prize in the whole system, and it is
what the published-in-advance schedule is for.

---

## Honest limitations of this run

1. **One site, one year.** Solapur 2025-26. Not yet generalised across districts
   or across seasons of differing rainfall.
2. **No satellite input yet.** Crop water demand comes from FAO-56 stage
   coefficients, not from measured Sentinel-2 NDVI/ET. That is the Round 2 build
   and it is what makes the deficit *observed* rather than *assumed*.
3. **Feeder parameters are representative, not surveyed.** Pump count, head and
   command area are stated as assumptions; every result scales linearly with
   them except the solar share, which does not.
4. **Forecast skill discounted at 75%,** applied uniformly. Real IMD skill varies
   by lead time and by season.
5. **Tier B is a model of behaviour, not an observation of it.** The 12-day /
   60 mm cycle is plausible and literature-consistent, but it is not measured.
