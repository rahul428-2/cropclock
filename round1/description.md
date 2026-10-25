# CropClock — Project Description (Round 1)

**Field:** Project Description (300–500 words, max 500)
**Challenge:** 01 — Sustainable Agriculture: Energy, Water & Productivity

---

India supplies electricity to 21.2 million agricultural pumpsets — roughly a fifth of national
consumption — on a fixed rotational roster. A feeder's eight-hour window is decided months in
advance and is blind to three things that change every week: rainfall, crop growth stage, and,
on the feeders now being solarised under Maharashtra's 16,000 MW Mukhyamantri Saur Krushi
Vahini scheme, the feeder's own generation. Power arrives the morning after 40mm of rain. Pumps
run at 6 a.m. while the feeder's solar plant peaks at noon.

This matters because of a mechanism most interventions miss. Farmers over-irrigate not because
they lack information, but because supply is unpredictable: if you cannot forecast when power
returns, flooding the field while you have it is the rational choice. Existing products — soil
sensors, advisory apps — target the farmer's knowledge. None targets the uncertainty that
drives the behaviour. Reliability is itself a water-saving technology.

CropClock is the scheduling layer that has never been built. It estimates actual crop water
deficit from free Sentinel-2 and Landsat imagery using a surface-energy-balance
evapotranspiration model, aggregates it to each feeder's command area, and combines it with IMD
rainfall forecasts and solar generation forecasts to decide which feeder is energised, and
when. It cancels windows ahead of rain, aligns pumping with the feeder's own solar output, and
publishes the schedule to farmers by SMS and IVR at least 48 hours ahead — because a schedule
changes behaviour only if it is trusted. Every feeder still receives its full statutory hours.
The saving comes from timing, not from rationing.

What is genuinely new is the connection. Satellite crop-water-stress estimation is a mature
field. Agricultural feeder scheduling is a mature operational practice across at least six
states. The two have never been joined: crop-water software advises farmers and assumes power
is available, while feeder scheduling optimises fairness and load, and has never once looked at
a crop.

We have already backtested this on observed weather for Solapur district across the 2025-26
kharif and rabi seasons. On a representative feeder — 250 pumps, 500 hectares, a 1 MW MSKVY
plant — realigning the supply window raises the share of pump energy served by the feeder's own
solar from 35% to 49% in rabi, avoiding 128 MWh of grid energy and ₹9.6 lakh of subsidy per
feeder per year. No behavioural assumption enters that figure. The backtest also corrected us:
rain-skip, which we expected to lead with, saves nothing in the dry rabi season but 255 MWh in
kharif. The lever changes with the season, so we report the physical saving and the behavioural
one separately rather than as a single headline.

Beneficiaries: farmers gain predictable, adequate irrigation; DISCOMs cut subsidised units and
raise solar self-consumption; state exchequers cut agricultural subsidy; and aquifers in
stressed districts see reduced draft. The system needs no new hardware, no proprietary data and
no field deployment. It is software layered on infrastructure India is already funding through
PM-KUSUM and RDSS.
