# Parseur tout simple du texte expose par /metrics (format Prometheus).
# On ne veut que quelques chiffres pour une page "monitoring" basique,
# pas besoin d'une vraie lib Prometheus cote Django pour ca.
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
