"""Builds the public, search-friendly SLAB site for GitHub Pages (E1/site-gh/).

Pages: home (latest issue), one page per issue, one page per ZIP code with new homes,
plus sitemap.xml and robots.txt. Visible pages show street + ZIP only (no house numbers).
Usage: python -I build_site.py   (reads every slab-permits-*.csv + notes/*.md in E1/)
"""
import csv, html, json, os, pathlib, re, collections, datetime, shutil, statistics

HERE = pathlib.Path(__file__).parent
# Cloud mode (GitHub Actions in commonfieldlabs/slab): SLAB_DATA = street-only inputs published at /src/data, SLAB_OUT = temp dir.
CLOUD = bool(os.environ.get("SLAB_DATA"))
DATA = pathlib.Path(os.environ.get("SLAB_DATA") or HERE)
OUT = pathlib.Path(os.environ.get("SLAB_OUT") or HERE / "site-gh")
# Set once slabpermits.com is bought and its DNS points at GitHub Pages; then BASE switches and a CNAME file is written.
CUSTOM_DOMAIN = "slabpermits.com"
BASE = f"https://{CUSTOM_DOMAIN}" if CUSTOM_DOMAIN else "https://commonfieldlabs.github.io/slab"
WEEKLY = "https://buy.stripe.com/7sY5kCberfkd5N4bo028800"
TERRITORY = "https://buy.stripe.com/4gMeVc0zN9ZTdfw4ZC28801"
INDEXNOW_KEY = "5f1c9a7e3b2d4e6f8a0b1c2d3e4f5a6b"
e = html.escape
# All sales copy lives in growth/copy.json so it can be tuned from metrics without touching code.
COPY = json.loads((DATA / "growth" / "copy.json").read_text(encoding="utf-8"))


def street(addr):
    return re.sub(r"^\d+[A-Z]?\s+", "", re.split(r" (?:Bldg|BLDG|Unit|UNIT|Apt|APT|#)\b", addr)[0])


