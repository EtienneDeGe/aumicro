"""Repérage : trouve les flux podcast des émissions via l'annuaire Apple Podcasts et affiche leurs derniers épisodes."""
import json, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET

RECHERCHES = [
    "L'invité de 7h50 France Inter", "Le grand entretien de 8h20 France Inter", "invité de 7h50 week-end France Inter",
    "8h30 franceinfo", "franceinfo interview politique", "Face à Face RMC Apolline de Malherbe",
    "Le Grand Jury RTL", "Elysée 2027 RTL", "L'invité de RTL", "RTL Matin",
    "Europe 1 grande interview", "Les Grands Entretiens d'Europe 1", "Europe 1 interview politique",
    "Sud Radio invité politique", "Sud Radio Le Grand Matin", "RFI invité du matin", "RFI invité Afrique matin",
    "Radio Classique invité politique", "Radio Classique la matinale",
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
        items = list(racine.iter("item"))[:6]
        for it in items:
            t = (it.findtext("title") or "").strip()
            d = (it.findtext("pubDate") or "").strip()
            l = (it.findtext("link") or "").strip()
            enc = it.find("enclosure"); e = enc.get("url") if enc is not None else ""
            desc = " ".join((it.findtext("description") or "").split())[:160]
            print(f"    · {d} | {t}\n      lien: {l}\n      audio: {e[:120]}\n      desc: {desc}")
