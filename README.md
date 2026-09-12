# USC Ticket Clock

When does parking enforcement come by the streets around USC? This project reads
every LADOT parking ticket written in a 2.5 × 2.5 km box around the University
Park campus (about 315k since 2014) and turns them into a clickable map. Pick a
block and it shows:

- **Street sweeping, per side:** the posted day and window, whether it's the
  1st & 3rd or 2nd & 4th week, how often a sweep day actually gets ticketed, when
  the officer's first ticket lands (one dot per sweep day), and the next posted dates.
- **Meter patrols (metered blocks):** the chance an officer walks by in each half
  hour of each weekday, the usual pass times, and the odds of a ticket if you
  never pay, by arrival time and length of stay.
- **Everything else ticketed there,** with the fine and the usual time of day.

Below the map: campus-wide evidence (every-other-week sweeping, officer arrival
times, meter waves).

A companion to [Curb Log](https://citina.github.io/curb-log/), which measures
free spaces on Vermont 36xx with LADOT's sensors.

## Run it

```
./fetch_citations.py   # data/citations_usc.csv (~45 MB, from data.lacity.org 4f5p-udkv)
./basemap.py           # docs/basemap.jpg (36 OpenStreetMap tiles at zoom 16, cached in .tilecache/)
./analyze.py           # data/bundle.json (every number the page shows)
./build.py             # docs/index.html (one self-contained file)
```

Python 3 with pandas, numpy, scipy and Pillow. The raw CSV and the tile cache are
not committed; both regenerate from the commands above.

| File | What it is |
|---|---|
| `citations.py` | shared loading: address parsing, street-name cleanup, holidays, USC term dates, map projection |
| `analyze.py` | per-block geometry, sweeping schedule per side, meter visit rates, campus charts |
| `template.html` | the page; `build.py` fills in the data and the basemap |

## Method in brief

- **Window.** Patterns use the last two years (from 1 Sep 2024), so they describe
  how enforcement works now.
- **Blocks.** Hundred block of each address; odd and even numbers are the two sides.
  A block's map line is fitted through its ticket locations. Where the two sides
  geocode to clearly opposite sides of it (13 blocks), the page names the compass side.
- **Sweeping.** LA sweeps every other week since March 2021 (1st & 3rd or 2nd & 4th
  weekday of the month). Per side: posted day = most common ticket weekday; window
  = the hour of the earliest 5% of tickets, 2 hours long; phase = whichever week pair
  holds more tickets (98% of sweeping tickets match). "Ticketed on X% of sweep days"
  excludes holidays and days with no sweeping tickets anywhere nearby.
- **Meters.** USC class weeks, Monday–Saturday, 8 am–8 pm. A visit = meter tickets on
  one block with gaps ≤ 10 min. A visit that finds every meter paid leaves no trace,
  so the visit rate is scaled up assuming expired cars per visit are Poisson (the mean
  tickets per visible visit gives the share of empty visits). "At least" figures skip
  that correction.

A ticket needs a violator, so quiet blocks look less patrolled than they are. None
of this replaces the posted sign.

Data: LADOT Parking Citations, data.lacity.org. Basemap © OpenStreetMap contributors.
