
import os, json, pathlib

from app.state import StateStore

OUT_DIR = pathlib.Path("exports")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def html_escape(s): 
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

def donut_svg(filled, total, size=72, stroke=10):
    import math
    radius = (size - stroke) / 2
    center = size/2
    circumference = 2 * math.pi * radius
    progress = (filled / max(1,total)) * circumference
    remaining = circumference - progress
    return f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <circle cx="{center}" cy="{center}" r="{radius}" fill="none" stroke="#e5e7eb" stroke-width="{stroke}" />
  <circle cx="{center}" cy="{center}" r="{radius}" fill="none" stroke="#10b981" stroke-width="{stroke}"
    stroke-dasharray="{progress} {remaining}" transform="rotate(-90 {center} {center})" stroke-linecap="round"/>
</svg>'''

def main():
    st = StateStore().get()
    parts = ['''<meta charset="utf-8"><style>
body{font-family:Inter,Arial,sans-serif}
.card{border:1px solid #e5e7eb;border-radius:12px;padding:10px;margin:6px;display:inline-block;min-width:220px}
.badge{background:#eef6ff;border:1px solid #bfdbfe;padding:0 6px;border-radius:8px;font-size:12px}
.hsec{font-weight:700;margin-top:12px}
</style>''']
    parts.append(f"<h1>{html_escape(st.get('crew',{}).get('name','Crew'))} — Cards</h1>")
    parts.append("<h2>Players</h2>")
    for name, data in st.get("players", {}).items():
        xp = int(data.get("xp",0)); adv = int(data.get("advances",0))
        parts.append(f'''<div class="card"><div class="hsec">{html_escape(name)} <span class="badge">XP {xp} (adv {adv})</span></div>
<div>Stress: {int(data.get('stress',0))} / 9</div>
<div>Trauma: {", ".join(map(html_escape, data.get("trauma", []))) or "—"}</div>
</div>''')
    parts.append("<h2>Factions</h2>")
    for name, fac in st.get("factions", {}).items():
        clocks = "".join([f"<div>{html_escape(c['name'])}{donut_svg(int(c.get('filled',0)), int(c.get('segments',4)) )}</div>" for c in fac.get("clocks",[])])
        parts.append(f'''<div class="card"><div class="hsec">{html_escape(name)} <span class="badge">Status {int(fac.get("status",0))}</span></div>
{clocks or "<i>No clocks</i>"}
</div>''')
    html = "\n".join(parts)
    out = OUT_DIR / "cards.html"
    out.write_text(html, encoding="utf-8")
    print(str(out))

if __name__ == "__main__":
    main()
