#!/usr/bin/env python3
"""Every number the page shows: data/citations_usc.csv -> data/bundle.json.

Per block (street + hundred block): where it is on the map, which tickets it gets
and when; per side, the street-sweeping schedule; for metered blocks, how often
an officer walks by in each half hour of each weekday. Plus the campus-wide
charts. See README.md for the method.
"""
import json
import math

from scipy.optimize import brentq

from citations import *

MIN_TIX = 20          # a block needs this many tickets in the window to get a panel
SWEEP_MIN = 8         # sweeping tickets on one side before we infer its schedule
METER_MIN = 20        # meter tickets before we model a block's patrols
VISIT_GAP = 10        # minutes: meter tickets closer than this on one block = one officer visit
SEP_MIN, CONS_MIN = 4.0, 0.75  # metres / share: when odd and even addresses sit on clear sides
SLOT0, NSLOT = 8 * 60, 24      # half hours from 8:00 am to 8:00 pm (meter hours)

LABELS = {
    "NO PARK/STREET CLEAN": "Street cleaning", "RED ZONE": "Red zone", "NO STOP/STANDING": "No stopping",
    "NO STOP/STAND": "No stopping", "STOP/STAND PROHIBIT": "No stopping", "DISPLAY OF TABS": "Expired tabs",
    "NO PARKING": "No parking", "DISPLAY OF PLATES": "Missing plates", "BLOCKING DRIVEWAY": "Blocking driveway",
    "18 IN. CURB/2 WAY": "Too far from curb", "FIRE HYDRANT": "Fire hydrant", "DOUBLE PARKING": "Double parking",
    "STANDNG IN ALLEY": "Standing in alley", "STANDING IN ALLEY": "Standing in alley",
    "PARKED OVER TIME LIMIT": "Over time limit", "PARKED ON SIDEWALK": "On sidewalk",
    "YELLOW ZONE": "Loading zone", "PARKED IN BUS ZONE": "Bus zone", "PK IN BUS ZONE": "Bus zone",
    "NO STOP/STAND AM": "No stopping, AM rush", "NO STOP/STAND PM": "No stopping, PM rush",
    "NO EVIDENCE OF REG": "No registration", "CARSHARE PARKING": "Car-share space", "WHITE ZONE": "Passenger zone",
    "PREFERENTIAL PARKING": "Permit district", "PREF PARKING": "Permit district", "COMM VEH OVER TIME LIMIT": "Commercial over limit",
    "EXCEED 72HRS-ST": "Parked over 72 hours", "OVERNIGHT PARKING": "Overnight parking", "HANDICAP/NO PLACARD": "Disabled space",
    "PARKED IN CROSSWALK": "In crosswalk", "WITHIN 15FT OF HYDRANT": "Fire hydrant", "LOADING ZONE": "Loading zone",
}

d = load()
END = end_date(d)
F = frame()
MPP = F["m_per_px"]
d["x"], d["y"] = to_px(d.lat.values, d.lon.values)
d["kind"] = np.where(d.meter, "Meter expired", d.viol.map(lambda v: LABELS.get(v, v.capitalize())))
START = END - WINDOW + pd.Timedelta(days=1)
w = d[(d.date >= START) & (d.date <= END)].copy()
hol = holidays(START, END)
if END > pd.Timestamp(TERMS[-1][1]):
    print(f"warning: USC term dates in citations.py stop at {TERMS[-1][1]}; add the next semester or meter stats lose class weeks")
print(f"{len(d):,} tickets; window {START.date()} to {END.date()}: {len(w):,}")


