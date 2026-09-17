#!/usr/bin/env python3
"""Download what the city-wide street rules page needs into data/city/ (not committed):

- tickets/YYYY-MM.csv: every LADOT parking citation in the last two years (plus the month the window
  starts in), one file per month (data.lacity.org 4f5p-udkv, about 160k rows / 17 MB a month).
  Months already on disk are kept, the last two are always refetched since the feed keeps filling
  them in, and months that fall out of the window are deleted, so the download doesn't grow.
- centerlines.json: the City of Los Angeles street centerlines with address ranges per side
  and the intersection at each end (LA GeoHub, Street_Information MapServer layer 36, ~85k segments).
- meters.csv: LADOT's metered parking inventory for the whole city (s49e-q6j2, ~35k spaces).
- sweep_routes.geojson: StreetsLA's posted sweeping routes for the whole city (~870 route days),
  the same layer fetch_citations.py saves for the USC box.
"""
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

from citations import DATA, WINDOW

CITY = DATA / "city"
TICKETS = "https://data.lacity.org/resource/4f5p-udkv.csv"
COLS = "issue_date,issue_time,meter_id,location,violation_code,violation_description,fine_amount,loc_lat,loc_long"
STREETS = "https://maps.lacity.org/lahub/rest/services/Street_Information/MapServer/36/query"
FIELDS = "ASSETID,INT_ID_FROM,INT_ID_TO,ADLF,ADLT,ADRF,ADRT,ZIP_L,ZIP_R,TDIR,STNAME,STSFX,SFXDIR,STATUS,Street_Designation"


def get(url, params, timeout=600, tries=4):
    """One request, retried on a server error: the city's map server hands out the odd 502, and a
    single one shouldn't throw away a download that takes minutes."""
    for k in range(tries):
        try:
            with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=timeout) as r:
                return r.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            code = getattr(e, "code", None)
            if k == tries - 1 or (code is not None and code < 500):
                raise
            print(f"warning: {url.split('/')[2]} said {code or e}; retrying in {20 * (k + 1)}s")
            time.sleep(20 * (k + 1))


def get_json(url, params, **kw):
    """A request whose answer has to parse as JSON: the map server also answers 200 with an HTML
    error page, which is just as broken as a 502."""
    for k in range(4):
        body = get(url, params, **kw)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            if k == 3:
                raise
            print(f"warning: {url.split('/')[2]} answered with something that isn't JSON; retrying in {20 * (k + 1)}s")
            time.sleep(20 * (k + 1))


def months(start, end):
    m = start.replace(day=1)
    while m <= end:
        nxt = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        yield m, nxt
        m = nxt


# ---- tickets, a month at a time ----
tdir = CITY / "tickets"
tdir.mkdir(parents=True, exist_ok=True)
today = dt.date.today()
start = (pd.Timestamp(today) - WINDOW).date().replace(day=1)
for old in tdir.glob("*.csv"):
    if old.stem < f"{start:%Y-%m}":
        old.unlink()
recent = {m for m, _ in list(months(start, today))[-2:]}
for m, nxt in months(start, today):
    out = tdir / f"{m:%Y-%m}.csv"
    if out.exists() and m not in recent:
        continue
    body = get(TICKETS, {"$select": COLS, "$where": f'issue_date >= "{m}" and issue_date < "{nxt}"',
                         "$order": "issue_date", "$limit": "2000000"})
    tmp = out.with_suffix(".part")
    tmp.write_bytes(body)
    tmp.replace(out)
    print(out.name, body.count(b"\n") - 1, "tickets")

# ---- street centerlines, 1,000 per request ----
feats, off = [], 0
while True:
    page = get_json(STREETS, {"where": "1=1", "outFields": FIELDS, "outSR": "4326", "orderByFields": "OBJECTID",
                              "resultOffset": off, "resultRecordCount": 1000, "f": "geojson"}, timeout=120)
    feats += page["features"]
    off += len(page["features"])
    if not page["features"] or not (page.get("exceededTransferLimit") or page.get("properties", {}).get("exceededTransferLimit")):
        break
(CITY / "centerlines.json").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
print("centerlines.json", len(feats), "segments")

# ---- metered spaces ----
body = get("https://data.lacity.org/resource/s49e-q6j2.csv",
           {"$select": "spaceid,blockface,metertype,ratetype,raterange,timelimit,latlng", "$order": "spaceid", "$limit": "100000"}, timeout=120)
(CITY / "meters.csv").write_bytes(body)
print("meters.csv", body.count(b"\n") - 1, "spaces")

# ---- posted sweeping routes: day, week pair, posted time and area ----
routes = get_json("https://services1.arcgis.com/PTh9WC0Sf2WS7AAq/arcgis/rest/services/Posted_Street_Sweeping_Routes_Update/FeatureServer/0/query",
                  {"where": "1=1", "outFields": "Route,Posted_Time,Posted_Day,Weeks", "returnGeometry": "true", "outSR": "4326", "f": "geojson"}, timeout=120)
(CITY / "sweep_routes.geojson").write_text(json.dumps(routes, separators=(",", ":")))   # an ArcGIS error is a 200 with no features
print("sweep_routes.geojson", len(routes["features"]), "posted sweeping route days")