CSS = """
:root{--paper:#f7f6f2;--sheet:#fff;--ink:#111;--sub:#5f5e58;--rule:#d7d4ca;--orange:#e2580b;--orange-ink:#b8460a}
@media (prefers-color-scheme:dark){:root{--paper:#121211;--sheet:#1a1a18;--ink:#f1efe8;--sub:#a5a39a;--rule:#34332f;--orange:#ff6a1f;--orange-ink:#ff8a4d;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 Inter,"Helvetica Neue",Arial,sans-serif;padding:24px max(16px,env(safe-area-inset-right)) 48px max(16px,env(safe-area-inset-left))}
.sheet{max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:32px}
a{color:var(--ink)}nav{font:12px/1 "IBM Plex Mono",Consolas,monospace;letter-spacing:.08em;text-transform:uppercase;display:flex;gap:16px;flex-wrap:wrap}
nav a{text-decoration:none;border-bottom:1px solid var(--rule)}
.mark{font:800 34px/1 "Barlow Condensed","Arial Narrow",sans-serif;letter-spacing:.04em;text-decoration:none}
.mark span{font:600 10px/1 "IBM Plex Mono",monospace;letter-spacing:.12em;color:var(--orange);margin-left:8px;vertical-align:middle}
h1{font:800 clamp(38px,8vw,72px)/.95 "Barlow Condensed","Arial Narrow",sans-serif;margin:0;text-wrap:balance}
h1 em{font-style:normal;color:var(--orange)}
h2{font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--orange-ink);margin:0 0 12px}
.lede{font:italic 21px/1.35 "Source Serif 4",Georgia,serif;margin:12px 0 0;max-width:36ch}
figure{margin:0;border:1px solid var(--rule);background:var(--sheet)}figure img{display:block;width:100%;height:auto}
figcaption{font:11px "IBM Plex Mono",monospace;color:var(--sub);padding:8px 12px;border-top:1px solid var(--rule)}
ul.read{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:10px}
ul.read li{padding-left:22px;position:relative}ul.read li::before{content:"";position:absolute;left:0;top:8px;width:10px;height:10px;background:var(--orange)}
.tw{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}
th{font:600 10px "IBM Plex Mono",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--sub);text-align:left;padding:6px 8px;border-bottom:2px solid var(--ink)}
td{padding:7px 8px;border-bottom:1px solid var(--rule)}td.n{font-family:"IBM Plex Mono",monospace;text-align:right;white-space:nowrap}
.cta{border:2px solid var(--ink);background:var(--sheet);padding:20px;display:flex;flex-direction:column;gap:10px}
.cta b{font:800 28px/1.05 "Barlow Condensed","Arial Narrow",sans-serif}
.btns{display:flex;gap:10px;flex-wrap:wrap}.btns a{background:var(--ink);color:var(--paper);font:600 12px "IBM Plex Mono",monospace;letter-spacing:.1em;text-transform:uppercase;padding:12px 16px;text-decoration:none}
.btns a.alt{background:transparent;color:var(--ink);border:1px solid var(--ink)}
.src{border-top:2px solid var(--ink);padding-top:12px;font:11px/1.8 "IBM Plex Mono",monospace;color:var(--sub);overflow-wrap:anywhere}
.bar{display:inline-block;height:10px;background:var(--orange);vertical-align:middle;margin-right:8px}
p.body{margin:0;max-width:62ch}
.strip{border-left:4px solid var(--orange);background:var(--sheet);padding:12px 16px;font-size:15px;line-height:1.5}
.strip b{display:block;font:800 22px/1.1 "Barlow Condensed","Arial Narrow",sans-serif;margin-bottom:4px}
.steps{list-style:none;margin:0;padding:0;display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.steps li{border-top:2px solid var(--ink);padding-top:8px}.steps b{display:block;font:800 22px/1.1 "Barlow Condensed","Arial Narrow",sans-serif}
.zips{display:flex;flex-wrap:wrap;gap:8px}.zips a{font:13px "IBM Plex Mono",monospace;border:1px solid var(--ink);padding:4px 10px;text-decoration:none}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Barlow+Condensed:wght@800&family=IBM+Plex+Mono:wght@400;600&family=Source+Serif+4:ital@1&family=Inter:wght@400;600&display=swap">')


def track(path):
    """Stripe Payment Links record client_reference_id + UTM tags, so each sale shows which page sold it."""
    slug = re.sub(r"[^A-Za-z0-9_-]", "-", path.replace(".html", "")) or "home"
    return f"client_reference_id={slug}&utm_source=slabpermits&utm_medium=site&utm_content={slug}"


def page(path, title, desc, body, depth, ld=""):
    up = "../" * depth
    ov = COPY["pages"].get(path, {})
    title, desc = ov.get("title", title), ov.get("description", desc)
    if ov.get("intro"):
        body = body.replace("</header>", "</header>" + ov["intro"], 1)
    cta = dict(COPY["cta"])
    for pre, c in COPY["cta_by_prefix"].items():
        if path.startswith(pre):
            cta.update(c)
    st = COPY["strip"]
    strip = f'<aside class="strip"><b>{e(st["who"])}</b> {e(st["what"])} <a href="what-you-get.html">{e(st["link"])} →</a></aside>' if path != "what-you-get.html" else ""
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{BASE}/{path}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:image" content="{BASE}/img-latest.png">
{FONTS}<style>{CSS}</style>{ld}</head><body><main class="sheet">
<nav><a class="mark" href="index.html">SLAB<span>NEW HOMES, WEEKLY</span></a><a href="index.html">Latest</a><a href="archive.html">Archive</a><a href="zips.html">By ZIP</a><a href="austin-new-construction-permits.html">12 months</a><a href="builders.html">Builders</a><a href="what-you-get.html">Subscribe</a></nav>
{strip}
{body}
<section class="cta"><b>{e(cta["headline"])}</b>
<span>{e(cta["sub"])}</span>
<div class="btns"><a href="{WEEKLY}?{track(path)}">{e(cta["weekly_label"])}</a><a class="alt" href="{TERRITORY}?{track(path)}">{e(cta["territory_label"])}</a>{'' if path == "what-you-get.html" else f'<a class="alt" href="what-you-get.html">{e(cta["more_label"])}</a>'}</div></section>
<p class="src">SOURCE · City of Austin Open Data, Issued Construction Permits (3syk-w9eu) · Address points (9s7j-tygf) · Basemap U.S. Census Bureau TIGERweb<br>
METHOD · New single-family and duplex building permits, duplicates removed · Move-in = permit date + 7 months (estimate) · Street names shown, house numbers withheld<br>
SLAB is published by Commonfield Labs.</p></main></body></html>"""
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc, encoding="utf-8")
    return path


