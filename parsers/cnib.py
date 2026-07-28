"""Parser CNIB Burkina Faso — extraction robuste 19 champs.

Stratégie :
1. Regex ciblées d'abord (numéros, dates, patterns spécifiques CNIB)
2. Fallback labels textuels (find_after)
3. Fallback MRZ pour nom/prénoms/dates si recto mal lu ou prénoms collés
4. Normalisation (espaces, format téléphone, split province/dept)
"""
import re
from ._utils import (
    DATE_RE, NIP_RE, find_after, find_dates, yam_id,
    parse_mrz_id, extract_mrz_lines,
)

# Numéro CNIB burkinabé : 15-18 chiffres (ex: 03010400226014499)
CNIB_NUM_RE = re.compile(r"\b(\d{15,18})\b")
# Numéro série court B8564132
SERIE_RE = re.compile(r"\b([A-Z]\d{6,10})\b")
SEXE_RE = re.compile(r"\b(M|F|MASCULIN|FEMININ)\b", re.I)
TAILLE_RE = re.compile(r"(\d{2,3})\s*cm", re.I)
TEL_RE = re.compile(r"(?:tel|tél|téléphone|phone)[^\d]*(\d[\d\s.\-]{6,})", re.I)
# Lieu de naissance : "Né(e) le DD/MM/YYYY A LIEU" ou " À LIEU "
LIEU_RE = re.compile(r"(?:né|née|ne|nee)e?\s*(?:le)?\s*\d{2}[./\- ]\d{2}[./\- ]\d{4}\s*(?:[àa])\s+([A-Z][A-ZÀ-Ÿ\-\s]{2,30})", re.I)
LIEU_A_RE = re.compile(r"\b[àa]\s+([A-Z][A-ZÀ-Ÿ]{3,})\b")
# Ville en majuscules isolée
VILLE_MAJ_RE = re.compile(r"\b(OUAGADOUGOU|BOBO[- ]DIOULASSO|KOUDOUGOU|BANFORA|OUAHIGOUYA|KAYA|DEDOUGOU|FADA|TENKODOGO|MANGA|ZINIARE|BOROMO|DIAPAGA|DORI|GAOUA|LEO|NOUNA|ORODARA|POUYTENGA|SAPONE|TITAO|TOUGAN|YAKO|BOGANDE|BOULSA|DJIBO|SEBBA|KOMBISSIRI|KONGOUSSI|POBE|REO|SINDOU|SOLENZO|KOUPELA|PO)\b")

PROFESSION_KEYS = [
    "profession", "prolession", "proiession", "proiesion",  # OCR errors
    "profesion", "activite", "activité", "métier", "metier", "occupation"
]


