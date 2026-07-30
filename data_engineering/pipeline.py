# Ce module fait le lien entre JPBOX et TMDB : il récupère les infos
# des 2 sources, vérifie qu'elles parlent bien du même film, puis
# enregistre le tout dans la base de données (via les modèles SQLAlchemy).
from sqlalchemy.orm import Session

from data_engineering import jpbox, tmdb
from data_engineering.matching import meme_film
from database.models import (
    Acteur,
    ActeurOeuvre,
    Genre,
    GenreOeuvre,
    Nature,
    Oeuvre,
    Production,
    ProductionOeuvre,
    Realisateur,
    RealisateurOeuvre,
)


def _get_ou_creer_nature(session: Session, nom: str) -> Nature:
    """Retourne la Nature existante, ou la crée si elle n'existe pas encore."""
    nature = session.query(Nature).filter_by(nom_nature=nom).first()
    if nature is None:
        nature = Nature(nom_nature=nom)
        session.add(nature)
        session.flush()
    return nature


def _get_ou_creer_genre(session: Session, nom: str) -> Genre:
    genre = session.query(Genre).filter_by(nom_genre=nom).first()
    if genre is None:
        genre = Genre(nom_genre=nom)
        session.add(genre)
        session.flush()
    return genre


def _get_ou_creer_production(session: Session, nom_societe: str) -> Production:
    production = session.query(Production).filter_by(nom_societe=nom_societe).first()
    if production is None:
        production = Production(nom_societe=nom_societe)
        session.add(production)
        session.flush()
    return production


def _decouper_nom(nom_complet: str) -> tuple[str, str]:
    """Sépare 'Prénom Nom' en (prenom, nom). Simplification : ne gère pas
    bien les prénoms/noms composés, mais suffisant pour ce projet."""
    prenom, _, nom = nom_complet.partition(" ")
    return prenom, nom or prenom


def _get_ou_creer_acteur(session: Session, nom_complet: str) -> Acteur:
    prenom, nom = _decouper_nom(nom_complet)
    acteur = session.query(Acteur).filter_by(nom=nom, prenom=prenom).first()
    if acteur is None:
        acteur = Acteur(nom=nom, prenom=prenom)
        session.add(acteur)
        session.flush()
    return acteur


def _get_ou_creer_realisateur(session: Session, nom_complet: str) -> Realisateur:
    prenom, nom = _decouper_nom(nom_complet)
    realisateur = session.query(Realisateur).filter_by(nom=nom, prenom=prenom).first()
    if realisateur is None:
        realisateur = Realisateur(nom=nom, prenom=prenom)
        session.add(realisateur)
        session.flush()
    return realisateur


def enrichir_avec_tmdb(titre: str, annee: int | None) -> dict | None:
    """Cherche un film sur TMDB et récupère ses infos (synopsis, genres,
    casting, réalisateur). Retourne None si aucun film ne correspond vraiment."""
    resultat = tmdb.rechercher_film(titre, annee)
    if resultat is None or not meme_film(titre, annee, resultat):
        return None

    details = tmdb.get_details_film(resultat["id"])
    casting = tmdb.get_casting_film(resultat["id"])
    realisateurs = [p["name"] for p in casting.get("crew", []) if p.get("job") == "Director"]

    return {
        "id_tmdb": resultat["id"],
        "synopsis": details.get("overview"),
        "genres": [g["name"] for g in details.get("genres", [])],
        "productions": [p["name"] for p in details.get("production_companies", [])],
        # on ne garde que les 10 premiers acteurs, pas tout le casting
        "acteurs": [
            {"nom": p["name"], "role": p.get("character")} for p in casting.get("cast", [])[:10]
        ],
        "realisateurs": realisateurs,
    }


