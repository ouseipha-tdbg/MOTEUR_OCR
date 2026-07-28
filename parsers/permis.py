import re
from ._utils import find_after, find_dates, yam_id

PERMIS_NUM_RE = re.compile(r"\b([A-Z]?\d{6,12})\b")
CAT_RE = re.compile(r"\b(A1?|B|C1?|D1?|E|BE|CE|DE)\b")


def parse_permis(lines: list[str]) -> dict:
    joined = " ".join(lines)
    out = {
        "nom": find_after(lines, ["nom", "surname"]),
        "prenoms": find_after(lines, ["prenom", "prénoms"]),
        "date_naissance": "",
        "lieu_naissance": find_after(lines, ["lieu de naiss"]),
        "numero_permis": find_after(lines, ["n°", "numero"]),
        "categories": [],
        "date_delivrance": "",
        "date_expiration": "",
    }
    dates = find_dates(joined)
    if dates: out["date_naissance"] = dates[0]
    if len(dates) >= 2: out["date_delivrance"] = dates[1]
    if len(dates) >= 3: out["date_expiration"] = dates[2]

    if not out["numero_permis"]:
        m = PERMIS_NUM_RE.search(joined)
        if m: out["numero_permis"] = m.group(1)

    out["categories"] = sorted(set(CAT_RE.findall(joined)))

    out["yam_id"] = yam_id(out["numero_permis"] or f"{out['nom']}{out['prenoms']}")
    return out