def parse_cnib(lines: list[str]) -> dict:
    joined = " ".join(lines)
    mrz = extract_mrz_lines(lines)
    mrz_data = parse_mrz_id(mrz)

    out = {
        # Identité
        "nom": find_after(lines, ["nom", "surname"]),
        "prenoms": find_after(lines, ["prenoms", "prénoms", "prenom", "given names"]),
        "date_naissance": find_after(lines, ["ne le", "née le", "né le", "date de naiss", "born"]),
        "lieu_naissance": "",
        "sexe": "",
        "taille": "",
        "profession": find_after(lines, PROFESSION_KEYS),
        # Numéros
        "numero_cnib": "",
        "numero_serie": "",
        "nationalite": mrz_data.get("nationalite", "BFA"),
        # Dates
        "date_delivrance": find_after(lines, ["delivre le", "délivrée le", "issued"]),
        "date_expiration": find_after(lines, ["expire le", "expiry"]),
        # Verso
        "province": find_after(lines, ["province"]),
        "departement": find_after(lines, ["departement", "département"]),
        "residence": find_after(lines, ["residence", "résidence"]),
        "personne_prevenir": find_after(lines, ["personne", "prevenir", "prévenir"]),
        "telephone": "",
        # MRZ
        "mrz": mrz,
        "mrz_doc_number": mrz_data.get("mrz_doc_number", ""),
    }

    # ---- Dates par ordre chrono (fallback) ----
    dates = find_dates(joined)
    if dates and not out["date_naissance"]:
        out["date_naissance"] = dates[0]
    if len(dates) >= 2 and not out["date_delivrance"]:
        out["date_delivrance"] = dates[1]
    if len(dates) >= 3 and not out["date_expiration"]:
        out["date_expiration"] = dates[2]

    # ---- Numéros ----
    nums = CNIB_NUM_RE.findall(joined)
    if nums:
        nums_sorted = sorted(nums, key=len, reverse=True)
        out["numero_cnib"] = nums_sorted[0]
    m = SERIE_RE.search(joined)
    if m:
        out["numero_serie"] = m.group(1)

    # ---- Nettoyer les dates si un numéro est collé (Gemini fait souvent ça) ----
    for k in ("date_naissance", "date_delivrance", "date_expiration"):
        v = out.get(k, "")
        if not v:
            continue
        # Cas "14/06/2026 B 8564132" -> date + série
        m = re.match(r"(\d{2}[./\- ]\d{2}[./\- ]\d{4})\s+([A-Z]\s*\d{6,10})", v)
        if m:
            out[k] = m.group(1)
            if not out["numero_serie"]:
                out["numero_serie"] = m.group(2).replace(" ", "")
            continue
        # Garde juste la date si autre chose est collé
        m = re.search(r"(\d{2}[./\- ]\d{2}[./\- ]\d{4})", v)
        if m and m.group(1) != v:
            out[k] = m.group(1)

    # ---- Sexe ----
    m = SEXE_RE.search(joined)
    if m:
        out["sexe"] = m.group(1)[0].upper()
    elif mrz_data.get("sexe_mrz"):
        out["sexe"] = mrz_data["sexe_mrz"]

    # ---- Taille ----
    m = TAILLE_RE.search(joined)
    if m:
        out["taille"] = f"{m.group(1)} cm"

    # ---- Lieu de naissance ----
    # 1. Pattern "Né(e) le DD/MM/YYYY A LIEU"
    m = LIEU_RE.search(joined)
    if m:
        out["lieu_naissance"] = _clean(m.group(1))
    # 2. Fallback : chercher "A OUAGADOUGOU" pattern
    if not out["lieu_naissance"]:
        m = VILLE_MAJ_RE.search(joined)
        if m:
            out["lieu_naissance"] = m.group(1)

    # ---- Téléphone ----
    m = TEL_RE.search(joined)
    if m:
        out["telephone"] = _format_tel(m.group(1))
    else:
        # fallback : chercher "TEL XX XX XX XX" ou 8 chiffres consécutifs après "tel"
        m = re.search(r"(?:tel|tél)[^\d]*(\d[\d\s.\-]{6,})", joined, re.I)
        if m:
            out["telephone"] = _format_tel(m.group(1))

    # ---- Fallback MRZ pour nom/prénoms/dates ----
    prenoms_mrz = mrz_data.get("prenoms_mrz", "")
    nom_mrz = mrz_data.get("nom_mrz", "")

    # Nom : si vide OU pas cohérent avec MRZ
    if not out["nom"] and nom_mrz:
        out["nom"] = nom_mrz

    # Prénoms : si vide OU collés (>8 chars sans espace) → priorité MRZ
    if prenoms_mrz and (not out["prenoms"] or (len(out["prenoms"]) > 8 and " " not in out["prenoms"])):
        out["prenoms"] = prenoms_mrz

    if not out["date_naissance"] and mrz_data.get("date_naissance_mrz"):
        out["date_naissance"] = mrz_data["date_naissance_mrz"]
    if not out["date_expiration"] and mrz_data.get("date_expiration_mrz"):
        out["date_expiration"] = mrz_data["date_expiration_mrz"]

    # ---- Split province/departement si collés ("KADIOGO.OUAGADOUGOU" ou "KADIOGO, OUAGADOUGOU") ----
    if out["province"] and (out["province"] == out["departement"] or re.search(r"[.,;]", out["province"])):
        parts = re.split(r"[.,;/]\s*", out["province"])
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            out["province"] = parts[0]
            out["departement"] = parts[1]

    # ---- Split personne_prevenir si contient un lien + nom ("KAFANDO PAUL") ----
    if out["personne_prevenir"]:
        out["personne_prevenir"] = _split_camel(_clean(out["personne_prevenir"]))

    # ---- Nettoyage résidence ----
    if out["residence"]:
        out["residence"] = _clean(out["residence"])
        # remplace "." et virgules collées par ", "
        out["residence"] = re.sub(r"\s*[.,]\s*", ", ", out["residence"]).strip(", ")

    # ---- Profession : fallback si label mal lu ----
    if not out["profession"]:
        # cherche mot en majuscules seul entre 4-15 chars entouré de labels connus
        m = re.search(r"(?:élève|eleve|etudiant|étudiant|commercant|commerçant|fonctionnaire|enseignant|medecin|médecin|ingenieur|ingénieur|infirmier|comptable|informaticien|entrepreneur|artisan|agriculteur|chauffeur|menuisier|electricien|maçon)", joined, re.I)
        if m:
            out["profession"] = m.group(0).upper()

    # ---- NIP ----
    m = NIP_RE.search(joined)
    if m:
        out["nip"] = m.group(1)

    return out


def _clean(s: str) -> str:
    """Enlève les caractères parasites en début/fin."""
    return s.strip(" \t\n\r.,;:!?—-").strip()


def _format_tel(s: str) -> str:
    """Normalise un téléphone BF (8 chiffres) au format XX XX XX XX."""
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:
        return f"{digits[:2]} {digits[2:4]} {digits[4:6]} {digits[6:]}"
    if len(digits) == 11 and digits.startswith("226"):  # +226
        d = digits[3:]
        return f"+226 {d[:2]} {d[2:4]} {d[4:6]} {d[6:]}"
    return s.strip()


def _split_camel(s: str) -> str:
    """KAFANDOPAUL -> KAFANDO PAUL (insère espace avant majuscule qui suit >=4 majuscules)."""
    if " " in s or len(s) < 8:
        return s
    # Insère un espace après une séquence 4+ de majuscules suivie d'une majuscule + minuscules
    # Simple heuristique : split si tout est majuscule et long
    if s.isupper() and len(s) > 8:
        # tenter split à mi-parcours si pas de séparateur naturel
        # ex: KAFANDOPAUL -> split au milieu approximatif
        # meilleure heuristique : chercher un point où insérer 1 espace
        for i in range(4, len(s) - 3):
            # heuristique : si le mot restant est un prénom court connu
            if s[i:] in ("PAUL", "JEAN", "MARIE", "PIERRE", "PAULINE", "JACQUES", "MOUSSA", "SALIF", "ISSA", "IBRAHIM", "ADAMA", "RASMANE", "OUSMANE", "ABDOUL", "MAHAMADOU"):
                return f"{s[:i]} {s[i:]}"
    return s