def sauvegarder_film(
    session: Session,
    id_jpbox: int | None,
    titre_francais: str,
    titre_original: str,
    annee_sortie: int | None,
    infos_tmdb: dict | None,
) -> Oeuvre:
    """Crée le film en base s'il n'existe pas encore (grâce à id_jpbox ou
    id_tmdb), sinon récupère la ligne déjà existante et la complète."""
    oeuvre = None
    if id_jpbox is not None:
        oeuvre = session.query(Oeuvre).filter_by(id_jpbox=id_jpbox).first()
    if oeuvre is None and infos_tmdb is not None:
        oeuvre = session.query(Oeuvre).filter_by(id_tmdb=infos_tmdb["id_tmdb"]).first()

    if oeuvre is None:
        nature = _get_ou_creer_nature(session, "Film")
        oeuvre = Oeuvre(
            nom_francais=titre_francais,
            nom_original=titre_original,
            annee_sortie=annee_sortie,
            id_jpbox=id_jpbox,
            nature=nature,
        )
        session.add(oeuvre)
        session.flush()

    if infos_tmdb is not None:
        oeuvre.id_tmdb = infos_tmdb["id_tmdb"]
        oeuvre.synopsis = infos_tmdb["synopsis"]

        for nom_genre in infos_tmdb["genres"]:
            genre = _get_ou_creer_genre(session, nom_genre)
            deja_liee = any(a.id_genre == genre.id_genre for a in oeuvre.genres_assoc)
            if not deja_liee:
                oeuvre.genres_assoc.append(GenreOeuvre(genre=genre))

        for nom_societe in infos_tmdb["productions"]:
            production = _get_ou_creer_production(session, nom_societe)
            deja_liee = any(
                a.id_production == production.id_production for a in oeuvre.productions_assoc
            )
            if not deja_liee:
                oeuvre.productions_assoc.append(ProductionOeuvre(production=production))

        for personne in infos_tmdb["acteurs"]:
            acteur = _get_ou_creer_acteur(session, personne["nom"])
            deja_liee = any(a.id_acteur == acteur.id_acteur for a in oeuvre.acteurs_assoc)
            if not deja_liee:
                oeuvre.acteurs_assoc.append(ActeurOeuvre(acteur=acteur, role=personne["role"]))

        for nom_complet in infos_tmdb["realisateurs"]:
            realisateur = _get_ou_creer_realisateur(session, nom_complet)
            deja_liee = any(
                a.id_realisateur == realisateur.id_realisateur for a in oeuvre.realisateurs_assoc
            )
            if not deja_liee:
                oeuvre.realisateurs_assoc.append(RealisateurOeuvre(realisateur=realisateur))

    session.flush()
    return oeuvre


def traiter_films_a_venir(session: Session) -> int:
    """Flux A : scrape les films bientôt en salle et les enregistre
    avec leurs infos TMDB. Retourne le nombre de films traités."""
    nb_films = 0
    for id_jpbox in jpbox.ids_films_a_venir():
        infos_jpbox = jpbox.details_film(id_jpbox)
        infos_tmdb = enrichir_avec_tmdb(infos_jpbox["titre_francais"], infos_jpbox["annee_sortie"])
        sauvegarder_film(
            session,
            id_jpbox=id_jpbox,
            titre_francais=infos_jpbox["titre_francais"],
            titre_original=infos_jpbox["titre_francais"],
            annee_sortie=infos_jpbox["annee_sortie"],
            infos_tmdb=infos_tmdb,
        )
        nb_films += 1
    session.commit()
    return nb_films


def traiter_entrees_semaine(session: Session, idsem: int, vue: int) -> int:
    """Flux B : scrape le classement hebdomadaire et enregistre
    entrees_premiere_semaine pour les films qui sortent tout juste
    (semaine_exploitation == 1). Retourne le nombre de films mis à jour."""
    nb_maj = 0
    for film in jpbox.classement_hebdo(idsem, vue):
        if film["semaine_exploitation"] != 1:
            continue  # on ne garde que la toute première semaine d'exploitation

        infos_tmdb = enrichir_avec_tmdb(film["titre_francais"], film["annee_sortie"])
        oeuvre = sauvegarder_film(
            session,
            id_jpbox=film["id_jpbox"],
            titre_francais=film["titre_francais"],
            titre_original=film["titre_original"],
            annee_sortie=film["annee_sortie"],
            infos_tmdb=infos_tmdb,
        )
        oeuvre.entrees_premiere_semaine = film["entrees_semaine"]
        nb_maj += 1

    session.commit()
    return nb_maj


def backfill(session: Session, idsem_debut: int, idsem_fin: int, vue: int) -> int:
    """Rattrapage historique : rejoue traiter_entrees_semaine sur une
    plage de semaines passées, pour avoir assez de données d'entraînement."""
    total = 0
    for idsem in range(idsem_debut, idsem_fin + 1):
        total += traiter_entrees_semaine(session, idsem, vue)
    return total
