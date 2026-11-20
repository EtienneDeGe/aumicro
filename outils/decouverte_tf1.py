"""Repérage : chaîne YouTube TF1 INFO, playlist donnée, et flux France 24."""
import re, sys, urllib.request, xml.etree.ElementTree as ET
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Accept-Language": "fr-FR,fr"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
def flux(param):
    try:
        r = ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?" + param))
    except Exception as e:
        print("##", param, "erreur", e); return
    print("##", param, r.findtext("a:title", namespaces=NS), "|", len(r.findall("a:entry", NS)), "vidéos")
    for e in r.findall("a:entry", NS):
        print("  ·", e.findtext("a:published", namespaces=NS)[:16], e.findtext("yt:videoId", namespaces=NS), "|", (e.findtext("a:title", namespaces=NS) or "")[:120])
html = get("https://www.youtube.com/@TF1INFO/videos").decode("utf-8", "replace")
cid = re.search(r'"(?:externalId|channelId)":"(UC[\w-]{22})"', html)
print("channel id :", cid and cid.group(1))
if cid:
    flux("channel_id=" + cid.group(1))
    print("onglet playlists :")
    pl = get(f"https://www.youtube.com/channel/{cid.group(1)}/playlists").decode("utf-8", "replace")
    vus = []
    for m in re.finditer(r'"playlistId":"(PL[\w-]+)".{0,1500}?"title":\{"(?:simpleText|runs)":(?:"([^"]+)"|\[\{"text":"([^"]+)")', pl):
        if m.group(1) not in vus:
            vus.append(m.group(1)); print("  PL", m.group(1), m.group(2) or m.group(3))
    for m in re.finditer(r'(PL[\w-]{16,40})', pl):
        if m.group(1) not in vus:
            vus.append(m.group(1)); print("  PL?", m.group(1))
for p in sys.argv[1:]:
    if p.startswith("PL"):
        # identifiant éventuellement tronqué : on cherche les playlists qui commencent ainsi
        try:
            flux("playlist_id=" + p)
        except Exception as e:
            print(p, e)
print("== France 24")
u = "https://apis.france24.com/products/get_product/podcast-f24-fr-get-podcast-by-entreprise-id?token_application=33d60288-7e20-11e9-884b-005056a9c687&program.entrepriseId=W"
try:
    b = get(u); print(len(b), "octets"); print(b[:1500].decode("utf-8", "replace"))
except Exception as e:
    print("erreur", e)
