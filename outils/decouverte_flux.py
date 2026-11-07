"""Repérage : titres et descriptions d'un flux pour des mots donnés."""
import sys, re, html, urllib.request, xml.etree.ElementTree as ET
flux, mots = sys.argv[1], sys.argv[2:]
r = ET.fromstring(urllib.request.urlopen(urllib.request.Request(flux, headers={"User-Agent": "AuMicro/1.0"}), timeout=30).read())
for it in r.iter("item"):
    t = it.findtext("title") or ""; d = " ".join(html.unescape(re.sub("<[^>]+>", " ", it.findtext("description") or "")).split())
    if any(m.lower() in (t + " " + d).lower() for m in mots):
        print("·", (it.findtext("pubDate") or "")[:22], "|", t[:100], "\n     ", d[:260])
