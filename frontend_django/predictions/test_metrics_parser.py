from predictions.metrics_parser import parser_metriques

EXEMPLE = """
# HELP http_requests_total Total number of requests
# TYPE http_requests_total counter
http_requests_total{handler="/predict",method="POST",status="2xx"} 3.0
http_requests_total{handler="/predict",method="POST",status="4xx"} 1.0
http_requests_total{handler="/health",method="GET",status="2xx"} 10.0
"""


def test_parser_metriques_compte_le_total_et_les_statuts():
    resultat = parser_metriques(EXEMPLE)
    assert resultat["total_requetes"] == 14
    assert resultat["par_statut"] == {"2xx": 13, "4xx": 1}
    assert resultat["requetes_predict"] == 4


def test_parser_metriques_texte_vide():
    resultat = parser_metriques("")
    assert resultat["total_requetes"] == 0
    assert resultat["par_statut"] == {}
    assert resultat["requetes_predict"] == 0
