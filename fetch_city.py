#!/usr/bin/env python3
"""Download what the city-wide street rules page needs into data/city/ (not committed):

- tickets/YYYY-MM.csv: every LADOT parking citation in the last two years (plus the month the window
  starts in), one file per month (data.lacity.org 4f5p-udkv, about 160k rows / 17 MB a month).
  The last two months are refetched every run since the feed keeps filling them in, plus the six
  older months whose copies are oldest, so each month is rechecked about once a month. Months that
  fall out of the window are deleted, so the download doesn't grow.
- centerlines.json: the City of Los Angeles street centerlines with address ranges per side
  and the intersection at each end (LA GeoHub, Street_Information MapServer layer 36, ~85k segments).
  They barely change, so they're refetched once the copy is four weeks old.
- meters.csv: LADOT's metered parking inventory for the whole city (s49e-q6j2, ~35k spaces).
- sweep_routes.geojson: StreetsLA's posted sweeping routes for the whole city (~870 route days),
  the same layer fetch_citations.py saves for the USC box.
- fetched.json: the date each file above was downloaded.

The weekly workflow keeps data/city/ between runs (the city-downloads release). When a download fails
and an older copy is on disk, that copy is kept with a warning, so a city server that's down for a day
doesn't stop the rebuild; a file with no copy yet still stops it.
"""
import datetime as dt
import json
import sys
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


missing = []   # files with no copy yet that couldn't be downloaded; the run fails at the end, after the rest


def refresh(name, fetch):
    """Run fetch(path), which writes data/city/<name> and returns a line to print. If it fails and an
    older copy exists, keep that copy and say so. With no copy, carry on with the other files and fail at
    the end, so what did download is kept for the next run."""
    path = CITY / name
    try:
        print(fetch(path))
        fetched[name] = today.isoformat()
    except Exception as e:
        if not path.exists():
            print(f"error: couldn't download {name} ({str(e)[:120]}), and there's no earlier copy")
            missing.append(name)
            return
        print(f"warning: couldn't refresh {name} ({str(e)[:120]}); keeping the copy from {fetched.get(name, 'an earlier run')}")


def write(path, body):
    tmp = path.with_suffix(".part")   # a run that dies halfway leaves the old copy, not half a file
    tmp.write_bytes(body)
    tmp.replace(path)


def months(start, end):
    m = start.replace(day=1)
    while m <= end:
        nxt = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        yield m, nxt
        m = nxt


NL = b"\n"
ROLL = 6          # older ticket months refetched per run, the ones whose copies are oldest
STREETS_DAYS = 28  # the centerlines are refetched once the copy is this old

tdir = CITY / "tickets"
tdir.mkdir(parents=True, exist_ok=True)
today = dt.date.today()
MANIFEST = CITY / "fetched.json"
fetched = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}   # file -> date downloaded
age = lambda name: (today - dt.date.fromisoformat(fetched[name])).days if name in fetched else 10 ** 6

# ---- tickets, a month at a time ----
start = (pd.Timestamp(today) - WINDOW).date().replace(day=1)
for old in tdir.glob("*.csv"):
    if old.stem < f"{start:%Y-%m}":
        old.unlink()
        fetched.pop(f"tickets/{old.name}", None)
window = list(months(start, today))
recent = {m for m, _ in window[-2:]}
due = recent | set(sorted((m for m, _ in window if m not in recent), key=lambda m: -age(f"tickets/{m:%Y-%m}.csv"))[:ROLL])


def month_fetcher(m, nxt):
    def fetch(path):
        body = get(TICKETS, {"$select": COLS, "$where": f'issue_date >= "{m}" and issue_date < "{nxt}"',
                             "$order": "issue_date", "$limit": "2000000"})
        write(path, body)
        return f"{path.name} {body.count(NL) - 1} tickets"
    return fetch


for m, nxt in window:
    name = f"tickets/{m:%Y-%m}.csv"
    if (CITY / name).exists() and m not in due:
        continue
    refresh(name, month_fetcher(m, nxt))


# ---- street centerlines, 1,000 per request ----
def fetch_streets(path):
    feats, off = [], 0
    while True:
        page = get_json(STREETS, {"where": "1=1", "outFields": FIELDS, "outSR": "4326", "orderByFields": "OBJECTID",
                                  "resultOffset": off, "resultRecordCount": 1000, "f": "geojson"}, timeout=120)
        feats += page["features"]
        off += len(page["features"])
        if not page["features"] or not (page.get("exceededTransferLimit") or page.get("properties", {}).get("exceededTransferLimit")):
            break
    write(path, json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")).encode())
    return f"centerlines.json {len(feats)} segments"


if age("centerlines.json") >= STREETS_DAYS or not (CITY / "centerlines.json").exists():
    refresh("centerlines.json", fetch_streets)
else:
    print(f"centerlines.json: keeping the copy from {fetched['centerlines.json']}")


# ---- metered spaces ----
def fetch_meters(path):
    body = get("https://data.lacity.org/resource/s49e-q6j2.csv",
               {"$select": "spaceid,blockface,metertype,ratetype,raterange,timelimit,latlng", "$order": "spaceid", "$limit": "100000"}, timeout=120)
    write(path, body)
    return f"meters.csv {body.count(NL) - 1} spaces"


refresh("meters.csv", fetch_meters)


# ---- posted sweeping routes: day, week pair, posted time and area ----
def fetch_routes(path):
    routes = get_json("https://services1.arcgis.com/PTh9WC0Sf2WS7AAq/arcgis/rest/services/Posted_Street_Sweeping_Routes_Update/FeatureServer/0/query",
                      {"where": "1=1", "outFields": "Route,Posted_Time,Posted_Day,Weeks", "returnGeometry": "true", "outSR": "4326", "f": "geojson"}, timeout=120)
    write(path, json.dumps(routes, separators=(",", ":")).encode())
    return f"sweep_routes.geojson {len(routes['features'])} posted sweeping route days"   # an ArcGIS error is a 200 with no features


refresh("sweep_routes.geojson", fetch_routes)
MANIFEST.write_text(json.dumps(fetched, indent=1, sort_keys=True))
if missing:
    sys.exit(f"stopping: no copy of {', '.join(missing)}; the rest is downloaded and kept for the next run")
