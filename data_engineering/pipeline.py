# Recupere les films sur JPBOX / AlloCine / TMDB et les enregistre en base
from datetime import date, timedelta

from sqlalchemy.orm import Session

from data_engineering import allocine, imdb, jpbox, tmdb
from data_engineering.matching import meme_film, nettoyer_annotations, se_ressemblent
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
    """Retourne la nature si elle existe deja, sinon la cree."""
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
    """Coupe 'Prenom Nom' en deux au premier espace."""
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
    """Cherche le film sur TMDB et renvoie ses infos (synopsis, genres,
    casting...). None si aucun resultat ne correspond."""
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

    # on prend la date de sortie France, et release_date si TMDB n'en a pas
    dates_par_pays = tmdb.get_dates_sortie_par_pays(resultat["id"])
    texte_date_sortie = tmdb.date_sortie_france(dates_par_pays) or details.get("release_date") or ""
    date_sortie_tmdb = date.fromisoformat(texte_date_sortie) if texte_date_sortie else None
    annee_sortie_tmdb = date_sortie_tmdb.year if date_sortie_tmdb else None

    return {
        "id_tmdb": resultat["id"],
        "imdb_id": details.get("imdb_id"),
        "annee_sortie": annee_sortie_tmdb,
        "date_sortie": date_sortie_tmdb,
        "synopsis": details.get("overview"),
        "note_tmdb": details.get("vote_average"),
        "langue_originale": details.get("original_language"),
        # budget en dollars, None quand TMDB renvoie 0 (= inconnu)
        "budget": details.get("budget") or None,
        "genres": [g["name"] for g in details.get("genres", [])],
        "productions": [p["name"] for p in details.get("production_companies", [])],
        # que les 10 premiers acteurs
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
    id_allocine: int | None = None,
) -> Oeuvre:
    """Cherche le film par id_jpbox puis id_allocine. S'il n'existe pas on
    le cree, et dans les deux cas on le complete avec les infos TMDB."""
    oeuvre = None
    if id_jpbox is not None:
        oeuvre = session.query(Oeuvre).filter_by(id_jpbox=id_jpbox).first()
    if oeuvre is None and id_allocine is not None:
        oeuvre = session.query(Oeuvre).filter_by(id_allocine=id_allocine).first()

    if oeuvre is None:
        nature = _get_ou_creer_nature(session, "Film")
        oeuvre = Oeuvre(
            nom_francais=titre_francais,
            nom_original=titre_original,
            annee_sortie=annee_sortie,
            id_jpbox=id_jpbox,
            id_allocine=id_allocine,
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
    """Remplit une oeuvre avec ses infos TMDB : synopsis, notes, genres,
    productions, acteurs et realisateurs."""
    if infos_tmdb is not None:
        oeuvre.id_tmdb = infos_tmdb["id_tmdb"]
        oeuvre.synopsis = infos_tmdb["synopsis"]
        oeuvre.note_tmdb = infos_tmdb["note_tmdb"]
        oeuvre.langue_originale = infos_tmdb["langue_originale"]
        if oeuvre.annee_sortie is None:
            oeuvre.annee_sortie = infos_tmdb["annee_sortie"]
        if oeuvre.date_sortie is None:
            oeuvre.date_sortie = infos_tmdb["date_sortie"]
        if notes_imdb and infos_tmdb.get("imdb_id"):
            oeuvre.note_imdb = notes_imdb.get(infos_tmdb["imdb_id"])

        # on verifie que le lien n'existe pas deja avant de l'ajouter,
        # sinon on se retrouve avec des doublons
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


def prochain_mercredi(depuis: date | None = None) -> date:
    """Date du prochain mercredi (jour des sorties en France).
    Renvoie aujourd'hui si on est deja mercredi."""
    depuis = depuis or date.today()
    jours_a_ajouter = (2 - depuis.weekday()) % 7  # lundi=0 ... mercredi=2
    return depuis + timedelta(days=jours_a_ajouter)


def traiter_films_a_venir(
    session: Session, notes_imdb: dict | None = None, date_sortie: date | None = None
) -> int:
    """Flux A : scrape les films qui sortent un mercredi donne (le prochain
    par defaut) sur JPBOX puis sur AlloCine, et les met en base avec leurs
    infos TMDB. Renvoie le nombre de films traites."""
    if notes_imdb is None:
        notes_imdb = imdb.telecharger_notes_imdb()
    if date_sortie is None:
        date_sortie = prochain_mercredi()

    nb_films = 0
    titres_traites = []  # (titre, oeuvre) deja vus, pour la boucle AlloCine

    for film in jpbox.films_du_calendrier(date_sortie):
        infos_tmdb = enrichir_avec_tmdb(film["titre_francais"], film["annee_sortie"])
        oeuvre = sauvegarder_film(
            session,
            id_jpbox=film["id_jpbox"],
            titre_francais=film["titre_francais"],
            titre_original=film["titre_francais"],
            annee_sortie=film["annee_sortie"],
            infos_tmdb=infos_tmdb,
            notes_imdb=notes_imdb,
        )
        # on ecrase la date TMDB par celle qu'on a demandee : pour une
        # reprise en salle TMDB donne la date de sortie d'origine
        oeuvre.date_sortie = date_sortie
        titres_traites.append((film["titre_francais"], oeuvre))
        nb_films += 1

    for film in allocine.films_de_la_semaine(date_sortie):
        # si le film est deja passe par JPBOX on ajoute juste son id_allocine
        deja_traite = next(
            (o for titre, o in titres_traites if se_ressemblent(titre, film["titre_francais"])),
            None,
        )
        if deja_traite is not None:
            deja_traite.id_allocine = film["id_allocine"]
            continue

        infos_tmdb = enrichir_avec_tmdb(film["titre_francais"], None)
        oeuvre = sauvegarder_film(
            session,
            id_jpbox=None,
            id_allocine=film["id_allocine"],
            titre_francais=film["titre_francais"],
            titre_original=film["titre_francais"],
            annee_sortie=None,
            infos_tmdb=infos_tmdb,
            notes_imdb=notes_imdb,
        )
        oeuvre.date_sortie = date_sortie  # pareil que plus haut
        titres_traites.append((film["titre_francais"], oeuvre))
        nb_films += 1

    session.commit()
    return nb_films


def traiter_entrees_semaine(
    session: Session, idsem: int, vue: int, notes_imdb: dict | None = None
) -> int:
    """Flux B : scrape le classement d'une semaine et enregistre
    entrees_premiere_semaine pour les films qui en sont a leur 1ere
    semaine. Renvoie le nombre de films mis a jour."""
    if notes_imdb is None:
        notes_imdb = imdb.telecharger_notes_imdb()

    nb_maj = 0
    for film in jpbox.classement_hebdo(idsem, vue):
        if film["semaine_exploitation"] != 1:
            continue  # que la 1ere semaine

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
        # une requete de plus par film pour aller chercher le nb de salles
        if film["id_jpbox"] is not None:
            oeuvre.nb_salles_semaine1 = jpbox.nb_salles_premiere_semaine(film["id_jpbox"])
        nb_maj += 1

    session.commit()
    return nb_maj


def reessayer_matching_tmdb(session: Session, notes_imdb: dict | None = None) -> int:
    """Retente le matching TMDB sur les films qui n'ont pas d'id_tmdb.
    Renvoie le nombre de films rattrapes."""
    if notes_imdb is None:
        notes_imdb = imdb.telecharger_notes_imdb()

    nb_corriges = 0
    for oeuvre in session.query(Oeuvre).filter(Oeuvre.id_tmdb.is_(None)).all():
        infos_tmdb = enrichir_avec_tmdb(oeuvre.nom_francais, oeuvre.annee_sortie)
        if infos_tmdb is None:
            continue
        # on passe directement par _enrichir_oeuvre, sinon sauvegarder_film
        # ne retrouve pas la ligne (pas d'id_jpbox) et en cree une autre
        _enrichir_oeuvre(session, oeuvre, infos_tmdb, notes_imdb)
        nb_corriges += 1

    session.commit()
    return nb_corriges


def backfill(
    session: Session, idsem_debut: int, idsem_fin: int, vue: int, notes_imdb: dict | None = None
) -> int:
    """Rejoue traiter_entrees_semaine sur une plage de semaines passees,
    pour recuperer l'historique."""
    if notes_imdb is None:
        notes_imdb = imdb.telecharger_notes_imdb()  # une seule fois pour toute la plage
    total = 0
    for idsem in range(idsem_debut, idsem_fin + 1):
        total += traiter_entrees_semaine(session, idsem, vue, notes_imdb=notes_imdb)
    return total
