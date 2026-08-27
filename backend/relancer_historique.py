# Script ponctuel (pas une route API - trop long pour une requete HTTP,
# ~11 min sur toute la base) : recalcule la prediction de TOUS les films
# deja sortis (entrees_premiere_semaine connu) avec le modele actuellement
# charge, et stocke une nouvelle ligne Prediction pour chacun.
#
# Pourquoi : /predictions/relancer (backend/predictions_admin.py) ne
# predit que les films PAS ENCORE sortis - une fois qu'un film sort, ses
# lignes Prediction restent figees a la version du modele qui tournait
# au moment ou elles ont ete calculees. Apres plusieurs reentrainements
# (V1 a V5, cf rapport data science), l'historique melangeait donc des
# predictions de plusieurs generations de modele differentes - pas une
# vraie mesure de la precision du modele ACTUEL. Ce script remet tout
# l'historique sur la meme base : le modele courant, pour tous les films.
#
# Usage : docker compose exec backend python3 -m backend.relancer_historique
from datetime import UTC, datetime

from backend.moteur_prediction import predire
from database.base import SessionLocal
from database.models import Oeuvre, Prediction


def main():
    session = SessionLocal()
    try:
        films = (
            session.query(Oeuvre.id_oeuvre, Oeuvre.nom_francais)
            .filter(Oeuvre.entrees_premiere_semaine.isnot(None))
            .all()
        )
        print(f"{len(films)} films deja sortis a repasser dans le modele actuel...")

        maintenant = datetime.now(UTC)
        nombre_ok = 0
        nombre_erreurs = 0
        for i, (id_oeuvre, nom_francais) in enumerate(films, start=1):
            try:
                valeur_predite = predire(id_oeuvre)
            except ValueError:
                # film mal renseigne (pas assez d'infos pour les features) :
                # on le saute plutot que de faire planter tout le script
                nombre_erreurs += 1
                continue
            session.add(
                Prediction(
                    id_oeuvre=id_oeuvre,
                    nom_francais=nom_francais,
                    entrees_premiere_semaine_predites=valeur_predite,
                    date_prediction=maintenant,
                )
            )
            nombre_ok += 1
            if i % 1000 == 0:
                session.commit()
                print(f"  {i}/{len(films)}...")

        session.commit()
        print(f"\n{nombre_ok} predictions recalculees, {nombre_erreurs} films sautes (donnees incompletes)")
    finally:
        session.close()


if __name__ == "__main__":
    main()
