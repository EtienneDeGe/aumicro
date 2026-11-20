"""Repérage : podcasts des émissions TV (annuaire Apple Podcasts) et forme de leurs derniers épisodes."""
import json, re, html, urllib.parse, urllib.request, xml.etree.ElementTree as ET
UA = {"User-Agent": "Mozilla/5.0 (compatible; AuMicro/1.0)"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
txt = lambda h: " ".join(html.unescape(re.sub("<[^>]+>", " ", h or "")).split())
RECHERCHES = [
 "Bonjour TF1 Bruce Toussaint", "TF1 interview politique", "Les 4 vérités France 2", "Télématin invité", "L'heure de vérité France 2",
 "C à vous France 5", "C ce soir France 5", "C l'hebdo", "Quotidien TMC", "28 minutes Arte",
 "LCI L'interview", "Rochebin LCI", "LCI Le grand entretien", "LCI Matin invité politique", "Darius Rochebin",
 "CNews La grande interview", "CNews Face à face", "CNews 100% politique", "L'heure des pros", "Punchline CNews",
 "franceinfo TV invité", "Ça vous regarde LCP", "LCP invité politique", "Bonjour chez vous Public Sénat", "Public Sénat invité",
 "Sens public", "France 24 Mardi politique", "France 24 l'entretien politique", "BFMTV Vous Président", "BFMTV Le Live Toussaint",
 "BFM Story invité", "Les Grandes Gueules BFM", "M6 Zone interdite politique", "France 3 Dimanche en politique", "ICI matin invité politique",
]
vus = set()
for t in RECHERCHES:
    try:
        res = json.loads(get("https://itunes.apple.com/search?" + urllib.parse.urlencode({"term": t, "media": "podcast", "country": "fr", "limit": 3})))["results"]
    except Exception as e:
        print("##", t, "erreur", e); continue
    print("\n##", t)
    for r in res:
        f = r.get("feedUrl")
        print(f"- {r.get('collectionName')} | {r.get('artistName')} | {f}")
        if not f or f in vus: continue
        vus.add(f)
        try:
            items = list(ET.fromstring(get(f)).iter("item"))[:3]
        except Exception as e:
            print("    illisible", e); continue
        for it in items:
            print("    ·", (it.findtext("pubDate") or "")[5:22], "|", txt(it.findtext("title"))[:90], "||", txt(it.findtext("description"))[:110])
