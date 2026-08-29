# -*- coding: utf-8 -*-
"""Generate 3 PNG charts for the paper using PIL + numpy (no matplotlib needed)."""
import os
import re
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Paths are resolved relative to this script (works from any cwd / any unzip dir)
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
SRC = os.path.join(ROOT, 'results', 'result.txt')
OUTDIR = os.path.join(ROOT, 'docs')
os.makedirs(OUTDIR, exist_ok=True)

PAT = re.compile(r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([-0-9.eE+]+),\s*([-0-9.eE+]+)\)')

rows = []
for line in open(SRC, encoding='utf-8'):
    m = PAT.match(line.strip())
    if m:
        rows.append((int(m.group(1)), float(m.group(4)), float(m.group(5))))

# ---- fonts ----
def font(sz, bold=False):
    for path in [r'C:\Windows\Fonts\arial.ttf',
                 r'C:\Windows\Fonts\segoeui.ttf']:
        try:
            return ImageFont.truetype(path, sz)
        except Exception:
            continue
    return ImageFont.load_default()

F_TITLE = font(20, True)
F_LABEL = font(14, True)
F_TICK = font(12)
F_LEG = font(13)

W, H = 800, 500

def new_canvas():
    img = Image.new('RGB', (W, H), 'white')
    return img, ImageDraw.Draw(img)

def draw_axes(d, x0, y0, x1, y1, xticks, yticks, xlab, ylab, xfmt=str, yfmt=str, logx=False, logy=False):
    """x0,y0 = bottom-left of plot area; x1,y1 = top-right."""
    # axes
    d.line([(x0, y0), (x1, y0)], fill='#333', width=2)   # x axis
    d.line([(x0, y0), (x0, y1)], fill='#333', width=2)   # y axis
    # ticks x
    for tv, l in xticks:
        x = x0 + (x1 - x0) * (math.log10(tv) - math.log10(xticks[0][0])) / (math.log10(xticks[-1][0]) - math.log10(xticks[0][0])) if logx else \
            x0 + (x1 - x0) * (tv - xticks[0][0]) / (xticks[-1][0] - xticks[0][0])
        d.line([(x, y0), (x, y0 + 5)], fill='#333')
        d.text((x - 20, y0 + 6), xfmt(l), font=F_TICK, fill='#333')
    # ticks y
    for tv, l in yticks:
        y = y1 + (y0 - y1) * (math.log10(tv) - math.log10(yticks[0][0])) / (math.log10(yticks[-1][0]) - math.log10(yticks[0][0])) if logy else \
            y1 + (y0 - y1) * (tv - yticks[0][0]) / (yticks[-1][0] - yticks[0][0])
        d.line([(x0 - 5, y), (x0, y)], fill='#333')
        d.text((x0 - 46, y - 8), yfmt(l), font=F_TICK, fill='#333')
    # labels
    d.text(((x0 + x1) / 2 - 30, y0 + 30), xlab, font=F_LABEL, fill='#111')
    # y label rotated: draw vertically by stacking chars
    yy = (y0 + y1) / 2 - 30
    for i, ch in enumerate(ylab):
        d.text((8, yy + i * 16), ch, font=F_LABEL, fill='#111')

def v2coord(v, x0, x1, xmin, xmax, log=False):
    if log:
        return x0 + (x1 - x0) * (math.log10(v) - math.log10(xmin)) / (math.log10(xmax) - math.log10(xmin))
    return x0 + (x1 - x0) * (v - xmin) / (xmax - xmin)

def v2coord_y(v, y0, y1, ymin, ymax, log=False):
    # y0=screen bottom, y1=screen top (y1<y0). v=ymin -> y0; v=ymax -> y1
    if log:
        return y0 + (y1 - y0) * (math.log10(v) - math.log10(ymin)) / (math.log10(ymax) - math.log10(ymin))
    return y0 + (y1 - y0) * (v - ymin) / (ymax - ymin)

# ============ Chart 1: |V_T| vs R (median/max, log y) ============
img, d = new_canvas()
d.text((W/2 - 200, 18), 'True correlation |V_T| vs rounds R (log scale)', font=F_TITLE, fill='#111')
byR = {}
for r, vt, ve in rows:
    byR.setdefault(r, []).append(abs(vt))
rs = sorted(byR)
x0, y0, x1, y1 = 80, 400, 740, 80
# log y from 1e-6 to 1
ymin, ymax = 1e-6, 1.0
# grid lines
for e in range(-6, 1):
    y = v2coord_y(10 ** e, y0, y1, ymin, ymax, log=True)
    d.line([(x0, y), (x1, y)], fill='#e0e0e0')
med_pts = []
max_pts = []
for r in rs:
    arr = np.array(byR[r])
    med_pts.append((r, float(np.median(arr))))
    max_pts.append((r, float(np.max(arr))))
# max line (red), median line (blue)
d.line([(x0, y0), (x1, y0)], fill='#333', width=2)
d.line([(x0, y0), (x0, y1)], fill='#333', width=2)
for pts, color, lab in [(med_pts, '#1f77b4', 'median |V_T|'), (max_pts, '#d62728', 'max |V_T|')]:
    px = [v2coord(r, x0, x1, 1, 20) for r, _ in pts]
    py = [v2coord_y(v, y0, y1, ymin, ymax, log=True) for _, v in pts]
    d.line(list(zip(px, py)), fill=color, width=3)
    for x, y in zip(px, py):
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=color)
    d.text((600, y0 - 20 if lab == 'max |V_T|' else y0 - 40), lab, font=F_LEG, fill=color)
