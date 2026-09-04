# Repare les films qui portent l'id_tmdb d'un autre film.
#
# Le rapprochement rapprochait "Toy Story 5" de la fiche "Toy Story", et la
# suite heritait du synopsis, du casting, du budget et des mots-cles de
# l'original. meme_film() ne le fait plus, mais les lignes deja en base
# gardent leur mauvais identifiant.
#
#   python -m data_engineering.corriger_suites              # rapport seul
#   python -m data_engineering.corriger_suites --appliquer  # repare
#
# On repere les cas sans appeler TMDB : deux oeuvres qui partagent un
# id_tmdb avec des numeros de suite differents, l'une des deux se trompe.
# On ne demande la fiche a TMDB que pour ces cas-la, pour savoir laquelle.
import sys
from collections import defaultdict

from data_engineering import tmdb
from data_engineering.matching import numero_de_suite
from data_engineering.pipeline import _enrichir_oeuvre, enrichir_avec_tmdb
from database.base import SessionLocal
from database.models import Oeuvre


def _oeuvres_mal_rapprochees(session) -> list[tuple[Oeuvre, int | None]]:
    """Les oeuvres dont le numero de suite ne colle pas a celui de la fiche
    TMDB qu'elles portent. Renvoie (oeuvre, numero attendu par la fiche)."""
    par_tmdb = defaultdict(list)
    for oeuvre in session.query(Oeuvre).filter(Oeuvre.id_tmdb.isnot(None)).all():
        par_tmdb[oeuvre.id_tmdb].append(oeuvre)

    suspects = []
    for id_tmdb, oeuvres in par_tmdb.items():
        numeros = {numero_de_suite(o.nom_francais or "") for o in oeuvres}
        if len(numeros) < 2:
            continue  # tout le monde est d'accord, rien a verifier
        # une seule requete par groupe : le titre de la fiche tranche
        try:
            titre_fiche = tmdb.get_details_film(id_tmdb).get("title", "")
        except Exception as erreur:  # noqa: BLE001 - on continue sur les autres
            print(f"  fiche {id_tmdb} illisible ({erreur}), ignoree")
            continue
        attendu = numero_de_suite(titre_fiche)
        for oeuvre in oeuvres:
            if numero_de_suite(oeuvre.nom_francais or "") != attendu:
                suspects.append((oeuvre, titre_fiche))
    return suspects


def main(appliquer: bool = False) -> int:
    session = SessionLocal()
    try:
        suspects = _oeuvres_mal_rapprochees(session)
        if not suspects:
            print("Aucun film mal rapproche.")
            return 0

        for oeuvre, titre_fiche in suspects:
            print(
                f"  id_oeuvre={oeuvre.id_oeuvre} « {oeuvre.nom_francais} » "
                f"porte la fiche {oeuvre.id_tmdb} « {titre_fiche} »"
            )

        if not appliquer:
            print(f"\n{len(suspects)} film(s) a rerapprocher. Relancer avec --appliquer.")
            return 0

        nb_repares, nb_vides = 0, 0
        for oeuvre, _ in suspects:
            infos = enrichir_avec_tmdb(oeuvre.nom_francais, oeuvre.annee_sortie)
            if infos is None:
                # aucune fiche ne correspond : mieux vaut pas de fiche du
                # tout que celle d'un autre film, le film sort alors des
                # ecrans qui exigent une fiche complete
                oeuvre.id_tmdb = None
                nb_vides += 1
            else:
                _enrichir_oeuvre(session, oeuvre, infos)
                nb_repares += 1
        session.commit()
        print(f"\n{nb_repares} film(s) rerapproche(s), {nb_vides} laisse(s) sans fiche.")
        return nb_repares + nb_vides
    finally:
        session.close()


if __name__ == "__main__":
    main(appliquer="--appliquer" in sys.argv)
