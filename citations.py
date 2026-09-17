"""Shared loading, geometry and calendar helpers for the USC ticket analysis."""
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
CSV = DATA / "citations_usc.csv"
METERS = DATA / "meters_usc.csv"
ROUTES = DATA / "sweep_routes.geojson"

# The study area: a 2.5 x 2.5 km box around USC's University Park campus
BOX = dict(s=34.012, n=34.035, w=-118.300, e=-118.272)
ZOOM, TILE = 16, 256

# Patterns use the two years up to the newest ticket, so they describe how enforcement works now
WINDOW = pd.DateOffset(years=2)

# USC class periods (from the academic calendar), spring break removed. Add each new
# semester once USC posts it; analyze.py warns when the newest ticket is past the last one.
TERMS = [("2024-08-26", "2024-12-06"), ("2025-01-13", "2025-03-14"), ("2025-03-24", "2025-05-02"),
         ("2025-08-25", "2025-12-05"), ("2026-01-12", "2026-03-13"), ("2026-03-23", "2026-05-01"),
         ("2026-08-24", "2026-12-04"), ("2027-01-11", "2027-03-12"), ("2027-03-22", "2027-04-30"),
         ("2027-08-23", "2027-12-03")]

SUFFIX = {"AV": "AVE", "AVENUE": "AVE", "BL": "BLVD", "BLV": "BLVD", "BOULEVARD": "BLVD",
          "STREET": "ST", "PLACE": "PL", "DRIVE": "DR", "WY": "WAY"}
SUFFIXES = {"ST", "AVE", "BLVD", "PL", "DR", "WAY", "CT", "LN", "RD", "TER", "WALK", "PARK", "SQ"}
DIRS = {"N", "S", "E", "W", "NORTH", "SOUTH", "EAST", "WEST", "REAR", "OF"}
ADDR = re.compile(r"(\d{2,5})\s+(.+)")
METER = "8813B"  # code 88.13B; some handhelds write it without dots (8813B+)


def parse_loc(s):
    """'3601 VERMONT AV S' -> (3601, 'VERMONT AVE'); intersections and blanks -> (None, None).

    East addresses keep an 'E ' prefix: 101 E 35th St is across Main St from 101 W 35th St,
    on a different sweeping route.
    """
    if not isinstance(s, str):
        return None, None
    m = ADDR.search(s.upper())
    if not m:
        return None, None
    raw = re.split(r"[\s.]+", m.group(2))
    toks = [SUFFIX.get(t, t) for t in raw if t and t not in DIRS]
    east = "E " if {"E", "EAST"} & set(raw) else ""
    return (int(m.group(1)), east + " ".join(toks)) if toks else (None, None)


def canonical_streets(streets):
    """Fold spelling variants into the common form: 'FIGUEROA' -> 'FIGUEROA ST', '32' -> '32ND ST'."""
    counts = streets.value_counts()
    full = [s for s in counts.index if s.split()[-1] in SUFFIXES]
    fix = {}
    for s in counts.index:
        if s.split()[-1] in SUFFIXES:
            continue
        if re.fullmatch(r"\d+", s):
            cands = [f for f in full if re.match(rf"^{s}(ST|ND|RD|TH) ", f)]
        else:
            cands = [f for f in full if f.startswith(s + " ") and len(f.split()) == len(s.split()) + 1]
        if cands:
            fix[s] = max(cands, key=lambda f: counts[f])
    return streets.map(lambda s: fix.get(s, s))