# x ticks 1..20
for r in rs:
    x = v2coord(r, x0, x1, 1, 20)
    d.line([(x, y0), (x, y0 + 5)], fill='#333')
    d.text((x - 5, y0 + 6), str(r), font=F_TICK, fill='#333')
for e in range(-6, 1):
    y = v2coord_y(10 ** e, y0, y1, ymin, ymax, log=True)
    d.text((x0 - 42, y - 8), f'1e{e}', font=F_TICK, fill='#333')
d.text((380, y0 + 30), 'Rounds R', font=F_LABEL, fill='#111')
img.save(f'{OUTDIR}/chart_corr_vs_rounds.png')
print('chart1 ok')

# ============ Chart 2: |V_E| vs |V_T| scatter, ±25% window ============
img, d = new_canvas()
d.text((W/2 - 190, 18), 'V_E vs V_T (|values|, log-log; dashed = 0.75x, 1.25x)', font=F_TITLE, fill='#111')
x0, y0, x1, y1 = 90, 420, 730, 90
vmin, vmax = 1e-6, 1.0
for e in range(-6, 1):
    y = v2coord_y(10 ** e, y0, y1, vmin, vmax, log=True)
    d.line([(x0, y), (x1, y)], fill='#e0e0e0')
    x = v2coord(10 ** e, x0, x1, vmin, vmax, log=True)
    d.line([(x, y0), (x, y1)], fill='#e0e0e0')
# window lines 0.75x and 1.25x
for k, col in [(0.75, '#888'), (1.25, '#888')]:
    pts = []
    for e in np.linspace(-6, 0, 50):
        v = 10 ** e
        pts.append((v2coord(v, x0, x1, vmin, vmax, log=True),
                    v2coord_y(k * v, y0, y1, vmin, vmax, log=True)))
    d.line(pts, fill=col, width=1, joint='curve')
# scatter
n_ok = n_bad = 0
for r, vt, ve in rows:
    if vt == 0 or ve == 0:
        continue
    a, b = abs(vt), abs(ve)
    if 0.75 * a <= b <= 1.25 * a:
        col, n_ok = '#1a7f37', n_ok + 1
    else:
        col, n_bad = '#c0392b', n_bad + 1
    x = v2coord(a, x0, x1, vmin, vmax, log=True)
    y = v2coord_y(b, y0, y1, vmin, vmax, log=True)
    d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col)
# axes
d.line([(x0, y0), (x1, y0)], fill='#333', width=2)
d.line([(x0, y0), (x0, y1)], fill='#333', width=2)
for e in range(-6, 1):
    y = v2coord_y(10 ** e, y0, y1, vmin, vmax, log=True)
    d.text((x0 - 42, y - 8), f'1e{e}', font=F_TICK, fill='#333')
    x = v2coord(10 ** e, x0, x1, vmin, vmax, log=True)
    d.text((x - 18, y0 + 6), f'1e{e}', font=F_TICK, fill='#333')
d.text((300, y0 + 30), '|V_T|', font=F_LABEL, fill='#111')
d.text((40, y0 - 120), '|V_E|', font=F_LABEL, fill='#111')
d.text((600, 110), f'valid {n_ok}', font=F_LEG, fill='#1a7f37')
d.text((600, 130), f'outside {n_bad}', font=F_LEG, fill='#c0392b')
img.save(f'{OUTDIR}/chart_ve_vs_vt.png')
print('chart2 ok, valid', n_ok, 'bad', n_bad)

# ============ Chart 3: valid entries & score by R (bar) ============
img, d = new_canvas()
d.text((W/2 - 190, 18), 'Valid entries and score by rounds R', font=F_TITLE, fill='#111')
x0, y0, x1, y1 = 80, 400, 740, 80
rs = sorted(byR)
nvalid_byR = {}
score_byR = {}
for r, vt, ve in rows:
    nvalid_byR.setdefault(r, [0, 0])
    nvalid_byR[r][1] += 1
    if ve != 0 and 0.75 * abs(vt) <= abs(ve) <= 1.25 * abs(vt):
        nvalid_byR[r][0] += 1
        s = math.log2((2 ** (2 * r)) * abs(ve))
        score_byR[r] = score_byR.get(r, 0) + max(s, 0)
maxv = max(r[1] for r in nvalid_byR.values())
barw = (x1 - x0) / (len(rs) * 1.6)
for i, r in enumerate(rs):
    n, tot = nvalid_byR[r]
    cx = x0 + (x1 - x0) * (i + 0.5) / len(rs)
    # total bar (light)
    y_tot = v2coord_y(tot, y0, y1, 0, maxv)
    y_n = v2coord_y(n, y0, y1, 0, maxv)
    d.rectangle([cx - barw / 2, y_tot, cx + barw / 2, y0], fill='#d5dbe0')
    d.rectangle([cx - barw / 2, y_n, cx + barw / 2, y0], fill='#2c7fb8')
    d.text((cx - 6, y0 + 6), str(r), font=F_TICK, fill='#333')
    d.text((cx - barw / 2, y_n - 18), str(n), font=F_TICK, fill='#2c7fb8')
d.line([(x0, y0), (x1, y0)], fill='#333', width=2)
d.line([(x0, y0), (x0, y1)], fill='#333', width=2)
for t in range(0, maxv + 1, 8):
    y = v2coord_y(t, y0, y1, 0, maxv)
    d.line([(x0 - 5, y), (x0, y)], fill='#333')
    d.text((x0 - 22, y - 8), str(t), font=F_TICK, fill='#333')
d.text((350, y0 + 30), 'Rounds R (dark = valid, light = total)', font=F_LABEL, fill='#111')
img.save(f'{OUTDIR}/chart_valid_by_round.png')
print('chart3 ok')

print('ALL CHARTS DONE')
