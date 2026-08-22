# Ce module fait le lien entre JPBOX et TMDB : il récupère les infos
# des 2 sources, vérifie qu'elles parlent bien du même film, puis
# enregistre le tout dans la base de données (via les modèles SQLAlchemy).
from datetime import date

from sqlalchemy.orm import Session

from data_engineering import imdb, jpbox, tmdb
from data_engineering.matching import meme_film, nettoyer_annotations
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
    casting, réalisateur). Retourne None si aucun film ne correspond vraiment.

    On regarde tous les résultats TMDB, pas que le premier : pour un titre
    générique (ex: "Who"), le bon film n'est pas toujours en tête."""
    titre_recherche = nettoyer_annotations(titre)
    resultat = next(
        (
            candidat
            for candidat in tmdb.rechercher_films(titre_recherche, annee)
            if meme_film(titre, annee, candidat)
        ),
        None,
    )
    if resultat is None:
        return None

    details = tmdb.get_details_film(resultat["id"])
    casting = tmdb.get_casting_film(resultat["id"])
    realisateurs = [p["name"] for p in casting.get("crew", []) if p.get("job") == "Director"]

    # Le texte JPBOX ne donne pas toujours l'année (titre tronqué, pas de
    # parenthèse...). TMDB donne une vraie date de sortie, plus fiable.
    # On gardait avant seulement l'année en jetant le jour/mois : corrigé,
    # on garde la date complète (utile pour savoir quel film sort quel
    # mercredi, pas juste quelle année).
    texte_date_sortie = details.get("release_date") or ""
    date_sortie_tmdb = date.fromisoformat(texte_date_sortie) if texte_date_sortie else None
    annee_sortie_tmdb = date_sortie_tmdb.year if date_sortie_tmdb else None

    return {
        "id_tmdb": resultat["id"],
        "imdb_id": details.get("imdb_id"),
        "annee_sortie": annee_sortie_tmdb,
        "date_sortie": date_sortie_tmdb,
        "synopsis": details.get("overview"),
        "note_tmdb": details.get("vote_average"),
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
    notes_imdb: dict | None = None,
) -> Oeuvre:
    """Crée le film en base s'il n'existe pas encore (grâce à id_jpbox),
    sinon récupère la ligne déjà existante et la complète.

    On ne retrouve plus une oeuvre existante via id_tmdb : plusieurs lignes
    peuvent légitimement partager le même id_tmdb (une reprise en salle a
    son propre id_jpbox et sa propre entrees_premiere_semaine, mais c'est
    le même film sur TMDB), donc id_tmdb n'identifie plus une ligne unique."""
    oeuvre = None
    if id_jpbox is not None:
        oeuvre = session.query(Oeuvre).filter_by(id_jpbox=id_jpbox).first()

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

    return _enrichir_oeuvre(session, oeuvre, infos_tmdb, notes_imdb)


