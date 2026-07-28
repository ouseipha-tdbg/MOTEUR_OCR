"""Parser ONEA — identification client (KYC/KYB), regex ultra-tolérantes.

Zone cible sur toutes les factures : bloc "Client :" (nom + parcelle SECT/LOT/PLE)
+ N° abonné, contrat, compteur. Pas de montants (inutiles pour le KYC).
"""
import re
from ._utils import fuzzy_client

# N° abonné : 14 chiffres, espacés (1301 52 45 2470 01) OU compacts (17015245207001)
ABONNE_SPACED_RE = re.compile(r"(\d[\d\s.,#\-]{12,32}\d)")
# Contrat : FE/FT + alphanum, points/espaces parasites tolérés (FE674C.5007931)
CONTRAT_RE = re.compile(r"\bF[TE]\s*[:#\-]?\s*(\d{3}[A-Z0-9.]{5,13}\d)", re.I)
# Fallback : préfixe FE perdu par l'OCR ('E674C5007931', '674CL5007931' nu)
# structure spécifique : 3 chiffres + 1-2 lettres + 6-8 chiffres
CONTRAT_FALLBACK_RE = re.compile(r"\b[FE]{0,2}(\d{3}[A-Z]{1,2}\.?\d{6,8})\b", re.I)
# Parcelle propre : SECT 11 LOT 02 PLE 44 (tolérant sur SECT : SEIT, SBCT...)
PARCELLE_RE = re.compile(
    r"(S\w{2,5}[\.\s#]*\d{1,3}[\.\s#]*L[O0]T[\.\s#]*\d{1,3}[\.\s#]*(?:PLE|PARC[A-Z]*|P)[\.\s#]*\d{1,4})",
    re.I
)
# Parcelle dégradée (matriciel + photo rotée) : fragment ancré sur PLE+chiffres
# ex OCR réels : "SETLOD2PLE44", "TD2PLE44" = "SECT 11 LOT 02 PLE 44"
PARCELLE_DEGRADEE_RE = re.compile(r"([A-Z0-9]{0,12})PLE\s*(\d{1,4})\b", re.I)


def _abonne_14(lines: list[str], joined: str) -> str:
    # 1) segment alphanumérique dont les chiffres font exactement 14
    for l in lines:
        for seg in re.split(r"[^\d\s.,\-]+", l):
            digits = re.sub(r"\D", "", seg)
            if len(digits) == 14:
                return digits
    # 2) fallback : séquence espacée dans le texte joint
    for m in ABONNE_SPACED_RE.finditer(joined):
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) == 14:
            return digits
    return ""


def parse_onea(lines: list[str]) -> dict:
    joined = " ".join(lines)

    out = {
        "fournisseur": "ONEA",
        "client": "",
        "numero_abonne": "",
        "numero_contrat": "",
        "parcelle": "",
    }

    digits = _abonne_14(lines, joined)
    if digits:
        out["numero_abonne"] = f"{digits[:4]} {digits[4:6]} {digits[6:8]} {digits[8:12]} {digits[12:]}"

    # Contrat FE/FT (F souvent lu T/E ; points et lettres dans le numéro)
    m = CONTRAT_RE.search(joined) or CONTRAT_FALLBACK_RE.search(joined)
    if m:
        out["numero_contrat"] = "FE " + re.sub(r"[^A-Z0-9]", "", m.group(1).upper())

    # Client : fuzzy ZAMAPAY (ZAHAPAY, ZANAPAY...), sinon ligne débutant par "Client"
    out["client"] = fuzzy_client(joined)
    if not out["client"]:
        for l in lines:
            low = l.lower().strip()
            if low.startswith(("client", "clent", "cient")):  # typos OCR
                v = re.sub(r"^\W*c\w{3,5}t?\s*:?\s*", "", l, flags=re.I).strip()
                if len(v) > 2:
                    out["client"] = v
                    break

    # Parcelle : forme propre, sinon fragment dégradé (toujours mieux que vide)
    m = PARCELLE_RE.search(joined)
    if m:
        nums = re.findall(r"\d+", m.group(1))
        if len(nums) == 3:
            out["parcelle"] = f"SECT {nums[0]} LOT {nums[1]} PLE {nums[2]}"
        else:
            out["parcelle"] = re.sub(r"[\s#]+", " ", m.group(1)).upper()
    else:
        m = PARCELLE_DEGRADEE_RE.search(joined)
        # garde-fou : le fragment avant PLE doit contenir un chiffre ou débuter par S
        if m and (any(c.isdigit() for c in m.group(1)) or m.group(1).upper().startswith("S")):
            out["parcelle"] = f"{m.group(1)}PLE{m.group(2)}".upper() + " (partiel)"

    return out
