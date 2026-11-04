"""Repérage des flux Radio France à partir des pages d'émission."""
import re, sys, urllib.request, xml.etree.ElementTree as ET, html
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36", "Accept-Language": "fr-FR,fr"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
for p in sys.argv[1:]:
    try: h = get("https://www.radiofrance.fr/" + p)
    except Exception as e: print("##", p, "erreur", e); continue
    flux = sorted(set(re.findall(r'https://radiofrance-podcast\.net/podcast09/[\w-]+\.xml', h)))
    print("##", p, flux[:1])
    if flux:
        r = ET.fromstring(get(flux[0]).encode())
        for it in list(r.iter("item"))[:4]:
            print("   ·", (it.findtext("pubDate") or "")[:22], "|", (it.findtext("title") or "")[:90], "|", " ".join(html.unescape(re.sub("<[^>]+>", " ", it.findtext("description") or "")).split())[:130])
