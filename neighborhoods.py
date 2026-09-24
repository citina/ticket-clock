#!/usr/bin/env python3
"""Write docs/streets/hoods.json: the neighborhood outlines LA Street Rules draws on its city-wide map.

They're the Los Angeles Times' neighborhood boundaries (CC BY 4.0) for the 114 neighborhoods fully or
partly inside the City of Los Angeles, as the city publishes them on LA GeoHub, less the ones in SKIP.
They don't change, so the file is committed and this only needs running again if the city updates the layer.

The server simplifies the shapes (to about 2.5 m). Each neighborhood is [name, ring, ring, ...]; a ring
is its first point in zoom-17 Web Mercator pixels (the page's map units before its local shift), then
the step to each next point, all whole pixels (about 1 m in LA).
"""
import json
import urllib.parse
import urllib.request

from citations import DOCS

LAYER = "https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/LA_Times_Neighborhoods/FeatureServer/0/query"
HALF = 20037508.342789244   # half the Web Mercator world, in its metres
N17 = 2 ** 17 * 256
SKIP = {"Chatsworth Reservoir"}   # no ticketed streets (one block in the 2024-26 data), so nothing to show there

params = dict(where="1=1", outFields="name", returnGeometry="true", outSR=3857, maxAllowableOffset=3,
              geometryPrecision=0, f="json")
with urllib.request.urlopen(LAYER + "?" + urllib.parse.urlencode(params), timeout=120) as r:
    feats = json.load(r)["features"]

out = []
for f in sorted(feats, key=lambda f: f["attributes"]["name"]):
    if f["attributes"]["name"].strip() in SKIP:
        continue
    rings = []
    for ring in f["geometry"]["rings"]:
        pts = [(round((x + HALF) / (2 * HALF) * N17), round((HALF - y) / (2 * HALF) * N17)) for x, y in ring]
        pts = [p for i, p in enumerate(pts) if not i or p != pts[i - 1]]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts.pop()   # the page closes each ring itself
        if len(pts) < 3:
            continue
        flat = list(pts[0])
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            flat += [bx - ax, by - ay]
        rings.append(flat)
    out.append([f["attributes"]["name"].strip(), *rings])

path = DOCS / "streets" / "hoods.json"
path.write_text(json.dumps({"src": "Los Angeles Times neighborhood boundaries (CC BY 4.0), via LA GeoHub", "h": out},
                           separators=(",", ":")))
print(f"{len(out)} neighborhoods, {sum(len(r) // 2 for h in out for r in h[1:]):,} points, "
      f"{path.stat().st_size / 1024:.0f} KB -> {path}")