def homes_table(rows, show_zip=True):
    head = "<tr><th>Street</th>" + ("<th>ZIP</th>" if show_zip else "") + "<th>Sq ft</th><th>Builder</th><th>Move-in*</th></tr>"
    body = "".join(
        f"<tr><td>{e(street(r['address']))}</td>" + (f"<td class=n>{e(r['zip'])}</td>" if show_zip else "")
        + f"<td class=n>{int(r['sqft']):,}</td><td>{e(r['builder'])}</td><td class=n>{datetime.date.fromisoformat(r['est_move_in'] + '-01'):%b %Y}</td></tr>"
        for r in sorted(rows, key=lambda r: -int(r["sqft"])))
    return f'<div class="tw"><table>{head}{body}</table></div>'


if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
issues = []
for f in sorted(DATA.glob("slab-permits-*.csv")):
    d = f.stem.replace("slab-permits-", "")
    rows = list(csv.DictReader(open(f, encoding="utf-8")))
    note = DATA / "notes" / f"{d}.md"
    read = [l[2:].strip() for l in note.read_text(encoding="utf-8").splitlines() if l.startswith("- ")] if note.exists() else []
    hero = DATA / f"slab-hero-{d}.png"
    if hero.exists():
        shutil.copy(hero, OUT / f"img-{d}.png")
    issues.append((d, rows, read, hero.exists()))
if not issues:
    raise SystemExit("no issues found")

all_rows = []
pages = []
for n, (d, rows, read, has_img) in enumerate(issues, 1):
    end = datetime.date.fromisoformat(d)
    start = end - datetime.timedelta(days=7)
    zips = collections.Counter(r["zip"] for r in rows)
    med = int(statistics.median(int(r["sqft"]) for r in rows)) if rows else 0
    title = f"Austin new home permits, week of {start:%b %-d}–{end:%b %-d, %Y}: {len(rows)} homes" if False else \
        f"Austin new home permits, week of {start:%b} {start.day}–{end:%b} {end.day}, {end.year}: {len(rows)} homes"
    desc = f"{len(rows)} new homes got building permits in Austin, TX the week of {start:%b} {start.day}. Busiest ZIPs: " + \
        ", ".join(f"{z} ({c})" for z, c in zips.most_common(3)) + f". Median {med:,} sq ft. Mapped, with builders and estimated move-in."
    img = f'<figure><img src="img-{d}.png" alt="Map of {len(rows)} new Austin homes permitted {start:%b} {start.day} to {end:%b} {end.day}, {end.year}"><figcaption>SLAB No. {n:02d} · each dot is a new house, sized by square footage</figcaption></figure>' if has_img else ""
    body = (f"<header><h1>{len(rows)} new Austin homes got permits the week of {start:%b} {start.day}–{end:%b} {end.day}. <em>Here's where.</em></h1>"
            f'<p class="lede">Median {med:,} sq ft. Most of these families move in around {(end + datetime.timedelta(days=213)):%B %Y}.</p></header>{img}'
            + (f'<section><h2>The read</h2><ul class="read">' + "".join(f"<li>{e(l)}</li>" for l in read) + "</ul></section>" if read else "")
            + '<section><h2>By ZIP</h2><div class="zips">' + "".join(f'<a href="zip-{z}.html">{z} · {c}</a>' for z, c in zips.most_common()) + "</div></section>"
            + f"<section><h2>Every home this week</h2>{homes_table(rows)}</section>")
    pages.append(page(f"issue-{d}.html", title, desc, body, 0))
    all_rows += [dict(r, issue=d) for r in rows]

