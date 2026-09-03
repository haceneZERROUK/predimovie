# Parse le texte de /metrics pour en sortir 3-4 chiffres a afficher sur la
# page monitoring. Pas besoin d'une lib Prometheus pour ca.
import re

LIGNE_REQUETE = re.compile(
    r'^http_requests_total\{[^}]*handler="([^"]*)"[^}]*status="([^"]*)"[^}]*\}\s+([\d.]+)',
    re.MULTILINE,
)


def parser_metriques(texte: str) -> dict:
    total_requetes = 0
    par_statut = {}
    requetes_predict = 0

    for handler, statut, valeur in LIGNE_REQUETE.findall(texte):
        nombre = float(valeur)
        total_requetes += nombre
        par_statut[statut] = par_statut.get(statut, 0) + nombre
        if handler == "/predict":
            requetes_predict += nombre

    return {
        "total_requetes": int(total_requetes),
        "par_statut": {statut: int(n) for statut, n in par_statut.items()},
        "requetes_predict": int(requetes_predict),
    }
