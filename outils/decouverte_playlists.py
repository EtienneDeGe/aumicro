"""Repérage : flux d'une playlist et lecture de la durée via l'API interne du lecteur YouTube."""
import json, sys, urllib.request, xml.etree.ElementTree as ET
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
def duree(vid):
    corps = json.dumps({"videoId": vid, "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "fr"}}}).encode()
    req = urllib.request.Request("https://www.youtube.com/youtubei/v1/player?prettyPrint=false", data=corps,
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return r.get("videoDetails", {}).get("lengthSeconds"), r.get("playabilityStatus", {}).get("status")
    except Exception as e:
        return None, str(e)[:60]
print("test durée GFTBHZH78LY :", duree("GFTBHZH78LY"), "| VMF2zEw7mso :", duree("VMF2zEw7mso"))
for pl in sys.argv[1:]:
    try:
        r = ET.fromstring(urllib.request.urlopen(urllib.request.Request("https://www.youtube.com/feeds/videos.xml?playlist_id=" + pl, headers={"User-Agent": "AuMicro/1.0"}), timeout=30).read())
    except Exception as e:
        print("##", pl, "erreur", e); continue
    print("##", pl, r.findtext("a:title", namespaces=NS), "| auteur :", r.findtext("a:author/a:name", namespaces=NS), "|", len(r.findall("a:entry", NS)), "vidéos")
    for e in r.findall("a:entry", NS):
        v = e.findtext("yt:videoId", namespaces=NS)
        print("  ·", e.findtext("a:published", namespaces=NS)[:10], "|", duree(v)[0], "s |", (e.findtext("a:title", namespaces=NS) or "")[:100])
