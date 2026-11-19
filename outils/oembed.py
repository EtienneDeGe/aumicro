"""Titre et chaîne d'une vidéo YouTube (oEmbed)."""
import json, sys, urllib.parse, urllib.request
for v in sys.argv[1:]:
    u = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote("https://www.youtube.com/watch?v=" + v)
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "AuMicro/1.0"}), timeout=30).read())
        print(v, "|", r.get("author_name"), "|", r.get("title"))
    except Exception as e:
        print(v, "erreur", e)
