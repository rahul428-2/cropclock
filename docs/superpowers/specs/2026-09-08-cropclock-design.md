# CropClock — Design Spec

**Competition:** Yuva Yodha Energy Tech Hackathon 2026 (Schneider Electric India, via YouNoodle)
**Challenge:** 01 — Sustainable Agriculture: Energy, Water & Productivity
**Date:** 2026-09-08
**Round 1 deadline:** 2026-10-04, 23:59 IST
**Status:** Design approved (project + name + challenge). Round 1 artifacts not yet built.

---

## 1. Summary

India schedules electricity to 21.2 million agricultural pumpsets using a **fixed rotational
roster** that is blind to rainfall, crop growth stage, and the feeder's own solar generation.
CropClock replaces that roster with a schedule derived from **actual crop water deficit**,
measured from free satellite imagery, and publishes it to farmers in advance.

The DISCOM delivers the same statutory hours. The crops get water when they are actually
thirsty. The kWh, the groundwater, and the subsidy all fall.

**One-line pitch:** *India's 21 million irrigation pumps are its largest flexible load, and
they are scheduled by a rota that has never once looked at a crop.*

---

## 2. Problem

### 2.1 Verified facts

| Fact | Source | Status |
|---|---|---|
| 21.2M grid-electrified irrigation pumpsets; 4.9M diesel | CEA 2019, via CEEW | verified |
| Agriculture ≈ one-fifth of India's electricity consumption | CEEW / ICED-NITI | verified |
| Feeder segregation pioneered by Gujarat Jyotigram Yojana, 2003 | ORF / state records | verified |
| Maharashtra (MSEDCL) supplies ag feeders 8 hours/day, daytime, by rota | mahadiscom.in AG policy page | verified |
| Telangana supplies agriculture 24×7 free since 1 Jan 2018 (26.96 lakh consumers) | Prayas Energy Group; TS CMO | verified |
| PM-KUSUM Component C solarises agricultural feeders | MNRE | verified |
| Industry roadmap names "digital optimization: remote switching and pump controllers" as the missing third stage after feeder segregation and fixed published hours | ORF, *Subsidising Reliability* | verified |
| Maharashtra MSKVY 2.0 target: 16,000 MW solar, per GR dated 13.09.2024 (raised from an original 7,000 MW) | MSEDCL / Maharashtra Energy Dept | verified |
| MERC approved tariffs for 2,269 MW of MSKVY 2.0 procurement, Aug 2026 | MERC Case No. 196 of 2025; SolarQuarter | verified |
| A 1 MW solar agriculture feeder plant supplies ~8–10 daytime hours, 08:00–18:00 | Prayas (Energy Group) | verified |
| MSEDCL does **not** publish per-feeder rota schedules at usable granularity | searched 2026-09-08 | verified (negative) |

### 2.2 The failure

A feeder's 8-hour window is fixed months in advance. It cannot respond to:

- **Rainfall.** A feeder scheduled to energise the morning after 40mm of rain delivers pure waste.
- **Crop stage.** Water demand varies several-fold between establishment, vegetative,
  flowering and maturity. The roster treats every week as identical.
- **The feeder's own solar.** Under PM-KUSUM C / MSKVY, a solarised feeder generates most at
  midday while its rota window may sit at 06:00.

### 2.3 The non-obvious mechanism

Farmers over-irrigate primarily because **supply is unpredictable, not because they are
uninformed.** If you cannot forecast when power returns, the rational move is to flood the
field while you have it. Every existing intervention (soil sensors, advisory apps) targets the
farmer's *knowledge*. None targets the *uncertainty* that drives the behaviour.

**Therefore: reliability is itself a water-saving technology.** This is the spine of the pitch.

Telangana is the natural experiment that proves it — and the cautionary tale. 24×7 free supply
removes the uncertainty, but at a fiscal cost that has strained its DISCOMs. CropClock delivers
the *predictability* without the *kWh*.

---

## 3. Prior art — why this is unoccupied

Searched 2026-09-08. Two mature bodies of work exist and have never been connected:

- **Crop water stress from remote sensing** — extensive academic literature (SEBAL, SSEBop,
  METRIC, CWSI); commercial products in India (Fasal, Fyllo, Farmonaut, Krishijal). All of
  these **advise the farmer and assume power is available**.
