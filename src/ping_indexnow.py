"""Tells Bing (and other IndexNow engines) which slabpermits.com pages exist or changed. Run after each publish.
Usage: python -I ping_indexnow.py
"""
import json, os, pathlib, re, urllib.error, urllib.request

HERE = pathlib.Path(__file__).parent
KEY = "5f1c9a7e3b2d4e6f8a0b1c2d3e4f5a6b"
urls = re.findall(r"<loc>([^<]+)</loc>", (pathlib.Path(os.environ.get("SLAB_OUT") or HERE / "site-gh") / "sitemap.xml").read_text(encoding="utf-8"))
body = json.dumps({"host": "slabpermits.com", "key": KEY, "keyLocation": f"https://slabpermits.com/{KEY}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"IndexNow: {r.status} for {len(urls)} URLs")
except urllib.error.HTTPError as err:
    print(f"IndexNow failed: {err.code} {err.read()[:200]!r}")
