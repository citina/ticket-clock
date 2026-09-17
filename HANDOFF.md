# Handoff: USC Ticket Clock

Live: https://citina.github.io/ticket-clock/ · Repo: https://github.com/citina/ticket-clock (public, `main`)
Companion site: Curb Log (citina/curb-log). The masthead reads "Curb Log · Citations"; keep the family look.
State as of 2026-09-16: the USC page with StreetsLA posted routes and the 760px text width (see
VISUAL_CHANGES.md), plus LA Street Rules, described at the end.

Two pages now: the USC Ticket Clock (`docs/index.html`, built from `template.html`) and **LA Street
Rules** (`docs/streets/`), the city-wide "rules for my street" page that grew out of the planned
"near me" tab. Visual candidates for the USC page are listed near the end.

## How the page is built

- **For visual work, edit only `template.html`.** `build.py` (8 lines) fills `__DATA__` with
  `data/bundle.json` and `__BASEMAP__` with `docs/basemap.jpg` (base64), writing `docs/index.html`,
  one self-contained file of about 890 KB. Never hand-edit `docs/index.html`.
- Opening `template.html` directly shows no map and no numbers: the placeholders aren't filled yet.
  That's expected. Always look at the built `docs/index.html`.
- After a template change run `./build.py` only. Visual work doesn't need `analyze.py`. If you do
  rerun it, run `./fetch_citations.py` first (~45 MB), or the commit rolls the site back behind the
  weekly bot's data.
- Local Python is 3.9 with pandas 1.3.4, numpy 1.26.4 and scipy 1.12.0. CI pins the same versions.
- A weekly bot (`.github/workflows/weekly.yml`, Mondays 14:17 UTC) commits `data/bundle.json` and
  `docs/index.html`. **Run `git pull` before starting.** It stops without publishing if the ticket
  count drops more than 1%.
- Deploy: a push to `main` touching `docs/` runs `pages.yml`; the site is live in about a minute.
  Check with `gh run list --workflow pages.yml -L1`.

## Previewing

- The in-app browser can't open `file://`. Serve `docs/` over localhost: create `.claude/launch.json`
  with a `python3 -m http.server 8765 --directory docs` config, `preview_start` it, and delete the
  file when done (it isn't committed).
- Editing `template.html` makes the Browser pane open the raw template in its own tab. Pin every
  browser call to the tab serving localhost (`tabId`), or the checks run against the empty template.
- Screenshots fail while the Browser pane is hidden, and a hidden page also freezes timers, so a
  resize won't redraw the charts. DOM checks via `javascript_tool` still work; reload instead of
  resizing to test a width.
- Region zoom isn't supported. To inspect detail, scale the page with a CSS transform on
  `document.documentElement`. The first screenshot after a reload or a big scroll often comes back
  blank; take it twice.
- Deep links select a block: `#1100-36TH-PL` (two sweep sides), `#3600-VERMONT-AVE` (metered, long
  chip row), `#500-28TH-ST` (longest panel). The navigate tool can drop the hash; set
  `location.hash` and reload.
- Check light and dark (`resize_window` `colorScheme`), 1440 / 900 / 375 widths, and the console.
  The explorer stacks under 1000px; summary rows and the method list stack under 560px.

## Page map (`template.html`, 723 lines)

| Lines | What |
|---|---|
| 1–6 | charset, **viewport meta** (phones need it), title, fonts |
| 8–43 | Color tokens: light on `:root`, dark under `prefers-color-scheme` (guarded) **and** `[data-theme="dark"]`. Keep all three in sync. |
| 44–98 | Base CSS: body, `--measure`, `.intro`, `.lede-note`, `.note`, headings, chips, legend |
| 99–167 | Explorer, map, panel, sign, meter heat, odds |
| 168–207 | Verdict (summary cards), heatmap, method, tooltip |
| 209–240 | `<main>`: masthead, `.intro` (title, lede, `.lede-note` pitch), explorer |
| 240–331 | Sections: `#answers`, `#sweep`, `#meters`, `#method` + footer sources |
| 337–371 | Helpers: `S`/`T`/`H`, time and date formatting, tooltip, meter maths |
| 377–496 | Map: SVG over the basemap, layers gHalo/gBase/gCol/gSel/gHit. `drawColor` 410, `drawSel` 438, pan/zoom 445, `focusBlock` 469, `sizeMap` 474, `revealPanel` 480, search 486 |
| 497–645 | Panel: `insights` 502, `signHTML` 522, `arrivalStrip` 530, `meterCard` 554, `select` 600 |
| 647–722 | Summary text 647, `drawCal` 665, `drawLag` 684, meter heatmap 704, resize redraw 717 |

Fonts: Barlow for body, Barlow Condensed for h1/h2 and the sign, IBM Plex Mono for eyebrows and
ticks (Google Fonts).

## Layout (chosen 2026-09-13)

One 1240px grid for the whole page. `main` is `max-width:1280px`; `.explorer` is
`minmax(0,1fr) 430px` (map, then panel), with the title, lede and pitch above it. Sections below
share that left edge. Blocks of text share one width, `--measure` (760px); the Sources list and the
closing "Not a guide" note span the full width. Charts fill the width, and the three
summary answers become cards in a row above 1000px. Under 1000px everything stacks and the map is
capped at 72% of the screen height; tapping a block scrolls the panel title into view.

Charts are drawn at their container's real width (`arrivalStrip`, `drawLag`, `drawCal`, the odds
chart) and redraw on width changes, so text never scales down. Stacked-layout grid columns must stay
`minmax(0,1fr)`: a plain `1fr` lets a long chip row widen the whole page on phones.