latest_d, latest_rows, latest_read, latest_img = issues[-1]
shutil.copy(OUT / f"img-{latest_d}.png", OUT / "img-latest.png") if latest_img else None
home = (OUT / f"issue-{latest_d}.html").read_text(encoding="utf-8")
(OUT / "index.html").write_text(home.replace(f'{BASE}/issue-{latest_d}.html"', f'{BASE}/"'), encoding="utf-8")
pages.append("index.html")

pages.append(page("archive.html", "SLAB archive: Austin new home permits by week",
                  "Every weekly SLAB issue: new home building permits in Austin, TX, mapped by week.",
                  "<header><h1>Archive</h1></header><section><ul class='read'>" + "".join(
                      f'<li><a href="issue-{d}.html">Week ending {datetime.date.fromisoformat(d):%b %d, %Y}: {len(r)} new homes</a></li>' for d, r, _, _ in reversed(issues)) + "</ul></section>", 0))

# ---------- Evergreen pages from 12 months of permits (year.csv, from fetch_year.py) ----------
year = list(csv.DictReader(open(DATA / "year.csv", encoding="utf-8"))) if (DATA / "year.csv").exists() else []
for r in year:
    r["sqft"] = int(r["sqft"])
    r["mo"] = r["issued"][:7]
months = sorted({r["mo"] for r in year})[-12:]
span = f"{datetime.date.fromisoformat(months[0] + '-01'):%b %Y}–{datetime.date.fromisoformat(months[-1] + '-01'):%b %Y}" if months else ""
BIG = 3500


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def mon(m):
    return f"{datetime.date.fromisoformat(m + '-01'):%b %Y}"


def month_table(rows):
    c = collections.Counter(r["mo"] for r in rows)
    top = max([c[m] for m in months] + [1])
    return ('<div class="tw"><table><tr><th>Month</th><th>New homes</th></tr>' + "".join(
        f'<tr><td>{mon(m)}</td><td><span class="bar" style="width:{max(2, round(160 * c[m] / top))}px"></span>{c[m]}</td></tr>'
        for m in months) + "</table></div>")


def med(rows):
    return int(statistics.median(r["sqft"] for r in rows)) if rows else 0


def big_table(rows, n=10, show_zip=True):
    head = "<tr><th>Street</th>" + ("<th>ZIP</th>" if show_zip else "") + "<th>Sq ft</th><th>Builder</th><th>Permitted</th></tr>"
    return '<div class="tw"><table>' + head + "".join(
        f"<tr><td>{e(r['street'])}</td>" + (f'<td class=n><a href="zip-{r["zip"]}.html">{r["zip"]}</a></td>' if show_zip and r["zip"] in zip_pages else (f"<td class=n>{r['zip']}</td>" if show_zip else ""))
        + f"<td class=n>{r['sqft']:,}</td><td>{builder_link(r['builder'])}</td><td class=n>{mon(r['mo'])}</td></tr>"
        for r in sorted(rows, key=lambda r: -r["sqft"])[:n]) + "</table></div>"


by_zip_y = collections.defaultdict(list)
by_builder = collections.defaultdict(list)
for r in year:
    by_zip_y[r["zip"]].append(r)
    by_builder[r["builder"]].append(r)
zip_pages = {z for z, v in by_zip_y.items() if len(v) >= 5}
builder_pages = {b for b, v in by_builder.items() if len(v) >= 10 and b != "Owner-builder"}


