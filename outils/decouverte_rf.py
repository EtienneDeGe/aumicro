"""Repérage : flux Radio France (2e essai) et chaînes YouTube des radios."""
import re, urllib.request, xml.etree.ElementTree as ET
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36", "Accept-Language": "fr-FR,fr"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
for p in ["https://www.radiofrance.fr/franceinter/podcasts/l-invite-de-7h50",
          "https://www.radiofrance.fr/franceinfo/podcasts/8h30-franceinfo"]:
    print("\n## RF", p)
    try: h = get(p)
    except Exception as e: print(" erreur", e); continue
    urls = sorted(set(re.findall(r'https?:[^"\'\s<>]*(?:rss|\.xml|feed)[^"\'\s<>]*', h, re.I)))
    print(" urls:", urls[:15])
    for m in list(re.finditer(r'rss', h, re.I))[:5]:
        print("  …", h[max(0,m.start()-120):m.start()+120].replace("\n"," "))
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
for handle in ["franceinter", "franceinfo", "RMC", "BFMTV", "RTL", "rtlfrance", "Europe1", "SudRadio", "radioclassique", "RFI", "publicsenat", "LCP"]:
    print("\n## YT @" + handle)
    try: h = get("https://www.youtube.com/@" + handle)
    except Exception as e: print(" erreur", e); continue
    m = re.search(r'"(?:externalId|channelId)":"(UC[\w-]{22})"', h) or re.search(r'channel_id=(UC[\w-]{22})', h)
    t = re.search(r'<title>([^<]*)</title>', h)
    print(" titre:", t.group(1) if t else "?", "| id:", m.group(1) if m else "?")
    if not m: continue
    try: r = ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?channel_id=" + m.group(1)))
    except Exception as e: print(" flux erreur", e); continue
    for e in r.findall("a:entry", NS)[:12]:
        print("  ·", e.findtext("a:published", namespaces=NS)[:16], "|", e.findtext("a:title", namespaces=NS), "|", e.findtext("yt:videoId", namespaces=NS))
