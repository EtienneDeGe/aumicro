"""Repérage : lecture de la durée d'une vidéo YouTube depuis GitHub."""
import re, urllib.request
UA = {"User-Agent": "AuMicro/1.0 (https://etiennedege.github.io/aumicro/; recensement des invites politiques)", "Accept-Language": "fr-FR,fr"}
for v in ["GFTBHZH78LY", "EDgIBfffJmM", "VMF2zEw7mso"]:
    try:
        h = urllib.request.urlopen(urllib.request.Request("https://www.youtube.com/watch?v=" + v, headers=UA), timeout=30).read().decode("utf-8", "replace")
        m = re.search(r'"lengthSeconds":"(\d+)"', h); m2 = re.search(r'itemprop="duration" content="([^"]+)"', h); m3 = re.search(r'"approxDurationMs":"(\d+)"', h)
        print(v, len(h), "lengthSeconds", m and m.group(1), "| meta", m2 and m2.group(1), "| approx", m3 and m3.group(1), "| consent" if "consent" in h[:5000] else "")
    except Exception as e:
        print(v, "erreur", e)
