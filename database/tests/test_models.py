# Test "d'intégration" : il vérifie que les modèles SQLAlchemy définis
# dans database/models/ correspondent bien à un schéma cohérent, en
# créant un vrai film en base et en relisant ses relations (nature,
# genres, acteurs). `db_session` vient de conftest.py.
from datetime import date

from database.models import (
    Acteur,
    ActeurOeuvre,
    Compte,
    Genre,
    GenreOeuvre,
    Nature,
    Oeuvre,
    RoleCompte,
)


def test_oeuvre_with_nature_genre_acteur(db_session):
    # 1. On construit les objets en mémoire (rien n'est encore en BDD).
    nature = Nature(nom_nature="Film")
    genre = Genre(nom_genre="Science-fiction")
    oeuvre = Oeuvre(
        nom_francais="Dune",
        nom_original="Dune",
        annee_sortie=2021,
        mot_cle_1="désert",
        mot_cle_2="prophétie",
        mot_cle_3="empire",
        entrees_premiere_semaine=1_200_000,
        nature=nature,
    )
    # oeuvre.genres_assoc / .acteurs_assoc sont les tables d'association
    # (many-to-many) définies via `relationship()` dans oeuvre.py.
    oeuvre.genres_assoc.append(GenreOeuvre(genre=genre))
    acteur = Acteur(nom="Chalamet", prenom="Timothée")
    oeuvre.acteurs_assoc.append(ActeurOeuvre(acteur=acteur, role="Paul Atreides"))

    # 2. On envoie tout ça en base (SQLAlchemy déduit l'ordre des insertions
    # à partir des relations : nature, puis oeuvre, puis les associations).
    db_session.add(oeuvre)
    db_session.flush()

    # 3. On vérifie que tout a bien été sauvegardé et relié correctement.
    assert oeuvre.id_oeuvre is not None  # un id a été généré par la BDD
    assert oeuvre.nature.nom_nature == "Film"
    assert oeuvre.entrees_premiere_semaine == 1_200_000
    assert oeuvre.mot_cle_1 == "désert"
    assert oeuvre.genres_assoc[0].genre.nom_genre == "Science-fiction"
    assert oeuvre.acteurs_assoc[0].role == "Paul Atreides"


def test_compte_cinema_et_admin(db_session):
    compte_cinema = Compte(
        mail="cinema@example.com",
        mot_de_passe="hash",
        role=RoleCompte.CINEMA,
        nom_cinema="Le Rex",
        date_inscription=date(2026, 1, 1),
    )
    compte_admin = Compte(
        mail="admin@example.com",
        mot_de_passe="hash",
        role=RoleCompte.ADMIN,
        date_inscription=date(2026, 1, 1),
    )

    db_session.add_all([compte_cinema, compte_admin])
    db_session.flush()

    assert compte_cinema.role == RoleCompte.CINEMA
    assert compte_cinema.nom_cinema == "Le Rex"
    assert compte_admin.role == RoleCompte.ADMIN
    assert compte_admin.nom_cinema is None
