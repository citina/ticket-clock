#!/usr/bin/env python3
"""Download every LADOT parking citation inside the study box to data/citations_usc.csv,
LADOT's meter inventory for the same box to data/meters_usc.csv, and StreetsLA's posted
sweeping routes that reach into the box to data/sweep_routes.geojson.

Sources: data.lacity.org datasets 4f5p-udkv (Parking Citations, refreshed daily;
about 320k rows / 45 MB) and s49e-q6j2 (Metered Parking Inventory; about 700 spaces),
and StreetsLA's "Posted Street Sweeping Routes" layer on ArcGIS Online (about 26 route
days here). One request each, no key needed.
"""
import json
import urllib.parse
import urllib.request

from citations import BOX, CSV, DATA, METERS, ROUTES

URL = "https://data.lacity.org/resource/4f5p-udkv.csv"
COLS = ("ticket_number,issue_date,issue_time,meter_id,marked_time,location,route,agency,"
        "violation_code,violation_description,fine_amount,loc_lat,loc_long")

q = {"$select": COLS,
     "$where": f"loc_lat between {BOX['s']} and {BOX['n']} and loc_long between {BOX['w']} and {BOX['e']}",
     "$order": "ticket_number", "$limit": "2000000"}
DATA.mkdir(exist_ok=True)
tmp = CSV.with_suffix(".part")
with urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(q), timeout=600) as r, open(tmp, "wb") as f:
    while chunk := r.read(1 << 20):
        f.write(chunk)
tmp.replace(CSV)
print(CSV, sum(1 for _ in open(CSV)) - 1, "tickets")

# Every metered space, so a block whose meters never drew a ticket still counts as metered
q = {"$select": "spaceid,blockface,metertype,timelimit",
     "$where": f"within_box(latlng, {BOX['n']}, {BOX['w']}, {BOX['s']}, {BOX['e']})",
     "$order": "spaceid", "$limit": "50000"}
with urllib.request.urlopen("https://data.lacity.org/resource/s49e-q6j2.csv?" + urllib.parse.urlencode(q), timeout=120) as r:
    METERS.write_bytes(r.read())
print(METERS, sum(1 for _ in open(METERS)) - 1, "metered spaces")

# Posted sweeping routes: day, week pair, posted time and the area each one covers
URL = ("https://services1.arcgis.com/PTh9WC0Sf2WS7AAq/arcgis/rest/services/"
       "Posted_Street_Sweeping_Routes_Update/FeatureServer/0/query")
q = {"where": "1=1", "geometry": f"{BOX['w']},{BOX['s']},{BOX['e']},{BOX['n']}", "geometryType": "esriGeometryEnvelope",
     "inSR": "4326", "spatialRel": "esriSpatialRelIntersects", "outFields": "Route,Posted_Time,Posted_Day,Weeks",
     "returnGeometry": "true", "outSR": "4326", "f": "geojson"}
with urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(q), timeout=120) as r:
    body = r.read()
n = len(json.loads(body)["features"])  # an ArcGIS error comes back as 200 with no "features"
ROUTES.write_bytes(body)
print(ROUTES, n, "posted sweeping route days")