def _enrichir_oeuvre(
    session: Session,
    oeuvre: Oeuvre,
    infos_tmdb: dict | None,
    notes_imdb: dict | None = None,
) -> Oeuvre:
    """Complète une oeuvre déjà identifiée (existante ou tout juste créée)
    avec ses infos TMDB : synopsis, notes, genres, casting, réalisateurs."""
    if infos_tmdb is not None:
        oeuvre.id_tmdb = infos_tmdb["id_tmdb"]
        oeuvre.synopsis = infos_tmdb["synopsis"]
        oeuvre.note_tmdb = infos_tmdb["note_tmdb"]
        if oeuvre.annee_sortie is None:
            oeuvre.annee_sortie = infos_tmdb["annee_sortie"]
        if oeuvre.date_sortie is None:
            oeuvre.date_sortie = infos_tmdb["date_sortie"]
        if notes_imdb and infos_tmdb.get("imdb_id"):
            oeuvre.note_imdb = notes_imdb.get(infos_tmdb["imdb_id"])

        # Pour chaque lien (genre, acteur...), on vérifie en base s'il existe
        # déjà avant de l'ajouter, puis on flush tout de suite : ça évite les
        # doublons même si TMDB renvoie 2 fois le même nom pour un film, ou
        # si ce film a déjà été enrichi lors d'un passage précédent.
        for nom_genre in infos_tmdb["genres"]:
            genre = _get_ou_creer_genre(session, nom_genre)
            deja_liee = (
                session.query(GenreOeuvre)
                .filter_by(id_oeuvre=oeuvre.id_oeuvre, id_genre=genre.id_genre)
                .first()
                is not None
            )
            if not deja_liee:
                oeuvre.genres_assoc.append(GenreOeuvre(genre=genre))
                session.flush()

        for nom_societe in infos_tmdb["productions"]:
            production = _get_ou_creer_production(session, nom_societe)
            deja_liee = (
                session.query(ProductionOeuvre)
                .filter_by(id_oeuvre=oeuvre.id_oeuvre, id_production=production.id_production)
                .first()
                is not None
            )
            if not deja_liee:
                oeuvre.productions_assoc.append(ProductionOeuvre(production=production))
                session.flush()

        for personne in infos_tmdb["acteurs"]:
            acteur = _get_ou_creer_acteur(session, personne["nom"])
            deja_liee = (
                session.query(ActeurOeuvre)
                .filter_by(id_oeuvre=oeuvre.id_oeuvre, id_acteur=acteur.id_acteur)
                .first()
                is not None
            )
            if not deja_liee:
                oeuvre.acteurs_assoc.append(ActeurOeuvre(acteur=acteur, role=personne["role"]))
                session.flush()

        for nom_complet in infos_tmdb["realisateurs"]:
            realisateur = _get_ou_creer_realisateur(session, nom_complet)
            deja_liee = (
                session.query(RealisateurOeuvre)
                .filter_by(id_oeuvre=oeuvre.id_oeuvre, id_realisateur=realisateur.id_realisateur)
                .first()
                is not None
            )
            if not deja_liee:
                oeuvre.realisateurs_assoc.append(RealisateurOeuvre(realisateur=realisateur))
                session.flush()

    session.flush()
    return oeuvre


def traiter_films_a_venir(session: Session, notes_imdb: dict | None = None) -> int:
    """Flux A : scrape les films bientôt en salle et les enregistre
    avec leurs infos TMDB. Retourne le nombre de films traités."""
    if notes_imdb is None:
        notes_imdb = imdb.telecharger_notes_imdb()

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
            notes_imdb=notes_imdb,
        )
        nb_films += 1
    session.commit()
    return nb_films


def traiter_entrees_semaine(
    session: Session, idsem: int, vue: int, notes_imdb: dict | None = None
) -> int:
    """Flux B : scrape le classement hebdomadaire et enregistre
    entrees_premiere_semaine pour les films qui sortent tout juste
    (semaine_exploitation == 1). Retourne le nombre de films mis à jour."""
    if notes_imdb is None:
        notes_imdb = imdb.telecharger_notes_imdb()

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
            notes_imdb=notes_imdb,
        )
        oeuvre.entrees_premiere_semaine = film["entrees_semaine"]
        nb_maj += 1

    session.commit()
    return nb_maj


def reessayer_matching_tmdb(session: Session, notes_imdb: dict | None = None) -> int:
    """Retente l'enrichissement TMDB des films qui n'ont pas encore de
    id_tmdb (échec de matching lors d'un passage précédent, ex: titre
    générique noyé dans les résultats, ou annotation JPBOX du style
    "(Rep. 2026)"). Retourne le nombre de films corrigés."""
    if notes_imdb is None:
        notes_imdb = imdb.telecharger_notes_imdb()

    nb_corriges = 0
    for oeuvre in session.query(Oeuvre).filter(Oeuvre.id_tmdb.is_(None)).all():
        infos_tmdb = enrichir_avec_tmdb(oeuvre.nom_francais, oeuvre.annee_sortie)
        if infos_tmdb is None:
            continue
        # On enrichit directement la ligne déjà chargée (pas via
        # sauvegarder_film) : quand id_jpbox est None, sauvegarder_film ne
        # pourrait pas la retrouver et créerait un doublon.
        _enrichir_oeuvre(session, oeuvre, infos_tmdb, notes_imdb)
        nb_corriges += 1

    session.commit()
    return nb_corriges


def backfill(
    session: Session, idsem_debut: int, idsem_fin: int, vue: int, notes_imdb: dict | None = None
) -> int:
    """Rattrapage historique : rejoue traiter_entrees_semaine sur une
    plage de semaines passées, pour avoir assez de données d'entraînement."""
    if notes_imdb is None:
        notes_imdb = imdb.telecharger_notes_imdb()  # une seule fois pour tout le backfill
    total = 0
    for idsem in range(idsem_debut, idsem_fin + 1):
        total += traiter_entrees_semaine(session, idsem, vue, notes_imdb=notes_imdb)
    return total
