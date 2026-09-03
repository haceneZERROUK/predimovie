from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Oeuvre(Base):
    """Un film. C'est la table centrale, toutes les autres (genre, acteur,
    realisateur, production) la decrivent."""

    __tablename__ = "oeuvre"

    id_oeuvre: Mapped[int] = mapped_column(primary_key=True)
    nom_francais: Mapped[str] = mapped_column(String(255), nullable=False)
    nom_original: Mapped[str] = mapped_column(String(255), nullable=True)
    synopsis: Mapped[str] = mapped_column(Text, nullable=True)
    annee_sortie: Mapped[int] = mapped_column(Integer, nullable=True)
    # date complete, pour savoir quel film sort quel mercredi
    date_sortie: Mapped[date] = mapped_column(Date, nullable=True)
    # note TMDB sur 10
    note_tmdb: Mapped[float] = mapped_column(Float, nullable=True)
    # note IMDb sur 10
    note_imdb: Mapped[float] = mapped_column(Float, nullable=True)
    # les 3 mots-cles tires du synopsis, un par colonne
    mot_cle_1: Mapped[str] = mapped_column(String(100), nullable=True)
    mot_cle_2: Mapped[str] = mapped_column(String(100), nullable=True)
    mot_cle_3: Mapped[str] = mapped_column(String(100), nullable=True)
    # la cible du modele. nullable parce qu'un film pas encore sorti n'a
    # pas encore d'entrees, c'est justement ce qu'on veut predire
    entrees_premiere_semaine: Mapped[int] = mapped_column(Integer, nullable=True)
    # ids externes, pour retrouver un film deja en base au lieu d'en creer
    # un doublon a chaque passage du scraper. id_tmdb n'est pas unique :
    # une reprise en salle a son propre id_jpbox mais le meme id_tmdb que
    # la sortie d'origine.
    id_jpbox: Mapped[int] = mapped_column(Integer, nullable=True, unique=True)
    id_allocine: Mapped[int] = mapped_column(Integer, nullable=True, unique=True)
    id_tmdb: Mapped[int] = mapped_column(Integer, nullable=True)
    # code langue ISO 639-1 ("fr", "en"...), sert au sample_weight
    langue_originale: Mapped[str] = mapped_column(String(10), nullable=True)
    # budget en dollars. Souvent 0 ou NULL quand TMDB ne le connait pas,
    # a traiter comme une donnee manquante.
    budget: Mapped[int] = mapped_column(Integer, nullable=True)
    # vrai nombre de salles en 1ere semaine, connu seulement apres la
    # sortie : sert a entrainer le sous-modele salles
    nb_salles_semaine1: Mapped[int] = mapped_column(Integer, nullable=True)
    # ce que le sous-modele predit, utilisable avant la sortie lui
    nb_salles_predites: Mapped[float] = mapped_column(Float, nullable=True)
    id_nature: Mapped[int] = mapped_column(ForeignKey("nature.id_nature"), nullable=False)

    # les relations vers les tables d'association, pour naviguer en Python
    # (oeuvre.genres_assoc, etc.) sans ecrire de SQL
    nature: Mapped["Nature"] = relationship(back_populates="oeuvres")  # noqa: F821
    genres_assoc: Mapped[list["GenreOeuvre"]] = relationship(back_populates="oeuvre")  # noqa: F821
    acteurs_assoc: Mapped[list["ActeurOeuvre"]] = relationship(  # noqa: F821
        back_populates="oeuvre"
    )
    realisateurs_assoc: Mapped[list["RealisateurOeuvre"]] = relationship(  # noqa: F821
        back_populates="oeuvre"
    )
    productions_assoc: Mapped[list["ProductionOeuvre"]] = relationship(  # noqa: F821
        back_populates="oeuvre"
    )
