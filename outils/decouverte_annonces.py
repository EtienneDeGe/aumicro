"""Repérage (2) : contenu des grilles Radio France pour demain, et messages récents des comptes Bluesky."""
import json, re, urllib.parse, urllib.request, html
from datetime import date, timedelta
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36", "Accept-Language": "fr-FR,fr"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
for j in (0, 1):
    d = (date.today() + timedelta(days=j)).strftime("%d-%m-%Y")
    for st, cles in (("franceinter", ["7h50", "8h20", "Invité"]), ("franceinfo", ["8h30", "8.30"])):
        u = f"https://www.radiofrance.fr/{st}/grille-programmes?date={d}"
        print(f"\n## {st} {d}")
        try: h = get(u)
        except Exception as e: print(" erreur", e); continue
        titres = re.findall(r'title:"([^"]{8,160})"', h) + re.findall(r'\\"title\\":\\"([^\\]{8,160})\\"', h)
        for t in dict.fromkeys(titres):
            if any(k.lower() in t.lower() for k in cles) or re.search(r"[A-Z][a-zé]+ [A-Z][a-zé]+", t):
                print("  ·", html.unescape(t)[:160])
print("\n## Bluesky : derniers messages des comptes")
for acteur in ["franceinter.fr", "publicsenat.fr", "lcp.fr", "sudradiofrance.bsky.social", "europe1.bsky.social"]:
    try:
        r = json.loads(get("https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?" + urllib.parse.urlencode({"actor": acteur, "limit": 40})))
        posts = r.get("feed", [])
        print(f" ## {acteur} : {len(posts)} messages, dernier le {posts[0]['post']['record'].get('createdAt','')[:16] if posts else '-'}")
        for x in posts:
            t = " ".join(x["post"]["record"].get("text", "").split())
            if re.search(r"(?i)invit|demain|8h20|7h50|8h30|face à", t):
                print("   ·", x["post"]["record"].get("createdAt", "")[:16], "|", t[:170])
    except Exception as e: print(" ", acteur, "erreur", e)
