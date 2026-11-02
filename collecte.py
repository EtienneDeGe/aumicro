#!/usr/bin/env python3
"""Collecte quotidienne des invités politiques.

1. Lit les flux podcast des émissions (data/sources.json) : chaque épisode donne l'invité et le lien d'écoute.
2. Garde uniquement les personnalités politiques françaises (vérification sur Wikidata), avec photo libre.
3. Cherche la vidéo de l'interview sur les chaînes YouTube des radios.
4. Écrit les passages dans data/passages/AAAA-MM-JJ.json et un résumé dans resume.md (corps de la proposition à valider).

Usage : python collecte.py [--jours 3] [--depuis AAAA-MM-JJ] [--essai]
Seule la bibliothèque standard de Python est utilisée.
"""
import argparse, html, json, re, sys, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).parent
PARIS = ZoneInfo("Europe/Paris")
UA = {"User-Agent": "AuMicro/1.0 (https://etiennedege.github.io/aumicro/; recensement des invites politiques)",
      "Accept-Language": "fr-FR,fr"}
CACHE_F = RACINE / "data/cache_wikidata.json"


# ---------- utilitaires ----------
def lire(p):
    return json.loads((RACINE / p).read_text(encoding="utf-8"))


def ecrire(p, o):
    (RACINE / p).write_text(json.dumps(o, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get(url, essais=3):
    for i in range(essais):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
        except Exception as e:
            if i == essais - 1:
                raise
            time.sleep(2 * (i + 1))


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", sans_accents(s).lower()).strip()


def slugifier(s):
    return re.sub(r"[^a-z0-9]+", "-", sans_accents(s).lower()).strip("-")


def texte(h):
    h = re.sub(r"<[^>]+>", " ", h or "")
    return " ".join(html.unescape(h).split())


# ---------- extraction des noms ----------
MAJ = r"A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸ"
MOT = rf"[{MAJ}][a-zà-ÿ'’]+(?:-[{MAJ}]?[a-zà-ÿ'’]+)*"
PARTICULE = r"(?:de |du |des |d'|d’|de la |Le |La |Mc|Mac|Ben |Ould |Van |von |El |Al-)"
NOM_RE = re.compile(rf"\b({MOT}(?:\s+{PARTICULE}?{MOT}){{1,3}})")
MOTS_VIDES = {"Le", "La", "Les", "Un", "Une", "Avec", "Chaque", "Ecoutez", "Écoutez", "Retrouvez", "Sur", "Pour",
              "Face", "France", "Inter", "Sud", "Radio", "Europe", "Assemblée", "Sénat", "Parti", "République", "Matin"}


AVANT_ANIMATEUR = re.compile(r"(?:questions d[e'’]|au micro d[e'’]|présentée? par|animée? par|avec|interrogée? par|face à)\s*$", re.I)


def candidats(t):
    """Noms propres trouvés dans le texte, ceux de la forme « Nom, fonction » en premier."""
    vus, prioritaires, autres = set(), [], []
    for m in NOM_RE.finditer(t):
        mots = m.group(1).strip().split()
        while mots and mots[0] in MOTS_VIDES:
            mots = mots[1:]
        if len(mots) < 2:
            continue
        nom = " ".join(mots)
        debut = t.find(nom, m.start())
        avant = t[max(0, debut - 30):debut]
        if nom in vus or (AVANT_ANIMATEUR.search(avant) and not avant.rstrip().endswith(":")):
            continue
        vus.add(nom)
        (prioritaires if t[debut + len(nom):debut + len(nom) + 1] == "," else autres).append((nom, debut))
    return prioritaires + autres


FIN_FONCTION = re.compile(r"(?:^|,? )(?:rapporte|pointe|nie|débattent|appelle|alerte|estime|assure|regrette|confie|annonce|déclare|"
                          r"explique|dénonce|juge|affirme|plaide|souligne|considère|publie|défend|met en garde|s['’]inquiète|"
                          r"répond|est l['’]invit|est l|était|a salué|a |revient|réagit|invitée? |au micro|sur RTL|sur RMC|sur Europe|"
                          r"était|s['’]exprime|pour |qui |dans |face à|ce (?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)|"
                          r"était|et auteur|auteur d)|[.;:!?]")


FONCTION_POLITIQUE = re.compile(
    r"d[ée]put[ée]|ministre|s[ée]nat|maire|parti|porte-parole|candidat|conseill|élu|secrétaire (?:national|général|d['’]état)|"
    r"président(?:e)? (?:du groupe|des |de la région|du conseil|de région|du parti|du rassemblement|de l['’]assemblée|de la république)|"
    r"politique|homme d['’]état|femme d['’]état|LFI|\bRN\b|\bPS\b|\bLR\b|EELV|écologiste|insoumis|communiste|socialiste|"
    r"républicain|reconquête|renaissance|modem|horizons|gouvernement|chef de file|vice-président|adjoint|militant", re.I)


def fonction_apres(t, nom):
    i = t.find(nom)
    if i < 0:
        return None
    reste = t[i + len(nom):]
    if not reste.startswith(","):
        return None
    reste = reste[1:].strip()
    m = FIN_FONCTION.search(reste)
    f = (reste[:m.start()] if m else reste[:140]).strip(" ,").replace("«", "").replace("»", "").replace('"', "")
    f = " ".join(f.split())
    if f.count("(") > f.count(")"):
        f = f[:f.rfind("(")].strip(" ,")
    if 4 <= len(f) <= 160:
        return f[0].upper() + f[1:]
    return None


def animateur(t):
    m = re.search(r"(?:répond(?:ent)? aux questions d[e'’] ?|au micro d[e'’] ?)" + rf"({MOT}(?:\s+{PARTICULE}?{MOT}){{1,2}})", t)
    if m:
        return m.group(1)
    m = re.search(rf"^({MOT}(?:\s+{PARTICULE}?{MOT}){{1,2}}) reçoit", t)
    return m.group(1) if m else None


# ---------- Wikidata ----------
class Wikidata:
    API = "https://www.wikidata.org/w/api.php"

    def __init__(self):
        self.cache = json.loads(CACHE_F.read_text(encoding="utf-8")) if CACHE_F.exists() else {}
        self.modifie = False

    def api(self, **p):
        p.update(format="json", maxlag="5")
        for essai in range(5):
            time.sleep(0.4)
            r = json.loads(get(self.API + "?" + urllib.parse.urlencode(p)))
            if "error" not in r:
                return r
            time.sleep(3 * (essai + 1))
        raise RuntimeError(r["error"].get("info", "erreur Wikidata"))

    MANDATS = re.compile(r"ministre|député|sénat|maire|président de la république|secrétaire d['’]état|porte-parole du gouvernement|"
                         r"conseill(?:er|ère) (?:régional|départemental|municipal|de paris)|président du conseil|parlement européen|"
                         r"président de région|chef du gouvernement|haut-commissaire", re.I)

    def mandat_politique(self, positions):
        """Vrai si l'une des fonctions occupées (P39) est un mandat ou une fonction gouvernementale."""
        positions = [p for p in positions if p]
        if not positions:
            return False
        inconnues = [p for p in positions if ("pos:" + p) not in self.cache]
        for i in range(0, len(inconnues), 40):
            lot = inconnues[i:i + 40]
            ents = self.api(action="wbgetentities", ids="|".join(lot), props="labels", languages="fr|en")["entities"]
            for p in lot:
                lab = ents.get(p, {}).get("labels", {})
                self.cache["pos:" + p] = (lab.get("fr") or lab.get("en") or {}).get("value", "")
                self.modifie = True
        return any(self.MANDATS.search(self.cache["pos:" + p]) for p in positions)

    def politique(self, nom):
        """Renvoie {qid, nom, description, photo} si `nom` désigne une personnalité politique française, sinon None."""
        cle = norm(nom)
        if cle in self.cache:
            return self.cache[cle]
        res = None
        try:
            hits = self.api(action="wbsearchentities", search=nom, language="fr", uselang="fr", type="item", limit=5)["search"]
            ids = [h["id"] for h in hits if norm(h.get("label", "")) == cle or norm(h.get("match", {}).get("text", "")) == cle]
            if ids:
                ents = self.api(action="wbgetentities", ids="|".join(ids), props="claims|labels|descriptions", languages="fr")["entities"]
                for qid in ids:
                    e = ents[qid]
                    c = e.get("claims", {})
                    val = lambda p: [x["mainsnak"].get("datavalue", {}).get("value") for x in c.get(p, [])]
                    ids_de = lambda p: {v.get("id") for v in val(p) if isinstance(v, dict)}
                    humain = "Q5" in ids_de("P31")
                    francais = "Q142" in ids_de("P27")
                    politique = ("Q82955" in ids_de("P106") or bool(c.get("P102"))
                                 or self.mandat_politique(ids_de("P39")))
                    vivant = not c.get("P570")
                    if humain and francais and politique and vivant:
                        photo = (val("P18") or [None])[0]
                        res = {"qid": qid, "nom": e.get("labels", {}).get("fr", {}).get("value", nom),
                               "description": e.get("descriptions", {}).get("fr", {}).get("value"),
                               "photo_fichier": photo}
                        break
        except Exception as ex:
            print(f"  ! Wikidata indisponible pour {nom} : {ex}")
            return None  # pas de mise en cache en cas d'erreur
        self.cache[cle] = res
        self.modifie = True
        return res

    def photo(self, fichier):
        """URL d'une vignette Wikimedia Commons et crédit (auteur, licence)."""
        if not fichier:
            return None, None
        url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(fichier.replace(" ", "_")) + "?width=240"
        credit = None
        try:
            r = json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "query", "titles": "File:" + fichier, "prop": "imageinfo", "iiprop": "extmetadata", "format": "json"})))
            meta = next(iter(r["query"]["pages"].values()))["imageinfo"][0]["extmetadata"]
            auteur = texte(meta.get("Artist", {}).get("value", ""))[:80]
            licence = meta.get("LicenseShortName", {}).get("value", "")
            credit = ", ".join(x for x in (auteur, licence, "Wikimedia Commons") if x)
        except Exception:
            credit = "Wikimedia Commons"
        return url, credit

    def sauver(self):
        if self.modifie:
            CACHE_F.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