- **Agricultural feeder scheduling** — an operational reality across Gujarat, Maharashtra,
  Karnataka, MP, Rajasthan, Punjab. Set by **rota and fairness rules only**. No crop input.

No product or paper found that drives *feeder supply scheduling* from *satellite-derived crop
water deficit*. That intersection is the contribution.

**Deliberately avoided:** every item on Schneider's own "Ideas to get you started" lists, which
is what most entrants will build. Also avoided: DISCOM-facing demand-response and DERMS
analytics — Schneider acquired AutoGrid in May 2022 and has since **divested it to Uplight**.
So that pitch both sells them something they already built and points at a business they chose
to exit. CropClock is upstream of DERMS: it decides *when a feeder should be energised at all*,
which is a scheduling question, not a DER-dispatch question.

---

## 4. Architecture

Four components. Each is independently testable and independently demoable.

### 4.1 Water-deficit engine
**In:** Sentinel-2 L2A (10m, ~5-day revisit), Landsat 8/9 thermal (30/100m), ERA5 / IMD met.
**Out:** soil water deficit (mm) per pixel, aggregated to feeder command area, weekly.

Method: surface energy balance (SSEBop-style, or simplified NDVI–Kc where thermal is
unavailable) → actual ET. Crop demand = FAO-56 reference ET × crop coefficient from ICAR crop
calendars. Deficit = demand − (actual ET + effective rainfall). Running soil-moisture balance
per command area.

**Validation:** CGWB observation-well levels as an independent check on seasonal draft.

### 4.2 Rain-skip logic
**In:** IMD district QPF / Open-Meteo ensemble, 48–72h.
**Out:** cancel, shrink, or shift a scheduled window.

Deliberately dumb and deliberately auditable. This produces **hard savings with zero
behavioural assumptions**, and is the single most defensible number in the entire submission.

### 4.3 Feeder scheduler
**In:** per-feeder deficit ranking, solar generation forecast, distribution-transformer
capacity, statutory-hours entitlement per feeder.
**Out:** a weekly window assignment across all feeders on a substation.

Constraints: every feeder receives its full statutory hours over the rolling week (fairness is
non-negotiable and politically load-bearing); substation capacity not exceeded in any slot;
minimum contiguous block length.
Objective: maximise irrigation delivered against deficit, plus solar self-consumption on
solarised feeders.

Start with a greedy/heuristic assignment; upgrade to MILP if time allows. **A heuristic that
runs is worth more than an MILP that doesn't.**

### 4.4 Trust layer
Marathi SMS / IVR, published ≥48h ahead:
> *"Feeder 47: power tomorrow 10:00–18:00. Rain expected Thursday — do not irrigate Wednesday."*

This is not a nice-to-have. It is the delivery mechanism for the entire behavioural saving.
Without published-in-advance schedules, defensive pumping does not fall.

---

## 5. Data — all public, all free

| Source | Use | Access |
|---|---|---|
| Sentinel-2 L2A (ESA Copernicus) | NDVI, canopy | Google Earth Engine / Copernicus Hub |
| Landsat 8/9 (USGS) | Land surface temperature → ET | Earth Engine |
| Open-Meteo / ERA5 | Reference ET, forecast | Free API |
| IMD | District rainfall, QPF | Public bulletins |
| ICAR / FAO-56 | Crop calendars, Kc values | Published |
| CGWB | Observation-well groundwater levels | Public portal |
| MSEDCL | Published ag feeder rota schedules, tariff orders | mahadiscom.in / MERC orders |
| CEA, Grid-India | State demand, RE generation | Public reports |
| MNRE / MSKVY | Solarised feeder locations & capacity | Scheme documents |

No field access required. No hardware. No proprietary data. This is a feature — state it
explicitly in the deck as *reproducibility*, not as a limitation.

---

## 6. Quantification methodology

This section decides whether we win. Judges are Schneider engineers; they will attack the
numbers before they attack the idea.

**Baseline:** an **MSKVY-solarised feeder cluster**, one full rabi season. MSEDCL does not
publish per-feeder rota, so we do not depend on it. On a solarised feeder the supply window
tracks a known solar plant (1–10 MW, ~08:00–18:00), and generation is reconstructable from
public irradiance. This makes the baseline *computable* rather than *requested*.

**Counterfactual:** CropClock's schedule over the same period, **delivering the same statutory
hours per feeder**. Not fewer hours — the saving must not come from rationing.