def builder_link(b):
    return f'<a href="builder-{slug(b)}.html">{e(b)}</a>' if b in builder_pages else e(b)


def builders_table(rows, n=10):
    c = collections.Counter(r["builder"] for r in rows)
    return ('<div class="tw"><table><tr><th>Builder</th><th>Homes</th><th>Median sq ft</th></tr>' + "".join(
        f"<tr><td>{builder_link(b)}</td><td class=n>{k}</td><td class=n>{med([r for r in rows if r['builder'] == b]):,}</td></tr>"
        for b, k in c.most_common(n)) + "</table></div>")


def zip_chips(counter, n=40):
    return '<div class="zips">' + "".join(
        (f'<a href="zip-{z}.html">{z} · {k}</a>' if z in zip_pages else f'<a>{z} · {k}</a>') for z, k in counter.most_common(n)) + "</div>"


by_zip = collections.defaultdict(list)
for r in all_rows:
    by_zip[r["zip"]].append(r)
zip_pages |= set(by_zip)

for z in sorted(zip_pages):
    yr, wk = by_zip_y.get(z, []), by_zip.get(z, [])
    if not yr:
        yr = [dict(street=street(r["address"]), zip=z, sqft=int(r["sqft"]), builder=r["builder"], mo=r["issued"][:7]) for r in wk]
    bc = collections.Counter(r["builder"] for r in yr).most_common(3)
    streets = collections.Counter(r["street"] for r in yr).most_common(6)
    nbig = sum(1 for r in yr if r["sqft"] >= BIG)
    body = (f"<header><h1>New homes in {z}, Austin TX: <em>{len(yr)} permitted</em> in the last 12 months.</h1>"
            f'<p class="lede">Median {med(yr):,} sq ft. {nbig} of them are {BIG:,}+ sq ft. Most active: {", ".join(e(b) for b, _ in bc)}.</p></header>'
            + (f"<section><h2>Newest permits (SLAB weekly)</h2>{homes_table(wk, show_zip=False)}</section>" if wk else "")
            + f"<section><h2>Month by month, {span}</h2>{month_table(yr)}</section>"
            + f"<section><h2>Who's building in {z}</h2>{builders_table(yr, 8)}</section>"
            + "<section><h2>Streets with the most new homes</h2><ul class='read'>" + "".join(f"<li>{e(s_)}: {k} homes</li>" for s_, k in streets) + "</ul></section>"
            + f"<section><h2>Biggest new homes in {z}</h2>{big_table(yr, 10, show_zip=False)}</section>")
    pages.append(page(f"zip-{z}.html", f"New construction in {z} Austin TX: {len(yr)} new home permits, builders, streets",
                      f"{len(yr)} new single-family homes permitted in ZIP {z}, Austin TX in the last 12 months. Top builders: {', '.join(b for b, _ in bc)}. Median {med(yr):,} sq ft. Updated weekly from City of Austin permits.", body, 0))

pages.append(page("zips.html", "Austin new construction by ZIP code: new home permits, last 12 months",
                  f"New home building permits in Austin, TX by ZIP code, {span}. {len(year):,} homes. Updated weekly.",
                  f"<header><h1>New Austin homes by ZIP</h1><p class='lede'>{len(year):,} new homes permitted, {span}. Pick a ZIP for builders, streets and the biggest houses.</p></header><section>{zip_chips(collections.Counter({z: len(v) for z, v in by_zip_y.items()}))}</section>", 0))