## Color rules (validated, don't change casually)

- Sweeping day colors: Tue `--s1` blue, Wed `--s2` orange, Thu `--s3` aqua, Fri `--s4` violet
  (`#4a3aa7` light / `#6247cc` dark), checked with the dataviz skill's
  `scripts/validate_palette.js --pairs all` in both modes. Only violet passed as a 4th color and no
  5th passes on a map, so a Monday would need a dash pattern, not a new color. Rerun the validator
  before touching these.
- Grey (`--ink-3`) means "no sweeping schedule found". Dotted blue (`--accent-ink`) means a metered
  block the current view has nothing else to show for. No weekday may be grey again.
- Meter mode uses a sequential accent-blue scale by officer visits per weekday.
- Selection halos draw **under** the colored lines (`gHalo` before `gCol`) so a selected block keeps
  its own colors. In dark mode the basemap is inverted with `--map-filter` (Safari ignores CSS filters
  on elements inside an SVG, so on iPhones it stays light; LA Street Rules keeps its map light on
  purpose, see below).

## Decisions Citina made (keep them)

- The "Rebuilding officer patrols" section and the two-officer route map were removed on purpose.
- No copy implying a time is safe from tickets ("gap at 3 pm", "3 pm quiet hour" were removed).
  **But keep** the per-block "The quietest stretch is …" line.
- The disclaimer stays small and unobtrusive (12.5px, `--ink-3`, no border). Since 2026-09-16
  "Not a guide to parking illegally" is the last thing on the page (`.note.end`), and "Street
  sweeping signs" is an `.aside` after the sweeping section's opening paragraph. Under the lede, the
  `.lede-note` pitch says signs often leave out the week.
- Places in plain language: "Vermont Ave from W 36th St down to about W 37th St (both sides)", never
  "Vermont 36xx". Curb Log measures "available parking", not "free parking".
- Search and the block buttons never zoom; they pan only if the block is off-screen, and searching a
  street name outlines all its blocks.
- Legend wording is "no sweeping schedule found" / "metered, no sweeping schedule found", plus the
  explanatory note. Section eyebrows show the ticket code as "Ticket code · …". "Updated weekly"
  appears in the masthead and the method section.
- The arrival strip has two lanes: first ticket (blue) and last ticket (orange), one dot per sweep day.

## The sweeping-sign story (checked 2026-09-13)

