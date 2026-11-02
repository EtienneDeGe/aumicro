"""Repérage des flux Radio France à partir des pages d'émission."""
import re, urllib.request, xml.etree.ElementTree as ET
UA = {"User-Agent": "Mozilla/5.0 (compatible; AuMicro/0.1)"}
PAGES = [
 "https://www.radiofrance.fr/franceinter/podcasts/l-invite-de-7h50",
 "https://www.radiofrance.fr/franceinter/podcasts/l-invite-de-8h20-le-grand-entretien",
 "https://www.radiofrance.fr/franceinter/podcasts/l-invite-de-7h50-du-week-end",
 "https://www.radiofrance.fr/franceinter/podcasts/l-invite-de-8h20-du-week-end",
 "https://www.radiofrance.fr/franceinfo/podcasts/8h30-franceinfo",
 "https://www.radiofrance.fr/franceinfo/podcasts/l-interview-politique",
 "https://www.radiofrance.fr/franceinfo/podcasts/le-grand-face-a-face",
]
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
for p in PAGES:
    print("\n##", p)
    try: html = get(p).decode("utf-8", "replace")
    except Exception as e: print("  erreur", e); continue
    flux = sorted(set(re.findall(r'https://radiofrance-podcast\.net/podcast09/rss_\d+\.xml', html)))
    print("  flux:", flux)
    for f in flux[:1]:
        try: r = ET.fromstring(get(f))
        except Exception as e: print("  illisible", e); continue
        for it in list(r.iter("item"))[:5]:
            print("   ·", it.findtext("pubDate"), "|", (it.findtext("title") or "").strip())
            print("     lien:", it.findtext("link"))
            print("     desc:", " ".join((it.findtext("description") or "").split())[:200])
