"""Repérage : trouve les flux podcast des émissions via l'annuaire Apple Podcasts et affiche leurs derniers épisodes."""
import json, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET

RECHERCHES = [
    "Les Grandes Gueules RMC", "Face aux Grandes Gueules", "Les Grandes Gueules invité politique",
    "Questions politiques France Inter", "franceinfo interview 18h", "franceinfo l'interview politique soir",
    "Europe 1 soir interview politique", "Europe 1 l'invité de 18h", "RTL soir invité", "RTL l'invité de 18h", "RTL Grand Jury",
    "Sud Radio Midi invité politique", "Sud Radio invité soir", "RFI invité de la mi-journée", "France Inter 13h invité",
    "franceinfo 12h invité politique", "Les informés franceinfo", "Estelle Midi RMC invité", "On refait le monde RTL",
    "Le grand rendez-vous Europe 1", "Dimanche en politique", "franceinfo le grand entretien dimanche",
]
UA = {"User-Agent": "Mozilla/5.0 (compatible; AuMicro/0.1; +https://etiennedege.github.io/aumicro/)"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()

vus = set()
for terme in RECHERCHES:
    q = urllib.parse.urlencode({"term": terme, "media": "podcast", "country": "fr", "limit": 4})
    try:
        res = json.loads(get("https://itunes.apple.com/search?" + q))["results"]
    except Exception as e:
        print(f"## {terme} : erreur {e}"); continue
    print(f"\n## Recherche : {terme}")
    for r in res:
        flux = r.get("feedUrl")
        print(f"- {r.get('collectionName')} | {r.get('artistName')} | {flux}")
        if not flux or flux in vus: continue
        vus.add(flux)
        try:
            racine = ET.fromstring(get(flux))
        except Exception as e:
            print(f"    (flux illisible : {e})"); continue
        for it in racine.iter("item"):
            pass
        items = list(racine.iter("item"))[:4]
        for it in items:
            t = (it.findtext("title") or "").strip()
            d = (it.findtext("pubDate") or "").strip()
            l = (it.findtext("link") or "").strip()
            enc = it.find("enclosure"); e = enc.get("url") if enc is not None else ""
            desc = " ".join((it.findtext("description") or "").split())[:160]
            print(f"    · {d} | {t}\n      lien: {l}\n      audio: {e[:120]}\n      desc: {desc}")
