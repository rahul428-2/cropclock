"""CropClock architecture diagram. Run: python architecture.py architecture.svg"""
import sys
from html import escape

W, H = 1440, 940
LH, PAD = 19, 16
INK, INK2, MUTED, LINE = "#0b0b0b", "#52514e", "#898781", "#c3c2b7"
ACCENT = "#2a78d6"
out = []


def text(x, y, s, size=13.5, weight=400, fill=INK2, anchor="start"):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
               f'text-anchor="{anchor}">{escape(s)}</text>')


def box(x, y, w, title, lines, tag=None, dashed=False, accent=False):
    h = 46 + len(lines) * LH + 8
    stroke = ACCENT if accent else LINE
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    fill = "#f3f7fd" if accent else "#ffffff"
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
               f'stroke="{stroke}" stroke-width="1.5"{dash}/>')
    text(x + PAD, y + 28, title, 15.5, 650, INK)
    for i, s in enumerate(lines):
        text(x + PAD, y + 50 + i * LH, s)
    if tag:
        label, color = tag
        tw = 9 + len(label) * 6.6
        out.append(f'<rect x="{x + w - tw - 10}" y="{y + 12}" width="{tw}" height="20" rx="10" fill="{color}"/>')
        text(x + w - tw / 2 - 10, y + 26, label, 11.5, 600, "#ffffff", "middle")
    return (x, y, w, h)


def arrow(pts, label=None, lpos=None, dashed=False, head=True):
    d = "M" + " L".join(f"{px},{py}" for px, py in pts)
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    out.append(f'<path d="{d}" fill="none" stroke="{MUTED}" stroke-width="1.6"{dash}{' marker-end="url(#a)"' if head else ''}/>')
    if label:
        lx, ly = lpos
        text(lx, ly, label, 12, 500, MUTED)


mid = lambda b: b[1] + b[3] / 2
right = lambda b: b[0] + b[2]
BUILT, MOCK, PLAN, DATA = ("built", "#0c7a3e"), ("mocked", "#b06a00"), ("planned", "#6b6a66"), ("live data", "#2a78d6")

out.append(f'<rect width="{W}" height="{H}" fill="#fcfcfb"/>')
text(40, 52, "CropClock — solution architecture", 26, 700, INK)
text(40, 80, "Decides which agricultural feeder is energised, and when, from crop water demand, the rain forecast and the feeder's own solar output.", 14.5, 400, INK2)

cols = [(40, 290, "1  Data in", "free, no account"), (380, 300, "2  Crop water layer", "per feeder, daily"),
        (730, 330, "3  Decision engine", "re-plans every day"), (1110, 290, "4  Delivery", "")]
for x, w, h1, h2 in cols:
    text(x, 124, h1, 16, 700, ACCENT if "Decision" in h1 else INK)
    if h2:
        text(x + w, 124, h2, 12.5, 500, MUTED, "end")
    out.append(f'<line x1="{x}" y1="134" x2="{x + w}" y2="134" stroke="{LINE}"/>')

x, w = cols[0][:2]
a1 = box(x, 150, w, "Sentinel-2 L2A", ["Element84 Earth Search (AWS)", "10 m red + NIR + scene class", "every ~5 days"], DATA)
a2 = box(x, a1[1] + a1[3] + 18, w, "Weather archive", ["Open-Meteo ERA5: observed rain,", "FAO-56 ET₀, hourly irradiance"], DATA)
a3 = box(x, a2[1] + a2[3] + 18, w, "Forecasts as issued", ["rain 1–2 days ahead,", "irradiance day ahead", "(Open-Meteo previous-runs)"], DATA)
a4 = box(x, a3[1] + a3[3] + 18, w, "Feeder register", ["command area, pumps, MSKVY", "solar MW, substation limit", "prototype: 8 × 500 ha, approx."], PLAN, dashed=True)

x, w = cols[1][:2]
b1 = box(x, 150, w, "Cloud mask → NDVI", ["drop cloud, shadow, cirrus pixels", "mean NDVI per feeder, each pass", "28 clear passes in rabi 2025-26"], BUILT)
b2 = box(x, b1[1] + b1[3] + 26, w, "Crop coefficient", ["Kc = 1.457 · NDVI − 0.1725", "interpolated daily between passes", "monsoon cloud → FAO-56 stages"], BUILT)
b3 = box(x, b2[1] + b2[3] + 26, w, "Soil water balance", ["deficit += Kc · ET₀ − 0.8 · rain", "irrigate at 80 mm (50% of TAW)", "FAO-56, per feeder"], BUILT)