# ---------- flux podcast ----------
def url_flux(src):
    if src.get("flux"):
        return src["flux"]
    page = get(src["page"]).decode("utf-8", "replace")
    m = re.search(r'https://radiofrance-podcast\.net/podcast09/[\w-]+\.xml', page)
    if not m:
        raise RuntimeError("flux introuvable sur " + src["page"])
    return m.group(0)


def episodes(src):
    racine = ET.fromstring(get(url_flux(src)))
    lien_chaine = (racine.findtext("channel/link") or "").strip()
    for it in racine.iter("item"):
        try:
            quand = parsedate_to_datetime(it.findtext("pubDate")).astimezone(PARIS)
        except Exception:
            continue
        enc = it.find("enclosure")
        audio = enc.get("url") if enc is not None else None
        lien = (it.findtext("link") or "").strip()
        if src.get("replay") == "lien" and lien and lien.rstrip("/") != lien_chaine.rstrip("/"):
            ecouter = lien
        else:
            ecouter = audio or lien or None
        yield {"date": quand.date(), "titre": texte(it.findtext("title")), "desc": texte(it.findtext("description")),
               "ecouter": ecouter}


# ---------- YouTube ----------
YT_NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def videos(chaine):
    r = ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?channel_id=" + chaine))
    for e in r.findall("a:entry", YT_NS):
        yield {"titre": e.findtext("a:title", namespaces=YT_NS) or "",
               "date": datetime.fromisoformat(e.findtext("a:published", namespaces=YT_NS)).astimezone(PARIS).date(),
               "url": "https://www.youtube.com/watch?v=" + e.findtext("yt:videoId", namespaces=YT_NS)}


