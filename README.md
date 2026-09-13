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

A companion to [Curb Log](https://citina.github.io/curb-log/), which uses
LADOT's sensors to measure available parking on Vermont Ave from W 36th St down to about
W 37th St (both sides), and on W 36th St just west of Vermont.

## Disclaimer

This project is not meant to encourage anyone to break parking rules or park
illegally. It shows when and where LADOT has written tickets, so the rules on each
block, and how they're enforced, are easier to understand. Past tickets don't
predict the next one: an officer can come by at any time, and a quiet hour in the
data can still end in a ticket.

**Street sweeping signs.** LA has swept each street every other week since March 2021
(the 1st & 3rd or the 2nd & 4th time its weekday comes up in a month), but many signs
were never updated and still show only the day, like "No parking Thursday". LADOT says
parking is legal on a street's off weeks and that it doesn't ticket then
([Larchmont Chronicle, March 2025](https://larchmontchronicle.com/to-adhere-to-parking-signs-or-not-to-adhere/)).
Some tickets are still written on off weeks
([L.A. Material, July 2026](https://lamaterial.com/p/la-wrongful-street-sweeping-tickets)),
and LADOT says it dismisses those. The weeks this project shows are worked out from
the tickets themselves (about 98% of sweeping tickets near campus fall on them), so
they're evidence, not the official schedule. For that, look up your street at
[streets.lacity.gov](https://streets.lacity.gov/services/street-sweeping).

## Run it

```
./fetch_citations.py   # data/citations_usc.csv (~45 MB, data.lacity.org 4f5p-udkv) and data/meters_usc.csv (meter inventory, s49e-q6j2)
./basemap.py           # docs/basemap.jpg (36 OpenStreetMap tiles at zoom 16, cached in .tilecache/)
./analyze.py           # data/bundle.json (every number the page shows)
./build.py             # docs/index.html (one self-contained file)
```

Python 3 with pandas, numpy, scipy and Pillow. The raw downloads and the tile cache
are not committed; they regenerate from the commands above.

## Weekly update

`.github/workflows/weekly.yml` reruns fetch, analyze and build every Monday on GitHub
Actions, commits the new `data/bundle.json` and `docs/index.html`, and starts
`pages.yml` to publish `docs/`. Run it by hand with `gh workflow run weekly.yml`. If
the ticket count falls more than 1% from the last build, it stops without publishing.
USC term dates in `citations.py` run through fall 2027; the run log warns once the
newest ticket is past them.

| File | What it is |
|---|---|
| `citations.py` | shared loading: address parsing, street-name cleanup, holidays, USC term dates, map projection |
| `analyze.py` | per-block geometry, sweeping schedule per side, meter visit rates, campus charts |
| `template.html` | the page; `build.py` fills in the data and the basemap |

## Method in brief

- **Window.** Patterns use the two years up to the newest ticket (a rolling window),
  so they describe how enforcement works now.
- **Blocks.** Hundred block of each address; odd and even numbers are the two sides.
  A block's map line is fitted through its ticket locations. Where the two sides
  geocode to clearly opposite sides of it (13 blocks), the page names the compass side.
- **Sweeping.** Street-cleaning tickets are code 80.69BS (a few handhelds write it
  8069BS; both count). A block side needs 8 of them in the window to get a schedule;
  the map calls the rest "no sweeping schedule found". LA sweeps every other week since March 2021 (1st & 3rd or 2nd & 4th
  weekday of the month). Per side: posted day = most common ticket weekday; window
  = the hour of the earliest 5% of tickets, 2 hours long; phase = whichever week pair
  holds more tickets (98% of sweeping tickets match). "Ticketed on X% of sweep days"
  excludes holidays and days with no sweeping tickets anywhere nearby.
- **Metered blocks.** From LADOT's meter inventory, so blocks whose meters never drew
  a ticket still count (tickets alone miss 3800 Figueroa and 2600 Vermont). On the
  map they're dotted where the current view has nothing else to show for them.
- **Meters.** USC class weeks, Monday–Saturday, 8 am–8 pm. A visit = meter tickets on
  one block with gaps ≤ 10 min. A visit that finds every meter paid leaves no trace,
  so the visit rate is scaled up assuming expired cars per visit are Poisson (the mean
  tickets per visible visit gives the share of empty visits). "At least" figures skip
  that correction.

A ticket needs a violator, so quiet blocks look less patrolled than they are. None
of this replaces the posted sign.

Data: LADOT Parking Citations, data.lacity.org. Basemap © OpenStreetMap contributors.