for b in sorted(builder_pages):
    rows = by_builder[b]
    zc = collections.Counter(r["zip"] for r in rows)
    body = (f"<header><h1>{e(b)} in Austin: <em>{len(rows)} new homes</em> permitted in 12 months.</h1>"
            f'<p class="lede">Median {med(rows):,} sq ft. Busiest ZIPs: {", ".join(f"{z} ({k})" for z, k in zc.most_common(3))}.</p></header>'
            + f"<section><h2>Where they're building</h2>{zip_chips(zc)}</section>"
            + f"<section><h2>Month by month, {span}</h2>{month_table(rows)}</section>"
            + f"<section><h2>Largest homes</h2>{big_table(rows, 10)}</section>")
    pages.append(page(f"builder-{slug(b)}.html", f"{b} Austin new home permits: {len(rows)} homes, ZIP codes, sizes",
                      f"{b} pulled {len(rows)} new home building permits in Austin, TX in the last 12 months, mostly in {', '.join(z for z, _ in zc.most_common(3))}. Median {med(rows):,} sq ft. Updated weekly.", body, 0))

pages.append(page("builders.html", "Austin home builders ranked by new home permits, last 12 months",
                  f"Which builders are building the most new homes in Austin, TX: {len(builder_pages)} builders ranked by permits, {span}.",
                  f"<header><h1>Austin builders, <em>ranked by new homes</em></h1><p class='lede'>Every builder with 10+ new-home permits in Austin city limits, {span}.</p></header>"
                  f"<section>{builders_table([r for r in year if r['builder'] != 'Owner-builder'], len(builder_pages))}</section>", 0))

ld = ('<script type="application/ld+json">' + __import__("json").dumps({
    "@context": "https://schema.org", "@type": "Dataset", "name": "Austin new home building permits (SLAB)",
    "description": "Weekly-updated list of new single-family and duplex building permits issued by the City of Austin, deduplicated, with ZIP, square footage, builder and estimated move-in month.",
    "url": f"{BASE}/austin-new-construction-permits.html", "isBasedOn": "https://data.austintexas.gov/d/3syk-w9eu",
    "spatialCoverage": "Austin, Texas", "temporalCoverage": f"{months[0]}/{months[-1]}" if months else None,
    "creator": {"@type": "Organization", "name": "Commonfield Labs"}, "isAccessibleForFree": False}) + "</script>")
zc_all = collections.Counter(r["zip"] for r in year)
pages.append(page("austin-new-construction-permits.html", f"Austin new construction permits: {len(year):,} new homes in 12 months, by ZIP and builder",
                  f"Every new home building permit in Austin, TX, {span}: {len(year):,} homes. Monthly totals, busiest ZIP codes, top builders and the biggest houses. Updated weekly.",
                  f"<header><h1>{len(year):,} new Austin homes got permits <em>in 12 months.</em></h1>"
                  f"<p class='lede'>Median {med(year):,} sq ft. {sum(1 for r in year if r['sqft'] >= BIG)} were {BIG:,}+ sq ft. Busiest: {', '.join(f'{z} ({k})' for z, k in zc_all.most_common(3))}.</p></header>"
                  f"<section><h2>Month by month, {span}</h2>{month_table(year)}</section>"
                  f"<section><h2>Busiest ZIP codes</h2>{zip_chips(zc_all, 30)}</section>"
                  f"<section><h2>Top builders</h2>{builders_table([r for r in year if r['builder'] != 'Owner-builder'], 12)}<p><a href='builders.html'>All builders →</a></p></section>"
                  f"<section><h2>Biggest new homes</h2>{big_table(year, 12)}</section>"
                  "<section><h2>For your trade</h2><div class='zips'><a href='pool-leads-austin.html'>Pool builders</a><a href='solar-leads-austin.html'>Solar</a><a href='landscaping-leads-austin.html'>Landscaping</a><a href='fence-leads-austin.html'>Fence</a></div></section>", 0, ld))