LA has swept every other week since March 2021, but ~75,000 signs still show only the weekday.
LADOT says parking is legal on a street's off weeks
([Larchmont Chronicle, Mar 2025](https://larchmontchronicle.com/to-adhere-to-parking-signs-or-not-to-adhere/)),
and its [weekly update of March 4, 2021](https://ladot.lacity.gov/dotnews/weekly-update-march-4-2021)
said officers would enforce sweeping only on days sweeping happens. On 2026-09-16 Citina had the
pages stop saying off-week tickets still get written (and dropped the L.A. Material source), so
don't bring that back. Our own data agrees: a side is ticketed on 39.6% of its scheduled days,
1.05% of its other-week days, and 0% of 5th-week days. Signs won't change until the City Council
makes the schedule permanent. Both pages' "Street sweeping signs" note and the README say this.

## Open visual candidates (not requests)

Ranked roughly by payoff:

1. The block panel is long (36th Pl 1,694px; 28th St 2,464px). Collapse the sweeping card to one
   line when there's no schedule, drop the per-day pass list under the meter heat grid (it restates
   the grid), label the stay chips ("30 min / 1 hr / 2 hr" wraps to an unlabeled row).
2. "What gets ticketed here": the count sits top-right while its bar starts at the left of a 110px
   column, so small counts read as a stray dot. Put bar and count on one line.
3. On phones the map's two bottom labels overlap ("drag to move · pinch or ⌘/ctrl-scroll to zoom"
   runs under the OpenStreetMap credit). Shorten or hide it under 560px; the zoom buttons could shrink.
4. Meter mode: the light end of the blue scale nearly vanishes on the light basemap; the "no meters"
   legend swatch is a thick grey bar while those streets are thin faint lines. In dark mode the
   metered dots are the brightest thing on the map.
5. The third summary stat ("3 meter waves a day") is weaker than the other two.
6. The legend note under the map runs 2–3 lines.
7. The `.code` eyebrow's explanation lives in a `title` tooltip, invisible on touch.

## LA Street Rules (`docs/streets/`)

Decisions Citina made on 2026-09-16 (keep them unless she asks):

- **Its own page**, not a tab on the USC page, so the USC page stays clean. The USC masthead has one
  small "LA Street Rules" link; the streets page links back the same way.
- **The whole City of Los Angeles**, a rolling two years of tickets (same window as the USC page).
- **Sweeping schedule from StreetsLA's posted routes, the same rule as the USC page** (asked for on
  2026-09-16): day, weeks and posted time from the route; tickets only decide which side gets which
  route day. `load_routes(..., weekly=True)` also reads the every-week routes the USC box doesn't
  have (Downtown "DT 1–4" Monday to Friday 1–4 am, Skid Row); "Adams Bl" ("As Available") is left
  out. The layer's `Odd_Even` field is the week pair (Odd = 1st & 3rd), not the side of the street.
- **Location only moves the map** (no accuracy matching or pick lists): it centers an ~800 m view on
  the reader, who taps their block. No precise location is needed.
- **Map images load live from OpenStreetMap** (tile.openstreetmap.org), faded like the USC basemap.
  **The map stays light in dark mode** (asked for on 2026-09-17, after seeing the USC map stay light on
  an iPhone): its background, block lines and halo use `--map-*` tokens that dark mode doesn't
  override, and the legend's line swatches sit on a bit of that light background. Bulk-downloading tiles for the city is against OSM's policy, so the
  page only requests what's in view. The disclaimer's "What the page loads" part says OSM and GitHub
  can tell roughly which area a reader looks at.
- **City data is published as the `city-data` release**, overwritten weekly, not committed.
- **The block card** (2026-09-17): the sign carries the posted rule, so a side shows only its name and
  the next two sweep dates in bold. The meter card is spaces, officer visits a weekday and the
  six-day unpaid odds (the meter ticket count lives in the kinds list). "What gets ticketed here"
  lists every kind like the USC card (8 shown, "Show all N kinds" / "Show fewer"), under a dot chart
  of the block's most ticketed kind by half hour (grey band = posted sweeping time when that kind is
  street cleaning). Each kind is a button: it opens a plain line about the rule
  (`KIND_NOTES` in citations.py -> `kind_note`), every code LADOT writes it under with their own
  wordings (`kind_src`: 6 codes and 3 wordings at most, then "and N more"), and, for kinds with
  `chart_min` (50) tickets on the block, its own dot chart (`hh` holds one entry per charted kind).
  A mouse also gets the name, the line and the first code as a tooltip.