### 6.1 Backtest results (run 2026-09-08)

Executed. See `analysis/backtest.py` and `analysis/RESULTS.md`. Solapur district,
2025-26 kharif and rabi, observed ERA5 weather via Open-Meteo. Representative feeder: 250 ×
7.5 HP pumps on a 50 m borewell, 500 ha, 1 MW MSKVY plant.

| | Rabi | Kharif | Year |
|---|---|---|---|
| Tier A — solar coincidence | 106.7 MWh | 21.5 MWh | **128.2 MWh** |
| Solar share of pump energy | 35.2% → 48.6% | 21.9% → 31.1% | |
| Subsidy avoided | ₹8.01 L | ₹1.61 L | **₹9.62 L** |

**The backtest overturned the original framing.** Rain-skip was the headline Tier A lever in
the first draft of this spec. It saves **nothing** in rabi — Solapur got 101 mm of rain against
839 mm of reference ET, so there is no rain to skip. Solar alignment carries the entire dry-season
saving. In kharif the reverse holds: rain-skip against realistic irrigation behaviour saves
255.5 MWh, more than the whole rabi solar figure. **The lever is season-dependent**, which is now
its own slide (deck slide 09).

Largest single quantity in the model: defensive irrigation applies 1,200 mm in kharif where
138 mm meets crop demand, and 1,092 mm of that drains past the root zone. That gap is what the
trust layer exists to close — and it is Tier B, so it never becomes the headline.

**Report savings in two tiers, labelled as such:**

- **Tier A — hard (physical, no behavioural assumption).**
  Rain-skip avoided pumping + solar-coincidence gain. Derived from rainfall records and
  irradiance alone. Defensible to the decimal.
- **Tier B — soft (behavioural).**
  Reduction in defensive over-pumping from published-in-advance schedules. Calibrated from
  literature, reported as a range with explicit sensitivity analysis.

Metrics: kWh per feeder per season · mm/ha irrigation water · % of pump-hours coincident with
feeder solar · ₹ subsidy per feeder per year · groundwater draft proxy.

Then extrapolate to Maharashtra and to India, showing the assumption chain on one slide.

**Publishing the Tier A / Tier B split, and naming which half is modelled, is a deliberate
credibility play.** Most entrants will present one confident inflated number. We present two
honest ones.

---

## 7. Case study: Maharashtra

Chosen over Telangana and Andhra Pradesh because:

- MSEDCL still runs an 8-hour rota — the problem is live there.
- **MSKVY 2.0 is solarising ag feeders toward a 16,000 MW target**, so solar-coincidence is a
  real, funded lever today rather than a hypothetical.
- Marathwada / Vidarbha groundwater stress makes the water saving material.
- Rabi season (Nov–Mar) is low-cloud, which materially improves optical satellite coverage.

**Scope to MSKVY solarised feeders specifically.** This is a deliberate narrowing, and it
strengthens the submission three ways: the baseline becomes computable from irradiance instead
of depending on unpublished rota data; solar-coincidence gain becomes the headline Tier A
number; and it lands the project inside a scheme the state has already committed capital to, so
the deployment ask is software on funded infrastructure. Prayas (Energy Group) publishes
detailed public analysis of Maharashtra's solar agriculture feeders — primary citation source.

Telangana is excluded as a case study (24×7 free supply since 2018 — no scheduling problem to
solve) but retained in the narrative as the proof that predictability changes farmer behaviour,
and as the fiscal cautionary tale.

---

## 8. Round 1 deliverables — due 2026-10-04

Per the YouNoodle form (4 questions):

1. **Project Name** — CropClock
2. **Challenge** — 01, Sustainable Agriculture
3. **Project Description** — 300–500 words covering: problem, why it matters, solution,
   what is innovative, expected impact and beneficiaries
4. **Presentation** — 8–12 slides covering: problem statement, proposed solution, alignment to
   challenge, key features / user journey, technical approach, innovation, expected impact,
   implementation roadmap, team intro

Plus: Personal Form (6 questions) and team invitations (min 1, max 4; each member needs a
YouNoodle account on the invited email).

### Proposed slide structure (11 slides)

