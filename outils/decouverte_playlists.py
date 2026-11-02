"""Repérage : contenu du flux de playlists YouTube."""
import sys, urllib.request, xml.etree.ElementTree as ET
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
for pl in sys.argv[1:]:
    try:
        r = ET.fromstring(urllib.request.urlopen(urllib.request.Request("https://www.youtube.com/feeds/videos.xml?playlist_id=" + pl, headers={"User-Agent": "AuMicro/1.0"}), timeout=30).read())
    except Exception as e:
        print("##", pl, "erreur", e); continue
    print("##", pl, r.findtext("a:title", namespaces=NS), len(r.findall("a:entry", NS)), "vidéos")
    for e in r.findall("a:entry", NS)[:8]:
        print("  ·", e.findtext("a:published", namespaces=NS)[:16], "|", (e.findtext("a:title", namespaces=NS) or "")[:110])