x, w = cols[2][:2]
c1 = box(x, 150, w, "Rain-skip", ["≥15 mm forecast in next 48 h → defer", "never past 75% of soil capacity", "scored against rain that fell"], BUILT, accent=True)
c2 = box(x, c1[1] + c1[3] + 26, w, "Feeder scheduler (greedy)", ["need kWh = deficit ÷ 0.6 efficiency", "1  sunniest forecast hours first", "2  most water-stressed feeders first",
                                                             "3  ≤ 4 feeders on (substation cap)", "4  every feeder keeps 8 h/day", "5  overflow → hours nearest daylight"], BUILT, accent=True)
c3 = box(x, c2[1] + c2[3] + 26, w, "24 h × feeder switching plan", ["published 48 h ahead"], None, accent=True)

x, w = cols[3][:2]
d1 = box(x, 150, w, "DISCOM switching", ["plan sent to substation /", "RDSS smart-feeder SCADA"], PLAN, dashed=True)
d2 = box(x, d1[1] + d1[3] + 26, w, "Farmer notice", ["SMS / IVR in Marathi:", "\"your feeder runs 09–17\""], MOCK, dashed=True)
d3 = box(x, d2[1] + d2[3] + 26, w, "Dashboard", ["deficit map, schedule vs rota,", "savings — live on GitHub Pages"], BUILT)

# column 1 -> 2
arrow([(right(a1), mid(a1)), (b1[0], mid(a1))])
arrow([(b1[0] + 150, b1[1] + b1[3]), (b2[0] + 150, b2[1])])
arrow([(b2[0] + 150, b2[1] + b2[3]), (b3[0] + 150, b3[1])])
arrow([(right(a2), mid(a2)), (362, mid(a2)), (362, b3[1] + 30), (b3[0], b3[1] + 30)])
# forecasts + feeder register ride a lane under column 2
lane = max(b3[1] + b3[3], a4[1] + a4[3]) + 34
up = c1[1] + c1[3] - 24
arrow([(right(a3), mid(a3)), (345, mid(a3)), (345, lane), (715, lane), (715, up), (c1[0], up)])
arrow([(right(a4), mid(a4)), (345, mid(a4))], head=False)
arrow([(715, mid(c2)), (c2[0], mid(c2))])
text(400, lane - 8, "rain + sun forecasts · feeder limits", 12, 500, MUTED)
# column 2 -> 3
arrow([(right(b3), mid(b3)), (697, mid(b3)), (697, mid(c1)), (c1[0], mid(c1))])
arrow([(c1[0] + 165, c1[1] + c1[3]), (c2[0] + 165, c2[1])])
arrow([(c2[0] + 165, c2[1] + c2[3]), (c3[0] + 165, c3[1])])
# column 3 -> 4
bus = 1085
arrow([(right(c3), mid(c3)), (bus, mid(c3)), (bus, mid(d1)), (d1[0], mid(d1))])
arrow([(bus, mid(d2)), (d2[0], mid(d2))])
arrow([(bus, mid(d3)), (d3[0], mid(d3))])

# results band
ry = lane + 40
out.append(f'<rect x="40" y="{ry}" width="{W - 80}" height="132" rx="12" fill="#ffffff" stroke="{LINE}" stroke-width="1.5"/>')
text(60, ry + 30, "Backtest: 8 feeders, rabi 2025-26, real satellite passes, weather and forecasts — vs the MSEDCL day/night rota", 14.5, 650, INK)
stats = [("−24.8%", "grid energy (663 MWh)"), ("₹49.7 lakh", "subsidy avoided, one season"),
         ("50.6% → 15.2%", "pumping at night"), ("41.9% → 56.3%", "pump energy from solar")]
sw = (W - 120) / 4
for i, (v, l) in enumerate(stats):
    sx = 60 + i * sw
    text(sx, ry + 78, v, 30, 700, INK)
    text(sx, ry + 104, l, 13.5, 500, INK2)
# legend
ly = ry + 132 + 30
lx = 40
for label, color, note in [BUILT + ("in the prototype",), MOCK + ("message designed, no gateway",), PLAN + ("needs DISCOM integration",), DATA + ("public source",)]:
    tw = 9 + len(label) * 6.6
    out.append(f'<rect x="{lx}" y="{ly - 14}" width="{tw}" height="20" rx="10" fill="{color}"/>')
    text(lx + tw / 2, ly, label, 11.5, 600, "#ffffff", "middle")
    text(lx + tw + 8, ly, note, 12.5, 400, INK2)
    lx += tw + 8 + len(note) * 6.7 + 28
text(W - 40, ly, "github.com/rahul428-2/cropclock", 12.5, 500, MUTED, "end")

Hh = ly + 26
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" viewBox="0 0 {W} {Hh}" '
       f'font-family="-apple-system, system-ui, Segoe UI, Helvetica, Arial, sans-serif">'
       f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
       f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>' + "".join(out) + "</svg>")
open(sys.argv[1], "w").write(svg)
print(W, Hh)
