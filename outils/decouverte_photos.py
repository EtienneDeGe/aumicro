"""Repérage : photos libres d'une personnalité sur Wikimedia Commons."""
import json, sys, urllib.parse, urllib.request, re, html
UA = {"User-Agent": "AuMicro/1.0 (https://etiennedege.github.io/aumicro/)"}
def api(**p):
    p["format"] = "json"
    return json.loads(urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p), headers=UA), timeout=30).read())
for nom in sys.argv[1:]:
    print("##", nom)
    r = api(action="query", list="search", srsearch=nom, srnamespace=6, srlimit=20)
    for h in r["query"]["search"]:
        t = h["title"]
        info = api(action="query", titles=t, prop="imageinfo", iiprop="extmetadata|size")
        page = next(iter(info["query"]["pages"].values()))
        ii = (page.get("imageinfo") or [{}])[0]
        m = ii.get("extmetadata", {})
        g = lambda k: " ".join(html.unescape(re.sub("<[^>]+>", " ", m.get(k, {}).get("value", ""))).split())[:70]
        print(f"- {t} | {ii.get('width')}x{ii.get('height')} | {g('DateTimeOriginal')} | {g('Artist')} | {g('LicenseShortName')} | {g('ImageDescription')}")
