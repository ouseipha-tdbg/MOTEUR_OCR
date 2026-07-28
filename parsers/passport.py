import re
from ._utils import find_after, find_dates, yam_id

MRZ_LINE_RE = re.compile(r"^[A-Z0-9<]{30,44}$")


def parse_passport(lines: list[str]) -> dict:
    joined = " ".join(lines)
    dates = find_dates(joined)

    out = {
        "nom": find_after(lines, ["nom", "surname"]),
        "prenoms": find_after(lines, ["prenom", "given names"]),
        "date_naissance": dates[0] if dates else "",
        "date_delivrance": dates[1] if len(dates) >= 2 else "",
        "date_expiration": dates[2] if len(dates) >= 3 else "",
        "numero_passeport": find_after(lines, ["passport no", "n° passeport", "numero"]),
        "nationalite": find_after(lines, ["nationalite", "nationality"]),
        "sexe": "",
        "mrz": [l for l in lines if MRZ_LINE_RE.match(l.replace(" ", ""))],
    }
    # MRZ parsing basique
    if len(out["mrz"]) >= 2:
        l1, l2 = out["mrz"][0], out["mrz"][1]
        # Nom / prénoms depuis MRZ ligne 1
        if l1.startswith("P<"):
            try:
                names = l1[5:].split("<<", 1)
                if len(names) == 2:
                    out["nom"] = out["nom"] or names[0].replace("<", " ").strip()
                    out["prenoms"] = out["prenoms"] or names[1].replace("<", " ").strip()
            except Exception:
                pass
        # N° passeport = 9 premiers caractères ligne 2
        if not out["numero_passeport"]:
            out["numero_passeport"] = l2[:9].replace("<", "")

    out["yam_id"] = yam_id(out["numero_passeport"] or f"{out['nom']}{out['prenoms']}")
    return out
