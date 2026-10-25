# CropClock — Round 1 Deck Content (11 slides)

Maps to the YouNoodle brief: problem statement · proposed solution · alignment to challenge ·
key features / user journey · technical approach · innovation · expected impact ·
implementation roadmap · team introduction.

---

## 1 — Title
**CropClock**
Scheduling India's farm power to the crop, not the calendar.
Yuva Yodha Energy Tech Hackathon 2026 · Challenge 01: Sustainable Agriculture

## 2 — The problem
- **21.2 million** electrified agricultural pumpsets (CEA, 2019)
- **~1/5** of India's total electricity consumption
- Each feeder's 8-hour window is fixed by a **rota decided months in advance**
- Blind to: rainfall · crop growth stage · the feeder's own solar generation
- Result: power arrives the morning after 40mm of rain; pumps run at 06:00 while the
  feeder's solar plant peaks at noon

## 3 — The insight everyone else misses
Farmers over-irrigate because supply is **unpredictable**, not because they are uninformed.
If you cannot forecast when power returns, flooding the field while you have it is rational.

> **Reliability is itself a water-saving technology.**

Every existing product targets the farmer's *knowledge*. None targets the *uncertainty*.
Telangana's 24×7 free supply proves behaviour does change — at a fiscal cost its DISCOMs
cannot carry. We deliver the predictability without the kWh.

## 4 — The gap
Two mature fields. Never connected.

| Satellite crop water stress | Agricultural feeder scheduling |
|---|---|
| SEBAL, SSEBop, METRIC | Jyotigram (2003) → 6+ states |
| Fasal, Fyllo, Farmonaut | MSEDCL 8h daytime rota |
| Advises the **farmer** | Optimises **fairness and load** |
| Assumes power is available | Has never looked at a crop |

**CropClock is the missing link.**

## 5 — What CropClock does
1. **Water-deficit engine** — Sentinel-2 + Landsat → evapotranspiration → deficit per feeder command area
2. **Rain-skip** — IMD/Open-Meteo forecast cancels or shrinks the window before rain
3. **Feeder scheduler** — assigns windows under fairness + transformer capacity, maximising deficit served and solar coincidence
4. **Trust layer** — Marathi SMS/IVR, published 48h ahead

*"Feeder 47: power tomorrow 10:00–18:00. Rain Thursday — do not irrigate Wednesday."*

Every feeder still receives its **full statutory hours**. The saving is timing, not rationing.

## 6 — Technical approach
- **Actual ET** — surface energy balance (SSEBop-style) on Sentinel-2 (10m, 5-day) + Landsat thermal
- **Crop demand** — FAO-56 reference ET × crop coefficient, ICAR crop calendars
- **Deficit** — demand − (actual ET + effective rainfall), running soil-water balance per command area
- **Scheduler** — fairness-constrained assignment; greedy heuristic first, MILP if time allows
- **Validation** — CGWB observation-well levels as an independent check on seasonal draft

## 7 — The numbers, reported honestly
**Tier A — hard.** Rain-skip + solar alignment. Derived from rainfall and irradiance records.
Zero behavioural assumptions.
**Tier B — soft.** Reduced defensive pumping. Literature-calibrated, reported as a sensitivity range.

Case study: one **MSKVY-solarised feeder cluster**, full rabi season.
Metrics: kWh/feeder/season · mm/ha irrigation water · % pump-hours coincident with feeder
solar · ₹ subsidy avoided.

*Most entries will show one confident number. We show two honest ones.*

## 8 — Why it scales
- **100% public data** — Sentinel-2, Landsat, IMD, CGWB, MERC, Grid-India
- **Zero new hardware.** No sensors, no field deployment, no proprietary data
- **Rides infrastructure India has already funded** — MSKVY 2.0 (16,000 MW target, GR 13.09.2024;
  2,269 MW tariff-approved Aug 2026), PM-KUSUM Component C, RDSS
- A software layer, not a capex ask

## 9 — Who benefits
- **Farmer** — predictable, adequate irrigation; less wasted diesel and effort
- **DISCOM** — fewer subsidised units, higher solar self-consumption on MSKVY feeders
- **State exchequer** — lower agricultural power subsidy
- **Aquifer** — reduced groundwater draft in stressed districts

## 10 — Roadmap
- **Round 2 (11 Oct – 22 Nov 2026)** — one Maharashtra district, one rabi season: ET pipeline,
  rain-skip, scheduler, backtest vs baseline, dashboard
- **Dec 2026** — top-team review
- **2027** — district pilot with a DISCOM under MSKVY
- **Then** — replicate to Gujarat, Karnataka, Madhya Pradesh, Rajasthan, Punjab

## 11 — Team, and what we are not claiming
**Limitations we are putting on the slide rather than hiding:**
- Feeder → command-area mapping is not public. We approximate geographically; DISCOMs hold it internally.
- ET is noisy on sub-hectare plots. We aggregate to feeder, where the errors cancel. We do not claim plot-level accuracy.
- The behavioural saving is modelled, not measured. That is exactly why we report Tier A and Tier B separately.

**Team:** *(confirm names + roles)*
