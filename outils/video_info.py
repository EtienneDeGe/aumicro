"""Titre, chaîne, date et heure de publication de vidéos YouTube."""
import json, re, sys, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Accept-Language": "fr-FR,fr"}
for v in sys.argv[1:]:
    try:
        o = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={v}&format=json", headers=UA), timeout=30).read())
        print(v, "|", o.get("title"), "|", o.get("author_name"))
    except Exception as e:
        print(v, "oembed erreur", e)
    try:
        h = urllib.request.urlopen(urllib.request.Request(f"https://www.youtube.com/watch?v={v}", headers=UA), timeout=30).read().decode("utf-8", "replace")
        for k in ("uploadDate", "datePublished", "startDate", "lengthSeconds"):
            m = re.search(rf'"{k}":"([^"]+)"', h) or re.search(rf'itemprop="{k}" content="([^"]+)"', h)
            print("  ", k, m and m.group(1))
        m = re.search(r'"shortDescription":"(.{0,600})', h); print("   desc:", m and m.group(1)[:600])
    except Exception as e:
        print("  page erreur", e)
