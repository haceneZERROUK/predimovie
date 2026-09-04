# Repere (et supprime, si on le demande) les films entres plusieurs fois en
# base sous des id_jpbox differents.
#
# Le correctif dans pipeline.py empeche d'en creer de nouveaux et celui de
# l'API les masque a l'affichage, mais les lignes deja enregistrees restent.
# Ce script sert a les enlever pour de bon.
#
#   python -m data_engineering.nettoyer_doublons              # rapport seul
#   python -m data_engineering.nettoyer_doublons --appliquer  # supprime
#
# On garde la ligne qui a le plus d'entrees reelles : c'est l'exploitation
# principale, celle qui a du sens dans l'historique predit/reel.
import sys
from collections import defaultdict

from data_engineering.matching import nettoyer_annotations, normaliser_titre
from database.base import SessionLocal
from database.models import (
    ActeurOeuvre,
    GenreOeuvre,
    Oeuvre,
    Prediction,
    ProductionOeuvre,
    RealisateurOeuvre,
)

# tout ce qui pointe vers une oeuvre et doit partir avec elle
TABLES_LIEES = (GenreOeuvre, ActeurOeuvre, RealisateurOeuvre, ProductionOeuvre, Prediction)


def _groupes_de_doublons(session) -> list[list[Oeuvre]]:
    """Regroupe les oeuvres qui ont le meme titre et la meme date de sortie.

    On ne regroupe pas sur id_tmdb, alors que ce serait plus direct : le
    rapprochement TMDB est flou et donne le meme id a des films
    differents ("Toy Story 5" pointe sur la fiche de "Toy Story"). Un
    regroupement sur cet identifiant proposerait de supprimer des suites.

    La date fait partie de la cle, donc une reprise en salle, qui sort des
    annees apres, reste une ligne a part."""
    par_cle = defaultdict(list)
    for oeuvre in session.query(Oeuvre).filter(Oeuvre.date_sortie.isnot(None)).all():
        titre = normaliser_titre(nettoyer_annotations(oeuvre.nom_francais or ""))
        if titre:
            par_cle[(titre, oeuvre.date_sortie)].append(oeuvre)
    return [groupe for groupe in par_cle.values() if len(groupe) > 1]


def _a_garder(groupe: list[Oeuvre]) -> Oeuvre:
    """La ligne avec le plus d'entrees reelles. A egalite, la plus ancienne
    (id le plus petit), pour que deux executions donnent le meme resultat."""
    return max(groupe, key=lambda o: (o.entrees_premiere_semaine or 0, -o.id_oeuvre))


def main(appliquer: bool = False) -> int:
    session = SessionLocal()
    try:
        groupes = _groupes_de_doublons(session)
        if not groupes:
            print("Aucun doublon trouve.")
            return 0

        nb_supprimables = 0
        for groupe in groupes:
            garde = _a_garder(groupe)
            print(f"\n{garde.nom_francais} (id_tmdb={garde.id_tmdb})")
            for oeuvre in sorted(groupe, key=lambda o: o.id_oeuvre):
                marque = "GARDE " if oeuvre is garde else "SUPPR."
                print(
                    f"  {marque} id_oeuvre={oeuvre.id_oeuvre} id_jpbox={oeuvre.id_jpbox} "
                    f"sortie={oeuvre.date_sortie} entrees={oeuvre.entrees_premiere_semaine} "
                    f"| {oeuvre.nom_francais}"
                )
                if oeuvre is not garde:
                    nb_supprimables += 1

        if not appliquer:
            print(f"\n{nb_supprimables} ligne(s) a supprimer. Relancer avec --appliquer.")
            return 0

        for groupe in groupes:
            garde = _a_garder(groupe)
            for oeuvre in groupe:
                if oeuvre is garde:
                    continue
                # les tables liees d'abord : il n'y a pas de suppression en
                # cascade sur ces relations, la contrainte sauterait
                for table in TABLES_LIEES:
                    session.query(table).filter_by(id_oeuvre=oeuvre.id_oeuvre).delete()
                session.delete(oeuvre)
        session.commit()
        print(f"\n{nb_supprimables} ligne(s) supprimee(s).")
        return nb_supprimables
    finally:
        session.close()


if __name__ == "__main__":
    main(appliquer="--appliquer" in sys.argv)
