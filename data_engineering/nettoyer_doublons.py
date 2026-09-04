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

from data_engineering.pipeline import ECART_MEME_SORTIE
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
    """Regroupe les oeuvres qui partagent un id_tmdb et dont les dates de
    sortie tombent dans la meme semaine. Deux sorties eloignees dans le
    temps sont une reprise en salle, pas un doublon : on les laisse."""
    par_tmdb = defaultdict(list)
    for oeuvre in session.query(Oeuvre).filter(Oeuvre.id_tmdb.isnot(None)).all():
        par_tmdb[oeuvre.id_tmdb].append(oeuvre)

    groupes = []
    for oeuvres in par_tmdb.values():
        if len(oeuvres) < 2:
            continue
        datees = sorted((o for o in oeuvres if o.date_sortie), key=lambda o: o.date_sortie)
        # on avance dans le temps et on coupe des qu'un ecart depasse la
        # semaine : ce qui reste ensemble est un vrai doublon
        courant = []
        for oeuvre in datees:
            if courant and oeuvre.date_sortie - courant[0].date_sortie > ECART_MEME_SORTIE:
                if len(courant) > 1:
                    groupes.append(courant)
                courant = []
            courant.append(oeuvre)
        if len(courant) > 1:
            groupes.append(courant)
    return groupes


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
                    f"sortie={oeuvre.date_sortie} entrees={oeuvre.entrees_premiere_semaine}"
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
