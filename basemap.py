#!/usr/bin/env python3
"""Stitch the OpenStreetMap background for the study box into docs/basemap.jpg.

Same approach as Curb Log's map_spaces.py: a few dozen tiles at zoom 16, a
descriptive User-Agent, cached in .tilecache/ so re-runs don't refetch, faded so
the ticket layer carries the eye. Anything that shows it must credit
"© OpenStreetMap contributors".
"""
import io
import os
import urllib.request

from PIL import Image

from citations import BOX, DOCS, ROOT, TILE, ZOOM, deg2num, frame

UA = "ticket-clock/1.0 (personal parking study near USC; contact via github.com/citina)"
CACHE = ROOT / ".tilecache"


def get_tile(z, x, y):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{z}_{x}_{y}.png"
    if path.exists():
        return Image.open(path).convert("RGB")
    req = urllib.request.Request(f"https://tile.openstreetmap.org/{z}/{x}/{y}.png", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    path.write_bytes(data)
    return Image.open(io.BytesIO(data)).convert("RGB")


x0, y0 = (int(v) for v in deg2num(BOX["n"], BOX["w"]))
x1, y1 = (int(v) for v in deg2num(BOX["s"], BOX["e"]))
img = Image.new("RGB", ((x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE), "white")
for tx in range(x0, x1 + 1):
    for ty in range(y0, y1 + 1):
        img.paste(get_tile(ZOOM, tx, ty), ((tx - x0) * TILE, (ty - y0) * TILE))
f = frame()
left, top = f["x0"] - x0 * TILE, f["y0"] - y0 * TILE
img = img.crop((round(left), round(top), round(left) + f["W"], round(top) + f["H"]))
img = Image.blend(img, Image.new("RGB", img.size, "white"), 0.30)
DOCS.mkdir(exist_ok=True)
out = DOCS / "basemap.jpg"
img.save(out, quality=82, optimize=True, progressive=True)
print(out, img.size, f"{(x1 - x0 + 1) * (y1 - y0 + 1)} tiles", f"{os.path.getsize(out) // 1024} KB")
