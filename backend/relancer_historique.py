# Script a lancer a la main (~11 min, trop long pour une route HTTP) :
# repasse tous les films deja sortis dans le modele actuel, pour que
# l'historique ne melange plus des predictions faites avec des versions
# differentes du modele.
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
                # film trop mal renseigne, on le saute
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
        print(
            f"\n{nombre_ok} predictions recalculees, {nombre_erreurs} films sautes "
            "(donnees incompletes)"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
