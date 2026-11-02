"""Repérage : où trouver les invités annoncés à l'avance (grilles des radios, Bluesky)."""
import json, re, urllib.parse, urllib.request, html
from datetime import date, timedelta
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36", "Accept-Language": "fr-FR,fr"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
def txt(h): return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", h)).split())
demain = date.today() + timedelta(days=1)
d1, d2 = demain.strftime("%d-%m-%Y"), demain.isoformat()
PAGES = [
  f"https://www.radiofrance.fr/franceinter/grille-programmes?date={d1}",
  f"https://www.radiofrance.fr/franceinfo/grille-programmes?date={d1}",
  "https://www.radiofrance.fr/franceinter/podcasts/l-invite-de-7h50",
  "https://www.sudradio.fr/programme/le-petit-dejeuner-politique-sudradio",
  "https://www.sudradio.fr/grille-des-programmes",
  "https://www.europe1.fr/programmes",
  "https://www.rtl.fr/programmes/l-invite-de-7h40",
  "https://www.radioclassique.fr/programmes/",
]
for p in PAGES:
    print("\n##", p)
    try: t = txt(get(p))
    except Exception as e: print("  erreur", e); continue
    print("  longueur", len(t))
    for m in list(re.finditer(r"(?i)invit|7h50|8h20|8h30|7h40|demain", t))[:8]:
        print("  …", t[max(0, m.start()-100):m.start()+160])
print("\n## Bluesky : comptes")
for q in ["franceinter", "franceinfo", "RTL", "Europe 1", "RMC", "Sud Radio", "Radio Classique", "Public Sénat", "LCP"]:
    try:
        r = json.loads(get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors?" + urllib.parse.urlencode({"q": q, "limit": 4})))
        print(" ", q, "→", [(a["handle"], a.get("displayName")) for a in r.get("actors", [])])
    except Exception as e: print(" ", q, "erreur", e)
print("\n## Bluesky : recherche de messages")
for q in ["invité demain matin", "sera l'invité", "invitée demain", "#8h30franceinfo", "Face à Face Apolline demain"]:
    try:
        r = json.loads(get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?" + urllib.parse.urlencode({"q": q, "lang": "fr", "limit": 10, "sort": "latest"})))
        print(" ##", q, len(r.get("posts", [])))
        for x in r.get("posts", [])[:6]:
            print("   ·", x["author"]["handle"], "|", x["record"].get("createdAt", "")[:16], "|", " ".join(x["record"].get("text", "").split())[:160])
    except Exception as e: print(" ", q, "erreur", e)
