# Visual changes to carry over to LA Street Rules

For the session building **LA Street Rules** (`docs/streets/index.html`, worktree
`.claude/worktrees/street-parking-rules-tab-7553df`). Read this once that page is done.

Citina is tuning the look of the USC Ticket Clock page (`template.html` on `main`) and wants the same
changes on LA Street Rules where they fit. Each entry below says what changed on the USC page, why,
and whether it applies to LA Street Rules. Started 2026-09-16 on `main` at `d8ac370`.

## How to use this

- Port entries marked **Applies: yes**. For **maybe**, ask Citina first. Skip **USC only**.
- The commit named in each entry shows the exact edit: `git show <commit> -- template.html`.
- Both pages share the color tokens (light `:root`, dark `prefers-color-scheme`, and
  `[data-theme="dark"]`; keep all three in sync), the fonts (Barlow, Barlow Condensed, IBM Plex Mono)
  and these class names, so a change to one of them usually ports as-is:
  `#tip .card .chip .code .explorer .hit .intro .k .kv .lede .legend .mapcol .maptag .mapwrap .mast
  .meta .method .n .nm .note .p-eyebrow .p-sub .p-title .panel .s1–.s5 .side .side-head .side-name
  .side-txt .sign .sign-in .sw .v .zoom`.
  Classes that exist on only one page need a look by eye:
  - USC only: `.verdict` cards, `#cal`, `.heat`/`.mheat`, `.odds-ctl`, `.chips`, `.insights`, `.passes`,
    `.basemap`, `.mapbar`, `.p-nav`, `.fig-title`/`.fig-sub`
  - LA Street Rules only: `.findbar`, `.searchbox`, `.sugg`, `.locbtn`, `.cands`, `.tiles`, `.also`,
    `.evid`, `.rule-line`, `.odds6`, `.blk`
- The wording rules still hold on both pages: no copy implying a time is safe from tickets, places in
  plain language, the disclaimer small and quiet.
- When an entry has been ported, add "Ported to LA Street Rules" and the commit under it.

## Changes

HANDOFF.md still describes the disclaimer as two parts at the top and cites L.A. Material. Changes 1
and 5 below replace that, so update HANDOFF.md to match when you merge.

### 1. "Street sweeping signs": LADOT's own source, no "tickets still get written"

Commit: `97ae462` · Applies: **yes**

- Removed "a few tickets still get written, and LADOT says it dismisses those." Citina doesn't want
  the page to say that.
- Added LADOT's own announcement of the change. Its March 4, 2021 weekly update says officers "will
  enforce street sweeping only on days that sweeping occurs" (checked 2026-09-16). The sentence now
  reads: `LADOT says parking is legal on a street's off weeks, and when the change began it said
  officers would enforce street sweeping only on days that sweeping happens (<a
  href="https://ladot.lacity.gov/dotnews/weekly-update-march-4-2021">LADOT, March 2021</a>).`
- "StreetsLA's list" is now a link to the routes layer
  (`https://www.arcgis.com/home/item.html?id=0e16fa641a0846a3ae29bffb150314dc`), both in the intro
  and in the footnote under the sign in the block panel.
- Sources: the L.A. Material item is gone, since nothing on the page cites it now. LADOT's March 4,
  2021 update sits next to Larchmont Chronicle instead. README.md's disclaimer got the same edits.
- On LA Street Rules: the same "Street sweeping signs." paragraph and the L.A. Material source are in
  `docs/streets/index.html`. Make the same LADOT edits there. Its schedule comes from tickets, not
  StreetsLA's list, so only add the StreetsLA link if that page starts using the routes layer.

### 2. Bullet dots under "Selected block" are black

Commit: `97ae462` · Applies: **yes**, to any colored bullet dots in its block panel

- `.insights li::before` background went from `var(--accent)` (blue) to `var(--ink)`, so the dots
  are black in light mode and white in dark mode.
- LA Street Rules has no `.insights` list, so this only matters if its panel has blue bullet dots.

### 3. Say where the number of sweep days comes from

Commit: `97ae462` · Applies: **yes**

- "Ticketed on 66% of 44 sweep days" was unclear about where 44 came from. It now reads "Ticketed on
  66% of sweep days in the past two years (44 days)".
- On LA Street Rules: "Tickets were written on X% of N sweep days here" should become the same kind
  of wording, e.g. "Tickets were written on X% of sweep days here in the past two years (N days)".

### 4. Arrival strip labels line up with the grey window

Commit: `97ae462` · Applies: **USC only for now**

- In `arrivalStrip`, the colored dot and its label start at the left edge of the grey posted-window
  band (`x(0)`) instead of the chart's left edge.
- The label still reads "First ticket: usually 12:51 pm" (Citina tried dropping "usually" and asked
  for it back).
- LA Street Rules has no arrival strip. Use this if it gets one.

### 5. "Not a guide to parking illegally" moved to the end of the page

Commit: `97ae462` · Applies: **yes**

- The paragraph is unchanged but now sits in `<div class="note end">`, the last thing in `<main>`,
  after the method section and its sources (`.note.end{margin-top:40px}`, same small grey style).
  The note at the top now holds only "Street sweeping signs".
- On LA Street Rules: move its "Not a guide to parking illegally." paragraph to the end of the page
  the same way. Ask Citina before moving its other disclaimer parts, such as "What the page loads".