# Trade landing pages: the searches buyers actually type ("pool leads austin").
TRADES = [
    ("pool", "Pool builder leads in Austin", "pool builders",
     f"Big new houses are the pool prospects. A family that just built {BIG:,}+ sq ft is the likeliest to add a pool or outdoor living, and the permit shows up about 7 months before they move in.",
     lambda r: r["sqft"] >= BIG, f"New homes {BIG:,}+ sq ft"),
    ("solar", "Solar leads in Austin: new homes before move-in", "solar installers",
     "Every new house is a roof with no panels on it, owned by someone already making big decisions about the home. The permit is the earliest public signal, about 7 months before move-in.",
     lambda r: True, "All new homes"),
    ("landscaping", "Landscaping leads in Austin: new home permits", "landscapers and irrigation companies",
     "New builds hand over bare or builder-basic yards. Custom and owner-built homes fit full design work; tract streets fit maintenance routes.",
     lambda r: True, "All new homes"),
    ("fence", "Fence company leads in Austin: new home permits", "fence companies",
     "When one builder pulls many permits on one street, many yards need fences at about the same time, often to the same spec.",
     lambda r: True, "All new homes"),
]
for key, h, who, why, keep, label in TRADES:
    rows = [r for r in year if keep(r)]
    zc = collections.Counter(r["zip"] for r in rows)
    extra = ""
    if key == "fence":
        st = collections.Counter((r["street"], r["zip"], r["builder"]) for r in year if r["builder"] != "Owner-builder")
        extra = "<section><h2>Streets with the most new homes from one builder</h2><ul class='read'>" + "".join(
            f"<li>{e(s_)} ({z}): {k} homes by {builder_link(b)}</li>" for (s_, z, b), k in st.most_common(10)) + "</ul></section>"
    if key == "landscaping":
        cust = [r for r in year if r["builder"] == "Owner-builder" or r["sqft"] >= BIG]
        extra = f"<section><h2>Custom and owner-built homes (full-design prospects): {len(cust)}</h2>{zip_chips(collections.Counter(r['zip'] for r in cust), 20)}</section>"
    body = (f"<header><h1>{e(h)}: <em>{len(rows):,} homes</em> in 12 months.</h1><p class='lede'>For {who}. {e(why)}</p></header>"
            f"<section><h2>{label} by ZIP, {span}</h2>{zip_chips(zc, 30)}</section>{extra}"
            + (f"<section><h2>Biggest of them</h2>{big_table(rows, 12)}</section>" if key == "pool" else "")
            + "<section><h2>How SLAB works</h2><p class='body'>Every Friday SLAB pulls the City of Austin's newly issued building permits, keeps the new single-family homes, removes duplicates and maps them. "
              "Subscribers get the map plus a spreadsheet for their ZIP codes: street address, size, builder and estimated move-in month. That's enough to plan mailers, door hangers or a builder pitch before the house is finished.</p></section>")
    pages.append(page(f"{key}-leads-austin.html", f"{h} | SLAB", f"{len(rows):,} new Austin homes in 12 months for {who}: by ZIP, with builders, sizes and move-in timing. Weekly list from City of Austin permits, $49/mo.", body, 0))


# ---------- What you get (the plain-language pitch page) ----------
sample = sorted(latest_rows, key=lambda r: -int(r["sqft"]))[:6]
sample_tbl = ('<div class="tw"><table><tr><th>Issued</th><th>Address</th><th>ZIP</th><th>Sq ft</th><th>Builder</th><th>Move-in</th></tr>' + "".join(
    f"<tr><td class=n>{r['issued']}</td><td>#### {e(street(r['address']))}</td><td class=n>{r['zip']}</td><td class=n>{int(r['sqft']):,}</td><td>{e(r['builder'])}</td><td class=n>{r['est_move_in']}</td></tr>"
    for r in sample) + "</table></div>")
