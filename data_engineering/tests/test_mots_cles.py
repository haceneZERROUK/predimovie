# Test de _parser_reponse_llm avec une fausse reponse, pas de reseau
from data_engineering.mots_cles import _parser_reponse_llm


def test_parser_reponse_llm_coupe_a_3_mots_cles():
    assert _parser_reponse_llm("thriller, evasion, prison") == [
        "thriller",
        "evasion",
        "prison",
    ]


def test_parser_reponse_llm_ignore_les_espaces():
    assert _parser_reponse_llm("  amour , trahison , vengeance  ") == [
        "amour",
        "trahison",
        "vengeance",
    ]


def test_parser_reponse_llm_garde_seulement_3_mots_meme_si_plus():
    assert _parser_reponse_llm("un, deux, trois, quatre, cinq") == ["un", "deux", "trois"]


def test_parser_reponse_llm_ignore_les_morceaux_vides():
    assert _parser_reponse_llm("thriller,, prison") == ["thriller", "prison"]


def test_parser_reponse_llm_tronque_a_100_caracteres():
    mot_trop_long = "x" * 150
    resultat = _parser_reponse_llm(mot_trop_long)
    assert len(resultat[0]) == 100
