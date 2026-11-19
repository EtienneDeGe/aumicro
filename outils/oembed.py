"""Titre, chaîne et date de publication d'une vidéo YouTube (oEmbed + flux de la chaîne)."""
import json, re, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36", "Accept-Language": "fr-FR,fr"}
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
for v in sys.argv[1:]:
    r = json.loads(get("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote("https://www.youtube.com/watch?v=" + v)))
    print(v, "|", r.get("author_name"), "|", r.get("author_url"), "|", r.get("title"))
    try:
        h = get(r["author_url"])
        cid = re.search(r'"(?:externalId|channelId)":"(UC[\w-]{22})"', h).group(1)
        f = ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?channel_id=" + cid).encode())
        print("  chaîne", cid)
        for e in f.findall("a:entry", NS):
            vid = e.findtext("yt:videoId", namespaces=NS)
            print("  ·", e.findtext("a:published", namespaces=NS)[:16], "|", vid, "|", e.findtext("a:title", namespaces=NS)[:110], "<==" if vid == v else "")
    except Exception as ex:
        print("  flux de la chaîne illisible :", ex)
