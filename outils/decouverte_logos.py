"""Repérage : logos des radios sur Wikidata / Wikimedia Commons (propriété P154)."""
import json, urllib.parse, urllib.request
UA = {"User-Agent": "AuMicro/1.0 (https://etiennedege.github.io/aumicro/)"}
def api(**p):
    p["format"] = "json"
    return json.loads(urllib.request.urlopen(urllib.request.Request("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(p), headers=UA), timeout=30).read())
for nom in ["RTL"]:
    hits = api(action="wbsearchentities", search=nom, language="fr", type="item", limit=20)["search"]
    for h in hits:
        e = api(action="wbgetentities", ids=h["id"], props="claims")["entities"][h["id"]]
        logos = [c["mainsnak"].get("datavalue", {}).get("value") for c in e.get("claims", {}).get("P154", [])]
        print(f"{nom} | {h['id']} | {h.get('label')} | {h.get('description','')[:60]} | {logos}")
    else:
        print(f"{nom} | aucun logo trouvé")