pages.append(page("what-you-get.html", "SLAB: weekly new-home leads for Austin pool, solar, landscaping and fence companies",
                  "What a SLAB subscription includes: every new home permitted in your Austin ZIP codes each Friday, with address, size, builder and estimated move-in. $49/mo.",
                  "<header><h1>New Austin homes, <em>before anyone moves in.</em></h1>"
                  "<p class='lede'>A list for companies that sell to new homeowners: pools, solar, landscaping, irrigation, fencing, security, blinds.</p></header>"
                  "<section><h2>Why it works</h2><p class='body'>When the City of Austin issues a building permit for a new house, it's public, but buried in a government database. "
                  "The family usually moves in about 7 months later. In between, they're choosing who builds the pool, installs the panels and fences the yard. "
                  "SLAB pulls those permits every week and hands you the ones in your ZIP codes, so you can be first through the door.</p></section>"
                  "<section><h2>What you get every Friday</h2><ul class='steps'>"
                  "<li><b>A spreadsheet</b>Every new home in your ZIP codes: full street address, square footage, builder, permit date, estimated move-in month and a link to the city's permit record.</li>"
                  "<li><b>A map</b>Where this week's homes are, so you can see which streets and subdivisions are filling up.</li>"
                  "<li><b>The read</b>Three lines on what matters: clusters, the big custom houses, who's building where.</li></ul></section>"
                  f"<section><h2>Sample rows from this week's file</h2>{sample_tbl}<p class='body' style='font-size:13px;color:var(--sub)'>House numbers hidden here; subscribers get full addresses.</p></section>"
                  "<section><h2>How people use it</h2><ul class='read'>"
                  "<li>Mail a postcard timed to move-in month instead of buying a generic list.</li>"
                  "<li>Pitch the builder who just pulled 15 permits on one street.</li>"
                  "<li>Plan door-hanger and sales routes around the streets filling up next.</li></ul></section>"
                  "<section><h2>The two options</h2><ul class='steps'>"
                  "<li><b>Weekly list · $49/mo</b>Every Friday, your ZIP codes. Cancel anytime. Enter your ZIP codes at checkout.</li>"
                  "<li><b>Territory Report · $750</b>One-time: 12 months of new homes in your service area, mapped and ranked by growth and house size, plus the builder list and a move-in calendar.</li></ul></section>", 0))

(OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                 + "".join(f"<url><loc>{BASE}/{p.replace('index.html', '')}</loc><lastmod>{datetime.date.today()}</lastmod></url>" for p in dict.fromkeys(pages)) + "</urlset>\n", encoding="utf-8")
(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /src/\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
(OUT / ".nojekyll").write_text("", encoding="utf-8")
# Search engine ownership/notification files (must survive every rebuild).
(OUT / "googlecc75f6662eab9738.html").write_text("google-site-verification: googlecc75f6662eab9738.html", encoding="utf-8")
(OUT / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
if CUSTOM_DOMAIN:
    (OUT / "CNAME").write_text(CUSTOM_DOMAIN + "\n", encoding="utf-8")
if not CLOUD:
    # Street-only copy of the build inputs, published at /src/ so the weekly GitHub Actions rebuild
    # (.github/workflows/rebuild.yml in commonfieldlabs/slab) runs with the laptop off. No house numbers leave E1.
    src, dat = OUT / "src", OUT / "src" / "data"
    (dat / "notes").mkdir(parents=True)
    (dat / "growth").mkdir()
    for name in ("build_site.py", "fetch_year.py", "ping_indexnow.py"):
        shutil.copy(HERE / name, src / name)
    shutil.copy(HERE / "growth" / "copy.json", dat / "growth" / "copy.json")
    if (HERE / "year.csv").exists():
        shutil.copy(HERE / "year.csv", dat / "year.csv")
    for d, rows, read, has_img in issues:
        with open(dat / f"slab-permits-{d}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["issued", "address", "zip", "sqft", "builder", "est_move_in"])
            w.writerows([r["issued"], street(r["address"]), r["zip"], r["sqft"], r["builder"], r["est_move_in"]] for r in rows)
        if (HERE / "notes" / f"{d}.md").exists():
            shutil.copy(HERE / "notes" / f"{d}.md", dat / "notes" / f"{d}.md")
        if has_img:
            shutil.copy(HERE / f"slab-hero-{d}.png", dat / f"slab-hero-{d}.png")
print(len(pages), "pages ->", OUT)
