"""Repérage : contenu du flux d'une playlist YouTube."""
import sys, urllib.request, xml.etree.ElementTree as ET
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
for pl in sys.argv[1:]:
    r = ET.fromstring(urllib.request.urlopen(urllib.request.Request("https://www.youtube.com/feeds/videos.xml?playlist_id=" + pl, headers={"User-Agent": "AuMicro/1.0"}), timeout=30).read())
    print("##", pl, r.findtext("a:title", namespaces=NS), len(r.findall("a:entry", NS)), "vidéos dans le flux")
    for e in r.findall("a:entry", NS):
        print("  ·", e.findtext("a:published", namespaces=NS)[:16], "|", e.findtext("a:title", namespaces=NS), "|", e.findtext("yt:videoId", namespaces=NS))
