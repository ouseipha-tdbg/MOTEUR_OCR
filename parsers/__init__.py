from .cnib import parse_cnib
from .passport import parse_passport
from .rccm import parse_rccm
from .facture import parse_facture
from .permis import parse_permis
from .onea import parse_onea
from .sonabel import parse_sonabel

REGISTRY = {
    "cnib":     parse_cnib,
    "passport": parse_passport,
    "rccm":     parse_rccm,
    "facture":  parse_facture,
    "permis":   parse_permis,
    "onea":     parse_onea,
    "sonabel":  parse_sonabel,
}


def parse(doc_type: str, lines: list[str]) -> dict:
    fn = REGISTRY.get(doc_type)
    if not fn:
        return {"error": f"doc_type inconnu: {doc_type}"}
    return fn(lines)
