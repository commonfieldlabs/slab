"""Pulls the last 12 months of new Austin home permits into E1/year.csv for the evergreen SEO pages.

Street + ZIP only (no house numbers): this file feeds public pages.
Usage: python -I fetch_year.py   (run weekly, before build_site.py)
"""
import csv, datetime, json, os, pathlib, re, urllib.parse, urllib.request

HERE = pathlib.Path(os.environ.get("SLAB_DATA") or pathlib.Path(__file__).parent)  # SLAB_DATA set in the GitHub Actions rebuild
API = "https://data.austintexas.gov/resource/3syk-w9eu.json"
since = datetime.date.today() - datetime.timedelta(days=365)
where = (f"issue_date >= '{since.isoformat()}T00:00:00' AND permittype = 'BP' AND work_class = 'New' "
         "AND permit_class_mapped = 'Residential' AND starts_with(permit_class, 'R- 10')")


def clean_builder(name):
    name = re.sub(r"\s*\*+.*$", "", (name or "").strip())
    name = re.sub(r"\s*\(MAIN\)\s*$", "", name, flags=re.I)
    return re.sub(r",?\s+(LLC|Inc\.?|LP|L\.P\.)$", "", name.strip(), flags=re.I).strip() or "Owner-builder"


def street(addr):
    a = re.split(r" (?:Bldg|Unit|Apt|#)\b", addr.title())[0]
    return re.sub(r"^\d+[A-Z]?\s+", "", a)


raw, offset = [], 0
while True:
    q = urllib.parse.urlencode({"$where": where, "$limit": "5000", "$offset": str(offset), "$order": "issue_date DESC",
                                "$select": "issue_date,permit_location,permit_class,original_zip,total_new_add_sqft,contractor_company_name"})
    batch = json.load(urllib.request.urlopen(API + "?" + q, timeout=120))
    raw += batch
    if len(batch) < 5000:
        break
    offset += 5000

seen, out = set(), []
for r in raw:
    k = (r.get("permit_location", "").upper(), r.get("permit_class"))
    if k in seen or not r.get("original_zip"):
        continue
    seen.add(k)
    out.append([r["issue_date"][:10], street(r.get("permit_location", "")), r["original_zip"][:5],
                int(float(r.get("total_new_add_sqft") or 0)), clean_builder(r.get("contractor_company_name"))])

with open(HERE / "year.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["issued", "street", "zip", "sqft", "builder"])
    w.writerows(out)
print(f"{len(out)} homes ({len(raw) - len(out)} duplicates removed) since {since} -> year.csv")
