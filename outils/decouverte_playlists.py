"""Repérage : playlists YouTube des émissions politiques sur les chaînes des radios."""
import re, urllib.request, html
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36", "Accept-Language": "fr-FR,fr"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
CLES = re.compile(r"(?i)face à face|invit|interview|entretien|8h30|7h50|8h20|7h40|grand jury|matinale|politique|questions politiques")
for h in ["RMC", "BFMTV", "franceinter", "franceinfo", "Europe1", "SudRadioOfficiel", "sudradiofrance", "RTLfrance1", "RTL.fr", "radio_classique", "RFIfr", "rfi.fr"]:
    try:
        p = get(f"https://www.youtube.com/@{h}/playlists")
    except Exception as e:
        print(f"## @{h} : erreur {e}"); continue
    titre = re.search(r"<title>([^<]*)</title>", p)
    print(f"## @{h} : {titre.group(1) if titre else '?'}")
    vus = set()
    for m in re.finditer(r'"contentId":"(PL[\w-]+)".{0,4000}?"title":\{"content":"([^"]+)"', p):
        pid, t = m.group(1), html.unescape(m.group(2))
        if pid in vus: continue
        vus.add(pid)
        if CLES.search(t): print(f"   {pid} | {t}")
    print("   (playlists trouvées :", len(vus), ")")
    for m in re.finditer(r'"playlistId":"(PL[\w-]+)".{0,1500}?"title":\{"(?:simpleText|runs)":(?:"([^"]+)"|\[\{"text":"([^"]+)")', p):
        pid, t = m.group(1), html.unescape(m.group(2) or m.group(3) or "")
        if pid in vus: continue
        vus.add(pid)
        if CLES.search(t): print(f"   {pid} | {t}")
    for m in re.finditer(r'"title":"([^"]{3,90})"[^{}]{0,300}?"playlistId":"(PL[\w-]+)"', p):
        pid, t = m.group(2), html.unescape(m.group(1))
        if pid not in vus and CLES.search(t):
            vus.add(pid); print(f"   {pid} | {t}")