def nice_street(s):
    t = s.title()
    t = re.sub(r"(\d)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), t)
    return re.sub(r"\bMc(\w)", lambda m: "Mc" + m.group(1).upper(), t)


def load(path=CSV):
    d = pd.read_csv(path, dtype=str)
    d["date"] = pd.to_datetime(d.issue_date.str[:10])
    d = d[(d.date >= "2014-01-01") & (d.date <= pd.Timestamp.today().normalize())].copy()
    t = pd.to_numeric(d.issue_time, errors="coerce")
    d = d[t.notna() & (t % 100 < 60) & (t < 2400)].copy()
    t = t.loc[d.index].astype(int)
    d["mins"] = (t // 100) * 60 + t % 100
    d["ts"] = d.date + pd.to_timedelta(d.mins, unit="m")
    d["dow"] = d.date.dt.dayofweek
    parsed = d.location.map(parse_loc)
    d["num"] = parsed.str[0]
    d["street"] = parsed.str[1]
    ok = d.street.notna()
    d.loc[ok, "street"] = canonical_streets(d.loc[ok, "street"])
    d["block"] = (d.num // 100 * 100).astype("Int64")
    d["side"] = np.where(d.num % 2 == 0, "even", "odd")
    d["lat"] = pd.to_numeric(d.loc_lat, errors="coerce")
    d["lon"] = pd.to_numeric(d.loc_long, errors="coerce")
    d["tno"] = pd.to_numeric(d.ticket_number, errors="coerce")
    d["fine"] = pd.to_numeric(d.fine_amount, errors="coerce")
    d["viol"] = d.violation_description.fillna("?").str.strip()
    d["meter"] = d.violation_code.fillna("").str.replace(".", "", regex=False).str.startswith(METER)
    return d


def end_date(d):
    """Last day with a normal day's worth of tickets (the feed has a few stray future dates)."""
    per_day = d.groupby("date").size()
    return per_day[per_day >= 20].index.max()


def holidays(start, end):
    h = set(USFederalHolidayCalendar().holidays(start, end))
    for y in range(start.year, end.year + 1):
        tg = pd.Timestamp(f"{y}-11-01") + pd.offsets.WeekOfMonth(week=3, weekday=3)
        h |= {tg, tg + pd.Timedelta(days=1), pd.Timestamp(f"{y}-03-31"), pd.Timestamp(f"{y}-12-24")}
    return h


def in_term(dates):
    dates = pd.Series(dates)
    s = pd.Series(False, index=dates.index)
    for a, b in TERMS:
        s |= (dates >= a) & (dates <= b)
    return s.values


# ---- StreetsLA's posted sweeping routes ----
DAYNUM = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}


def clock(s):
    """'6:30 am' -> 390 minutes after midnight."""
    m = re.fullmatch(r"(\d{1,2})(?::(\d\d))?\s*([ap])m", s.strip().lower())
    return (int(m[1]) % 12 + 12 * (m[3] == "p")) * 60 + int(m[2] or 0)


def load_routes(path=ROUTES):
    """One dict per route day: route, dow, on (1 = 1st & 3rd weeks, 2 = 2nd & 4th), posted
    window s0-s1 in minutes, and the polygon rings (lon, lat) of the area it covers."""
    out = []
    for f in json.loads(path.read_text())["features"]:
        p, geom = f["properties"], f["geometry"]
        parts = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        start, end = p["Posted_Time"].split("-")
        out.append(dict(route=p["Route"].split()[0], dow=DAYNUM[p["Posted_Day"]], on={"1 & 3": 1, "2 & 4": 2}[p["Weeks"]],
                        s0=clock(start), s1=clock(end), rings=[np.asarray(r, float) for q in parts for r in q]))
    return out


def inside(lon, lat, rings):
    """Which points fall inside a polygon. Even-odd rule over every ring, so holes and
    multi-part areas need no special case; points outside a ring's bounding box can't flip it."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    hit = np.zeros(len(lon), bool)
    for r in rings:
        lo, hi = r.min(0), r.max(0)
        k = np.flatnonzero((lon >= lo[0]) & (lon <= hi[0]) & (lat >= lo[1]) & (lat <= hi[1]))
        if not len(k):
            continue
        x, y = lon[k], lat[k]
        for (x1, y1), (x2, y2) in zip(r, np.roll(r, -1, axis=0)):
            if y1 != y2:
                hit[k] ^= ((y1 > y) != (y2 > y)) & (x < x1 + (x2 - x1) * (y - y1) / (y2 - y1))
    return hit


# ---- Web Mercator pixels on the basemap (same projection as the OSM tiles) ----
def deg2num(lat, lon, z=ZOOM):
    n = 2 ** z
    x = (np.asarray(lon) + 180.0) / 360.0 * n
    lr = np.radians(np.asarray(lat))
    y = (1.0 - np.log(np.tan(lr) + 1 / np.cos(lr)) / math.pi) / 2.0 * n
    return x, y


def frame():
    x0, y0 = deg2num(BOX["n"], BOX["w"])
    x1, y1 = deg2num(BOX["s"], BOX["e"])
    return dict(x0=float(x0) * TILE, y0=float(y0) * TILE,
                W=int(round((float(x1) - float(x0)) * TILE)), H=int(round((float(y1) - float(y0)) * TILE)),
                m_per_px=156543.03392 * math.cos(math.radians((BOX["n"] + BOX["s"]) / 2)) / 2 ** ZOOM)


def to_px(lat, lon):
    f = frame()
    x, y = deg2num(lat, lon)
    return x * TILE - f["x0"], y * TILE - f["y0"]
