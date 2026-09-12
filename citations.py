"""Shared loading, geometry and calendar helpers for the USC ticket analysis."""
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

# The study area: a 2.5 x 2.5 km box around USC's University Park campus
BOX = dict(s=34.012, n=34.035, w=-118.300, e=-118.272)
ZOOM, TILE = 16, 256

# Patterns use the last two years, so they describe how enforcement works now
START = pd.Timestamp("2024-09-01")

# USC class periods (approximate, from the academic calendar), spring break removed
TERMS = [("2024-08-26", "2024-12-06"), ("2025-01-13", "2025-03-14"), ("2025-03-24", "2025-05-02"),
         ("2025-08-25", "2025-12-05"), ("2026-01-12", "2026-03-13"), ("2026-03-23", "2026-05-01"),
         ("2026-08-24", "2026-12-04")]

SUFFIX = {"AV": "AVE", "AVENUE": "AVE", "BL": "BLVD", "BLV": "BLVD", "BOULEVARD": "BLVD",
          "STREET": "ST", "PLACE": "PL", "DRIVE": "DR", "WY": "WAY"}
SUFFIXES = {"ST", "AVE", "BLVD", "PL", "DR", "WAY", "CT", "LN", "RD", "TER", "WALK", "PARK", "SQ"}
DIRS = {"N", "S", "E", "W", "NORTH", "SOUTH", "EAST", "WEST", "REAR", "OF"}
ADDR = re.compile(r"(\d{2,5})\s+(.+)")
METER = "88.13B"


def parse_loc(s):
    """'3601 VERMONT AV S' -> (3601, 'VERMONT AVE'); intersections and blanks -> (None, None)."""
    if not isinstance(s, str):
        return None, None
    m = ADDR.search(s.upper())
    if not m:
        return None, None
    toks = [SUFFIX.get(t, t) for t in re.split(r"[\s.]+", m.group(2)) if t and t not in DIRS]
    return (int(m.group(1)), " ".join(toks)) if toks else (None, None)


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
    d["meter"] = d.violation_code.fillna("").str.startswith(METER)
    return d


def end_date(d):
    """Last day with a normal day's worth of tickets (the feed has a few stray future dates)."""
    per_day = d.groupby("date").size()
    return per_day[per_day >= 20].index.max()


def holidays(start=START, end=pd.Timestamp("2027-01-01")):
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