How it works:

- `fetch_city.py` → `data/city/` (gitignored): monthly ticket CSVs for the window (old months are
  deleted, the last two refetched), LA GeoHub street centerlines (`Street_Information/MapServer/36`,
  85k segments with address ranges per side and intersection IDs), LADOT's meter inventory, and
  StreetsLA's posted sweeping routes for the whole city (~870 route days, 36 MB).
- `analyze_city.py` (~5 min) → `docs/streets/data/` (gitignored, ~16 MB, 4.3 MB as the release
  tarball): tickets are matched to a centerline segment by street name, direction, suffix and house
  number (88% of tickets; intersections and unaddressable places like LAX's World Way are left out).
  A block is street + hundred block, split where a name repeats elsewhere (IDs then get the ZIP, e.g.
  `#100-W-1ST-ST-90012`). Its line is cut from the segments by address; cross streets come from the
  intersections at its ends; the centerline ranges give the compass side of the even numbers.
  Output: `index.json` (dates, counts, street names, ticket kinds, which cells exist; ~46 KB
  gzipped, loads with the page), `streets.json` (each street's blocks; ~98 KB, loads on search),
  `cells/<x>_<y>.json` (blocks in ~1 km zoom-17 Web Mercator cells, loaded as the map shows them,
  only when the view is under 3 km wide). It stops if a month in the window came back thin.
- `citations.py` now also holds `LABELS`, `SWEEP`, `compass` and `usual_hours`, shared by both
  analyses (moved from `analyze.py`; the USC bundle was checked byte-identical after the move).
- Ticket kinds on both pages are named by violation code (`CODE_KINDS` and `kind_label` in
  `citations.py`), because the handhelds spell one rule many ways ("STANDNG IN ALLEY",
  "OVNIGHT PRK W/OUT PE"); `LABELS` by description is only the fallback. All no-stopping
  codes are "No stopping": their AM/PM descriptions don't match when they're written. A new code
  shows LADOT's own description until it's added to the table. Each block lists every kind, and
  `hh` holds its most ticketed kind by half hour for the card's dot chart.
- `docs/streets/index.html` is hand-written, no build step. Deep links: `#3600-S-VERMONT-AVE`.
- `weekly.yml`: jobs `update` (USC, as before), `city` (fetch, analyze, check the count hasn't fallen
  >10%, upload to the `city-data` release) and `deploy` (starts `pages.yml` even if one job failed).
  `pages.yml` downloads the release into `docs/streets/data/` before publishing; if the release is
  missing it warns and the page says its data didn't load.
- The `city-data` release was first uploaded by hand on 2026-09-16 (tickets through 2026-09-14). If
  it's ever deleted, run `gh workflow run weekly.yml` to rebuild it.

Previewing: run `./fetch_city.py` and `./analyze_city.py`, serve `docs/`, open `/streets/`.

Known gaps: tickets written at intersections (7.6%) aren't shown; about 5% of blocks name no cross
street; the meter card has no posted meter hours (LADOT's data doesn't include them) and uses all
weeks, not USC class weeks, so 3600 S Vermont's odds differ a little between the two pages. A side with
fewer than 8 sweeping tickets shows no schedule even inside a posted route, as on the USC page, and
then the card lists the posted route days around the block (`wr` in the cell data: points 6 m off each
side of the middle of each piece of its line, tested against every route area) without saying which
side gets which, or says no posted route covers it. `index.json`'s `routes_around` tells the page the
data has `wr`; older data falls back to the ticket-only "No sweeping schedule found" text.

## Committing

Commit `template.html` and `docs/index.html`, plus `README.md` if touched. For LA Street Rules, commit
`docs/streets/index.html` and the scripts; its data is never committed (the release carries it). End commit messages with
the Co-Authored-By line. Pushing deploys the site through `pages.yml`. This handoff is committed at
the repo root; update it when the state above changes.
