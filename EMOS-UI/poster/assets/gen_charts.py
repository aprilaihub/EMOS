#!/usr/bin/env python3
"""Generate print-crisp SVG charts for the EMOS poster."""
import os
OUT = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(OUT, exist_ok=True)

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

INK, INK3, LINE, LINE2 = "#1a1d29", "#6b7280", "#e2e5ea", "#c8cdd6"
STABLE, MARGINAL, UNSTABLE, ACCENT = "#92a2df", "#f2a359", "#c8cdd6", "#92a2df"
SANS = "font-family='SF Pro Display, Arial, sans-serif'"
MONO = "font-family='SF Mono, ui-monospace, monospace'"

# ---------- 1. band-gap screening chart ----------
# (formula, band gap eV, stability)
cands = [
    ("Ga₂O₃", 4.80, STABLE), ("SnO₂", 3.60, STABLE),
    ("GaN", 3.42, STABLE), ("ZnO", 3.30, STABLE),
    ("In₂O₃", 2.90, MARGINAL), ("Fe₂O₃", 2.20, MARGINAL),
    ("MoS₂", 1.80, STABLE), ("WSe₂", 1.62, MARGINAL),
    ("CdTe", 1.50, STABLE), ("Bi₂Te₃", 0.30, UNSTABLE),
]
x0, k, pitch, top = 92, 70.0, 27, 12
bar_h = 17
W, H = 470, top + len(cands) * pitch + 34
tgt_x = x0 + 3.0 * k            # Eg = 3 eV target threshold
s = [f'<svg class="chart" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
# target region shading (Eg >= 3 eV)
s.append(f'<rect x="{tgt_x:.1f}" y="4" width="{x0+5*k-tgt_x:.1f}" height="{len(cands)*pitch:.0f}" fill="#eef1fb"/>')
s.append(f'<text x="{tgt_x+4:.1f}" y="{top-1}" {MONO} font-size="9" fill="#5a6dc0">target: E_g &gt; 3 eV</text>')
# axis gridlines + ticks
for ev in range(0, 6):
    gx = x0 + ev * k
    s.append(f'<line x1="{gx:.1f}" y1="4" x2="{gx:.1f}" y2="{top+len(cands)*pitch:.0f}" stroke="{LINE}" stroke-width="0.6"/>')
    s.append(f'<text x="{gx:.1f}" y="{H-14}" {MONO} font-size="10" fill="{INK3}" text-anchor="middle">{ev}</text>')
s.append(f'<text x="{x0+2.5*k:.1f}" y="{H-2}" {SANS} font-size="10.5" fill="{INK3}" text-anchor="middle">Predicted band gap (eV)</text>')
for i, (f, ev, col) in enumerate(cands):
    y = top + i * pitch
    w = ev * k
    s.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="1.5" fill="{col}"/>')
    s.append(f'<text x="{x0-6}" y="{y+bar_h-4}" {SANS} font-size="11.5" font-weight="700" fill="{INK}" text-anchor="end">{f}</text>')
    s.append(f'<text x="{x0+w+4:.1f}" y="{y+bar_h-4}" {MONO} font-size="10.5" fill="{INK3}">{ev:.2f}</text>')
s.append('</svg>')
open(os.path.join(OUT, "bandgap.svg"), "w").write("\n".join(s))

# ---------- 2. heuristic severity (paired before/after bars) ----------
heur = [
    ("User control & freedom", 3.5, 0.5), ("Visibility of status", 3.0, 1.0),
    ("Error prevention", 3.0, 0.5), ("Consistency", 2.5, 1.0),
    ("Help & documentation", 2.5, 1.0),
]
lx, hx0, hk = 200, 206, 55.0          # label width, bar origin, px per severity unit
rpitch, bh, gap = 48, 16, 3
W2, H2 = 490, 10 + len(heur) * rpitch + 20
s2 = [f'<svg class="chart" viewBox="0 0 {W2} {H2}" xmlns="http://www.w3.org/2000/svg">']
# severity axis 0..4
for sv in range(0, 5):
    gx = hx0 + sv * hk
    s2.append(f'<line x1="{gx:.1f}" y1="6" x2="{gx:.1f}" y2="{10+len(heur)*rpitch:.0f}" stroke="{LINE}" stroke-width="0.6"/>')
    s2.append(f'<text x="{gx:.1f}" y="{H2-4}" {MONO} font-size="10" fill="{INK3}" text-anchor="middle">{sv}</text>')
s2.append(f'<text x="{hx0+2*hk:.1f}" y="{H2-4}" {SANS} font-size="10" fill="{INK3}" text-anchor="middle"></text>')
for i, (name, b, a) in enumerate(heur):
    yt = 12 + i * rpitch
    s2.append(f'<text x="{lx-8}" y="{yt+2+bh}" {SANS} font-size="13" font-weight="600" fill="{INK}" text-anchor="end">{esc(name)}</text>')
    s2.append(f'<rect x="{hx0}" y="{yt}" width="{b*hk:.1f}" height="{bh}" rx="1.5" fill="{MARGINAL}"/>')
    s2.append(f'<text x="{hx0+b*hk+5:.1f}" y="{yt+bh-3}" {MONO} font-size="10.5" fill="{INK3}">{b:.1f}</text>')
    s2.append(f'<rect x="{hx0}" y="{yt+bh+gap}" width="{a*hk:.1f}" height="{bh}" rx="1.5" fill="{STABLE}"/>')
    s2.append(f'<text x="{hx0+a*hk+5:.1f}" y="{yt+2*bh+gap-3}" {MONO} font-size="10.5" fill="{INK3}">{a:.1f}</text>')
s2.append('</svg>')
open(os.path.join(OUT, "heuristic.svg"), "w").write("\n".join(s2))
print("charts written to", OUT)
