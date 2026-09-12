#!/usr/bin/env python3
"""Download every LADOT parking citation inside the study box to data/citations_usc.csv.

Source: data.lacity.org dataset 4f5p-udkv (Parking Citations), refreshed daily.
About 320k rows / 45 MB; one request, no key needed.
"""
import urllib.parse
import urllib.request

from citations import BOX, CSV, DATA

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