# ---------- programme principal ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jours", type=int, default=3, help="nombre de jours à remonter (défaut 3)")
    ap.add_argument("--depuis", help="date de début AAAA-MM-JJ (prioritaire sur --jours)")
    ap.add_argument("--essai", action="store_true", help="affiche le résultat sans rien écrire")
    a = ap.parse_args()
    aujourdhui = datetime.now(PARIS).date()
    debut = date.fromisoformat(a.depuis) if a.depuis else aujourdhui - timedelta(days=a.jours - 1)

    sources, emissions = lire("data/sources.json"), lire("data/emissions.json")
    personnes = lire("data/personnalites.json")
    exclus = {norm(n) for n in lire("data/exclus.json")["noms"]} if (RACINE / "data/exclus.json").exists() else set()
    par_qid = {p.get("wikidata"): s for s, p in personnes.items() if p.get("wikidata")}
    wd = Wikidata()
    nouveaux, completes, ecartes, prudence, erreurs = [], [], [], [], []
    jours_modifies = {}

    def jour(d):
        k = d.isoformat()
        if k not in jours_modifies:
            f = RACINE / f"data/passages/{k}.json"
            jours_modifies[k] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        return jours_modifies[k]

    # 1. Podcasts
    for src in sources["podcasts"]:
        em_id = src["emission"]
        em = emissions[em_id]
        print(f"\n== {em['nom']} ({em['radio']})")
        try:
            eps = [e for e in episodes(src) if debut <= e["date"] <= aujourdhui]
        except Exception as ex:
            erreurs.append(f"{em['nom']} : flux illisible ({ex})")
            print("  ! flux illisible :", ex)
            continue
        for ep in eps:
            t = f"{ep['desc']} {ep['titre']}"
            trouve = None
            anims = {norm(a) for a in re.split(r" et |, ", em.get("animateur") or "") if a}
            anim_ep = animateur(ep["desc"])
            if anim_ep:
                anims.add(norm(anim_ep))
            nom_cite = None
            for nom, _ in candidats(ep["desc"]) + candidats(ep["titre"]):
                if norm(nom) in exclus or norm(nom) in anims:
                    continue
                trouve = wd.politique(nom)
                if trouve:
                    nom_cite = nom
                    break
            if not trouve:
                ecartes.append(f"{ep['date']} · {em['nom']} : « {ep['titre'][:90]} »")
                print(f"  - {ep['date']} écarté : {ep['titre'][:80]}")
                continue
            fonction_ep = fonction_apres(ep["desc"], nom_cite) or fonction_apres(ep["titre"], nom_cite)
            # Prudence : homonymes, personnalités seulement citées dans le résumé
            if (fonction_ep and not FONCTION_POLITIQUE.search(fonction_ep)) or \
               (not fonction_ep and norm(nom_cite) not in norm(ep["titre"])):
                prudence.append(f"{ep['date']} · {em['nom']} : {trouve['nom']} ({fonction_ep or 'fonction non précisée'}) — « {ep['titre'][:80]} »")
                print(f"  ? {ep['date']} prudence : {trouve['nom']} — {fonction_ep}")
                continue
            # personnalité : existante ou nouvelle
            slug = par_qid.get(trouve["qid"])
            if not slug:
                slug = slugifier(trouve["nom"])
                if slug in personnes and personnes[slug].get("wikidata") not in (None, trouve["qid"]):
                    slug = f"{slug}-{trouve['qid'].lower()}"
                p = personnes.setdefault(slug, {"nom": trouve["nom"], "photo": None, "credit_photo": None})
                p["wikidata"] = trouve["qid"]
                if not p.get("photo") and trouve.get("photo_fichier"):
                    p["photo"], p["credit_photo"] = wd.photo(trouve["photo_fichier"])
                par_qid[trouve["qid"]] = slug
            fonction = fonction_ep or (trouve.get("description") or "").capitalize() or None
            liste = jour(ep["date"])
            existant = next((x for x in liste if x["emission"] == em_id and x["personne"] == slug), None)
            if existant:
                if not existant.get("ecouter") and ep["ecouter"]:
                    existant["ecouter"] = ep["ecouter"]
                    existant["statut"] = "confirme"
                    completes.append(f"{ep['date']} · {em['nom']} · {trouve['nom']} : lien d'écoute ajouté")
                continue
            x = {"heure": em.get("heure", "00:00"), "emission": em_id, "personne": slug, "fonction": fonction,
                 "ecouter": ep["ecouter"], "voir": None, "statut": "confirme"}
            anim = animateur(ep["desc"])
            if anim and anim != em.get("animateur") and norm(anim) != norm(trouve["nom"]):
                x["animateur"] = anim
            liste.append(x)
            nouveaux.append((ep["date"], em, trouve["nom"], fonction, ep["ecouter"]))
            print(f"  + {ep['date']} {trouve['nom']} — {fonction}")

    # 2. Vidéos YouTube pour les passages récents sans vidéo
    cache_videos = {}
    for d in [debut + timedelta(days=i) for i in range((aujourdhui - debut).days + 1)]:
        for x in jour(d):
            if x.get("voir"):
                continue
            radio = emissions[x["emission"]]["radio"]
            nom = personnes[x["personne"]]["nom"]
            nom_famille = norm(nom.split(" ", 1)[-1])
            for ch in sources["youtube"].get(radio, []):
                if ch not in cache_videos:
                    try:
                        cache_videos[ch] = list(videos(ch))
                    except Exception as ex:
                        erreurs.append(f"YouTube {ch} : {ex}")
                        cache_videos[ch] = []
                v = next((v for v in cache_videos[ch] if d <= v["date"] <= d + timedelta(days=1)
                          and f" {nom_famille} " in f" {norm(v['titre'])} "), None)
                if v:
                    x["voir"] = v["url"]
                    completes.append(f"{d} · {nom} : vidéo « {v['titre'][:80]} »")
                    break

    # 3. Écriture
    for k in list(jours_modifies):
        if not jours_modifies[k]:
            del jours_modifies[k]
    if a.essai:
        print("\n(essai : rien n'est écrit)")
    else:
        for k, liste in jours_modifies.items():
            liste.sort(key=lambda x: (x["heure"], x["emission"]))
            ecrire(f"data/passages/{k}.json", liste)
        ecrire("data/personnalites.json", dict(sorted(personnes.items())))
        wd.sauver()

    r = [f"## Collecte du {aujourdhui.strftime('%d/%m/%Y')}", ""]
    if nouveaux:
        r += [f"### {len(nouveaux)} nouveau{'x' if len(nouveaux) > 1 else ''} passage{'s' if len(nouveaux) > 1 else ''}", ""]
        r += [f"- **{d.strftime('%d/%m')}** · {em['heure'] if 'heure' in em else ''} · {em['nom']} : **{nom}** — {f or '_fonction à compléter_'}"
              + (f" ([écouter]({e}))" if e else "") for d, em, nom, f, e in sorted(nouveaux, key=lambda n: (n[0], n[1].get('heure', '')))]
        r.append("")
    if completes:
        r += ["### Compléments", ""] + [f"- {c}" for c in completes] + [""]
    if prudence:
        r += ["### Écartés par prudence (à ajouter à la main si ce sont bien des invités politiques)", ""]
        r += [f"- {p}" for p in prudence] + [""]
    if ecartes:
        r += ["<details><summary>Épisodes écartés (invité non reconnu comme personnalité politique)</summary>", ""]
        r += [f"- {e}" for e in ecartes] + ["", "</details>", ""]
    if erreurs:
        r += ["### Problèmes rencontrés", ""] + [f"- {e}" for e in erreurs] + [""]
    if not (nouveaux or completes):
        r.append("Rien de nouveau.")
    (RACINE / "resume.md").write_text("\n".join(r) + "\n", encoding="utf-8")
    print("\n" + "\n".join(r))


if __name__ == "__main__":
    main()