def compass(vx, vy):
    """Direction of a pixel-space vector (+x east, +y south) as one of 8 compass words."""
    ang = (math.degrees(math.atan2(-vy, vx)) + 360) % 360
    return ["east", "northeast", "north", "northwest", "west", "southwest", "south", "southeast"][int((ang + 22.5) // 45) % 8]


def usual_hours(mins, share=.5):
    """Clock-hour ranges holding the busiest `share` of tickets, as [[start, end], ...] in minutes.

    One quartile range misleads when tickets come at two times of day (fire hydrant:
    1-4 am and midday gives "3:34 am-1:58 pm"). Instead take the fewest hours that
    cover `share`, join runs split by one quiet hour, and keep the two biggest runs.
    """
    c = np.bincount(np.asarray(mins, dtype=int) // 60 % 24, minlength=24)
    pick = np.zeros(24, bool)
    for hr in np.argsort(-c, kind="stable"):
        if c[pick].sum() >= share * c.sum():
            break
        pick[hr] = True
    pick |= np.roll(pick, 1) & np.roll(pick, -1)
    if pick.all():
        return [[0, 1440]]
    s0 = int(np.argmin(pick))  # an unpicked hour, so no run wraps past the scan start
    runs, a = [], None
    for i in range(s0, s0 + 25):
        if i < s0 + 24 and pick[i % 24]:
            a = i if a is None else a
        elif a is not None:
            runs.append((int(c[[j % 24 for j in range(a, i)]].sum()), a % 24, i - a))
            a = None
    runs = sorted(sorted(runs, reverse=True)[:2], key=lambda r: r[1])
    return [[h * 60, (h + n) * 60] for _, h, n in runs]


# ---------- block geometry: all years, for a steadier line ----------
geo = {}
a = d.dropna(subset=["street", "block", "lat"])
a = a[a.x.between(0, F["W"]) & a.y.between(0, F["H"])]
for (st, bl), g in a.groupby(["street", "block"]):
    if len(g) < 15:
        continue
    P = g[["x", "y"]].values
    keep = np.hypot(*(P - np.median(P, 0)).T) * MPP < 150
    g, P = g[keep], P[keep]
    if len(g) < 12:
        continue
    m = P.mean(0)
    v = np.linalg.svd(P - m, full_matrices=False)[2][0]
    t = (P - m) @ v
    lo, hi = np.quantile(t, [.03, .97])
    if (hi - lo) * MPP < 40:
        lo, hi = (lo + hi) / 2 - 20 / MPP, (lo + hi) / 2 + 20 / MPP
    nrm = np.array([-v[1], v[0]])
    off = (P - m) @ nrm * MPP
    e, o = off[g.side.values == "even"], off[g.side.values == "odd"]
    sgn, even_dir = 0, None
    if len(e) >= 8 and len(o) >= 8:
        sep = np.median(e) - np.median(o)
        cons = ((np.sign(sep) * e > 0).mean() + (np.sign(sep) * o < 0).mean()) / 2
        if abs(sep) >= SEP_MIN and cons >= CONS_MIN:
            sgn = int(np.sign(sep))
            even_dir = compass(*(nrm * sgn))
    p1, p2 = m + v * lo, m + v * hi
    geo[(st, bl)] = dict(seg=[round(float(z), 1) for z in (*p1, *p2)], nrm=[round(float(nrm[0]), 3), round(float(nrm[1]), 3)],
                         sgn=sgn, even=even_dir)

# ---------- per-block summary ----------
blocks, index = [], {}
for (st, bl), g in w.dropna(subset=["street", "block"]).groupby(["street", "block"]):
    if (st, bl) not in geo or len(g) < MIN_TIX:
        continue
    top = []
    for kind, h in g.groupby("kind"):
        wk = h[h.dow < 5]
        top.append([kind, len(h), int(h.fine.median()) if h.fine.notna().any() else 0,
                    int(h.dow.mode()[0]), usual_hours(h.mins), round(len(wk) / len(h), 2)])
    top.sort(key=lambda r: -r[1])
    index[(st, bl)] = len(blocks)
    blocks.append(dict(id=f"{int(bl)}-{st.replace(' ', '-')}", street=nice_street(st), block=int(bl), n=len(g),
                       dow=np.bincount(g.dow, minlength=7).tolist(), top=top[:6], sweep=[], meter=None, **geo[(st, bl)]))
print(len(blocks), "blocks with a panel;", sum(b["even"] is not None for b in blocks), "with a known even side")

# ---------- street sweeping, per side ----------
sc = w[w.viol == "NO PARK/STREET CLEAN"].dropna(subset=["street", "block"])
program_days = set(sc.date.unique())  # a weekday with no sweeping ticket anywhere nearby = program off
phase_hits = phase_all = 0
for (st, bl, side), x in sc.groupby(["street", "block", "side"]):
    if len(x) < SWEEP_MIN or (st, bl) not in index:
        continue
    dow = int(x.dow.mode()[0])
    x = x[x.dow == dow]
    h = int(x.mins.quantile(.05) // 60)
    nth = (x.date.dt.day - 1) // 7 + 1
    on = 1 if nth.isin([1, 3]).mean() >= .5 else 2
    phase_hits += int(nth.isin([on, on + 2]).sum())
    phase_all += len(x)
    cand = pd.date_range(START, END)
    cand = cand[(cand.dayofweek == dow) & ~cand.isin(list(hol)) & cand.isin(list(program_days))]
    on_days = cand[np.isin((cand.day - 1) // 7 + 1, [on, on + 2])]
    tdays = set(x.date.unique())
    first = (x.groupby("date").mins.min() - h * 60).clip(0, 150).astype(int)
    last = (x.groupby("date").mins.max() - h * 60).clip(0, 150).astype(int)
    blocks[index[(st, bl)]]["sweep"].append(dict(
        side=side, dow=dow, h=h, on=on, rate=round(float(pd.Index(on_days).isin(tdays).mean()), 2), days=len(on_days),
        arr=sorted(first.tolist()), last=sorted(last.tolist()), n=len(x), tpd=round(len(x) / max(1, len(tdays)), 1)))
for b in blocks:
    b["sweep"].sort(key=lambda s: s["side"])
print("sweeping tickets on the posted weeks:", round(phase_hits / phase_all, 3))

# ---------- meters, per block (class weeks) ----------
m = w[w.meter].dropna(subset=["street", "block"])
mdays = pd.Index(sorted(set(m.date.unique()) - hol))
mdays = mdays[mdays.dayofweek < 6]
term_days = mdays[in_term(mdays)]
ndow = [max(1, int((term_days.dayofweek == k).sum())) for k in range(6)]
for (st, bl), x in m.groupby(["street", "block"]):
    if len(x) < METER_MIN or (st, bl) not in index:
        continue
    xt = x[x.date.isin(term_days)].sort_values("ts")
    if len(xt) < 12:
        continue
    vid = ((xt.ts.diff().dt.total_seconds() / 60 > VISIT_GAP) | (xt.date != xt.date.shift())).cumsum()
    v = xt.groupby(vid).agg(date=("date", "first"), start=("mins", "min"), k=("mins", "size"))
    kbar = v.k.mean()
    # expired cars found per visit ~ Poisson(lam); visible visits are the zero-truncated ones
    lam = brentq(lambda l: l / (1 - math.exp(-l)) - kbar, 1e-6, 50) if kbar > 1.001 else 0.05
    c = min(1 / (1 - math.exp(-lam)), 4.0)
    v = v[(v.start >= SLOT0) & (v.start < SLOT0 + NSLOT * 30)]
    slot, dw = ((v.start - SLOT0) // 30).values.astype(int), v.date.dt.dayofweek.values
    rates = [[round(n / ndow[k], 4) for n in np.bincount(slot[dw == k], minlength=NSLOT)] for k in range(6)]
    blocks[index[(st, bl)]]["meter"] = dict(n=len(x), visits=len(v), kbar=round(kbar, 2), c=round(c, 2),
                                            spaces=int(x.meter_id.nunique()), r=rates)
print(sum(b["meter"] is not None for b in blocks), "metered blocks modelled")

# ---------- campus-wide: one block's Tuesdays ----------
one = sc[(sc.street == "28TH ST") & (sc.block == 600) & (sc.side == "even")]
cal = [[str(t.date()), int((t.day - 1) // 7 + 1), int((one.date == t).sum()), int(t in hol)]
       for t in pd.date_range(START, END, freq="W-TUE")]
lags = [a for b in blocks for s in b["sweep"] if s["n"] >= 20 for a in s["arr"]]
lag_hist = np.bincount(np.clip(np.array(lags) // 10, 0, 12), minlength=13).tolist()

# ---------- campus-wide: meter tickets per hour ----------
m["hr"] = m.mins // 60
heat = {}
for lab, dset in (("term", term_days), ("off", mdays.difference(term_days))):
    x = m[m.date.isin(dset)]
    cnt = x.groupby(["dow", "hr"]).size().unstack(fill_value=0).reindex(index=range(6), columns=range(8, 20), fill_value=0)
    nd = pd.Series(dset.dayofweek).value_counts().reindex(range(6), fill_value=1)
    heat[lab] = cnt.div(nd.values, axis=0).round(2).values.tolist()

bundle = dict(frame=dict(W=F["W"], H=F["H"], mpp=round(MPP, 3)), start=str(START.date()), end=str(END.date()),
              total=len(d), window=len(w), phase=round(phase_hits / phase_all, 3),
              share=dict(sweep=round(float((d.viol == "NO PARK/STREET CLEAN").mean()), 3), meter=round(float(d.meter.mean()), 3)),
              fines=dict(sweep=int(w[w.viol == "NO PARK/STREET CLEAN"].fine.median()), meter=int(m.fine.median())),
              blocks=blocks, cal=cal, lag_hist=lag_hist, heat=heat)
out = DATA / "bundle.json"
out.write_text(json.dumps(bundle, separators=(",", ":")))
print(out, f"{out.stat().st_size // 1024} KB")
