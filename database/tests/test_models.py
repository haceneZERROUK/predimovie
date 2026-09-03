# Cree un vrai film en base et relit ses relations, pour verifier que le
# schema tient debout. db_session vient de conftest.py.
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
    # on construit tout en memoire, rien n'est encore en base
    nature = Nature(nom_nature="Film")
    genre = Genre(nom_genre="Science-fiction")
    oeuvre = Oeuvre(
        nom_francais="Dune",
        nom_original="Dune",
        annee_sortie=2021,
        note_tmdb=7.8,
        note_imdb=8.0,
        mot_cle_1="désert",
        mot_cle_2="prophétie",
        mot_cle_3="empire",
        entrees_premiere_semaine=1_200_000,
        nature=nature,
    )
    # genres_assoc et acteurs_assoc sont les tables d'association
    oeuvre.genres_assoc.append(GenreOeuvre(genre=genre))
    acteur = Acteur(nom="Chalamet", prenom="Timothée")
    oeuvre.acteurs_assoc.append(ActeurOeuvre(acteur=acteur, role="Paul Atreides"))

    # on envoie en base, SQLAlchemy se debrouille avec l'ordre des inserts
    db_session.add(oeuvre)
    db_session.flush()

    # et on verifie que tout est bien relie
    assert oeuvre.id_oeuvre is not None  # la base a bien genere un id
    assert oeuvre.nature.nom_nature == "Film"
    assert oeuvre.entrees_premiere_semaine == 1_200_000
    assert oeuvre.note_tmdb == 7.8
    assert oeuvre.note_imdb == 8.0
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