1. Title + the one-line pitch
2. The problem — 21.2M pumps, one-fifth of national electricity, scheduled by rota
3. The non-obvious insight — unpredictability causes over-pumping; reliability is a water technology
4. What exists and what doesn't — the two mature fields nobody has connected
5. CropClock — the four components, one diagram
6. Technical approach — satellite ET → deficit → scheduler → farmer
7. The numbers — Tier A hard, Tier B soft, Maharashtra case
8. Why it scales — 100% public data, zero hardware, rides RDSS/PM-KUSUM infrastructure already funded
9. Beneficiaries — farmer, DISCOM, state exchequer, groundwater table
10. Roadmap — Round 2 prototype → district pilot → DISCOM deployment
11. Team + honest limitations

---

## 9. Round 2 prototype — 2026-10-11 to 2026-11-22

Scoped for **2–3 people**, with an explicit cut list.

**Must ship (core demo):**
- Earth Engine pipeline: one Maharashtra district, one rabi season, weekly NDVI/ET → deficit map
- Rain-skip module against IMD/Open-Meteo historical forecasts
- Greedy feeder scheduler with fairness + capacity constraints
- Backtest harness: rota baseline vs CropClock, producing the Tier A numbers
- Web dashboard: deficit map, schedule comparison, savings panel

**Cut first if short-handed:**
- MILP optimiser (heuristic is sufficient for the demo)
- Live SMS/IVR integration (mock the message; do not build a gateway)
- Multi-district generalisation (one district proves it)
- CGWB validation (nice, not load-bearing)
- Tier B behavioural model (can stay a literature-cited estimate)

**Skills to recruit for, in priority order:** (1) geospatial/Python — Earth Engine, rasterio;
(2) frontend — the dashboard is the demo; (3) optimisation. If only one teammate joins, take
the geospatial person.

---

## 10. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Feeder → command-area mapping is not public | High | Approximate via land-use + Voronoi around distribution transformers; **state the approximation openly on a slide**. DISCOMs hold this data internally, so it is a deployment detail, not a design flaw. |
| ET noisy on sub-hectare smallholder plots | Medium | Aggregate to feeder command area — errors largely cancel. Never claim plot-level accuracy. |
| Defensive-pumping model is not measured | Medium | Tier A / Tier B split; sensitivity range; never headline the soft number. |
| Cloud cover breaks optical revisit | Low | Rabi is the dry season. Fall back to NDVI–Kc interpolation between clear passes. |
| Requires DISCOM adoption | Medium | The DISCOM pays the subsidy, so it holds the incentive. Software layer on infrastructure already funded by RDSS and PM-KUSUM — no new capex ask. |
| Judges ask "why hasn't anyone done this" | — | Because the two fields sit in different ministries and different companies. Have this answer ready; it is a strength. |

---

## 11. Open items

- [x] ~~Verify MSKVY 2.0 capacity target~~ — 16,000 MW, GR 13.09.2024; 2,269 MW tariff-approved Aug 2026
- [x] ~~Confirm MSEDCL publishes rota schedules~~ — it does **not**; baseline re-based on MSKVY solarised feeders (§7)
- [x] ~~Confirm Schneider/AutoGrid~~ — acquired May 2022, since divested to Uplight; internal note only, do not cite externally
- [x] ~~Select the specific district~~ — Solapur, Maharashtra (17.66 N, 75.90 E)
- [x] ~~Round 1 description~~ — 493 words, `round1/description.md`
- [x] ~~Round 1 deck~~ — 12 slides, `round1/deck.html` + PDF
- [x] ~~Tier A backtest~~ — `analysis/backtest.py`, results in `analysis/RESULTS.md`
- [ ] **Confirm team members and their YouNoodle-account emails** — blocks submission
- [ ] Personal Form (6 questions) on YouNoodle
- [ ] Round 2: replace FAO-56 stage coefficients with measured Sentinel-2 ET (needs a Google
      Earth Engine account — Rahul must register, it cannot be done on his behalf)
- [ ] Round 2: generalise the backtest across districts and rainfall years

---

## 12. Timeline

| Date | Milestone |
|---|---|
| 2026-09-08 | Design approved |
| ~2026-09-14 | 300–500 word description drafted; slide content locked |
| ~2026-09-21 | Deck built; team invited on YouNoodle |
| ~2026-09-28 | Review pass; buffer |
| **2026-10-04** | **Round 1 submission deadline (23:59 IST)** |
| 2026-10-11 → 11-22 | Round 2 prototype + judging |
| 2026-12-06 | Top teams announced |
| Jan 2027 | Finale, Schneider Electric India corporate office |
