from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Oeuvre(Base):
    """Un film (ou une série) : la table centrale du projet.

    Toutes les autres tables (genre, acteur, réalisateur, production)
    servent à décrire une Oeuvre. C'est à partir de ces informations que
    le modèle de Machine Learning apprendra à prédire
    `entrees_premiere_semaine`.
    """

    __tablename__ = "oeuvre"

    id_oeuvre: Mapped[int] = mapped_column(primary_key=True)
    nom_francais: Mapped[str] = mapped_column(String(255), nullable=False)
    nom_original: Mapped[str] = mapped_column(String(255), nullable=True)
    synopsis: Mapped[str] = mapped_column(Text, nullable=True)
    annee_sortie: Mapped[int] = mapped_column(Integer, nullable=True)
    note_allocine: Mapped[float] = mapped_column(Float, nullable=True)
    note_sens_critique: Mapped[float] = mapped_column(Float, nullable=True)
    # Les 3 mots-clés extraits automatiquement du synopsis par l'agent IA
    # branché sur le pipeline N8n (un mot-clé par colonne, pas de liste).
    mot_cle_1: Mapped[str] = mapped_column(String(50), nullable=True)
    mot_cle_2: Mapped[str] = mapped_column(String(50), nullable=True)
    mot_cle_3: Mapped[str] = mapped_column(String(50), nullable=True)
    # Nombre d'entrées en salle sur la première semaine d'exploitation.
    # C'est la valeur que le modèle de prédiction doit apprendre à estimer
    # (la "cible"/"target" en Machine Learning) à partir des autres colonnes
    # et des tables liées (genres, acteurs, réalisateurs, production).
    # Elle est `nullable=True` car un film pas encore sorti n'a pas encore
    # de valeur réelle : c'est justement ce qu'on veut prédire pour lui.
    entrees_premiere_semaine: Mapped[int] = mapped_column(Integer, nullable=True)
    # Identifiants externes : ils servent à retrouver un film déjà enregistré
    # au lieu d'en recréer un doublon à chaque passage du scraper.
    id_jpbox: Mapped[int] = mapped_column(Integer, nullable=True, unique=True)
    id_tmdb: Mapped[int] = mapped_column(Integer, nullable=True, unique=True)
    id_nature: Mapped[int] = mapped_column(ForeignKey("nature.id_nature"), nullable=False)

    # Chaque relationship() ci-dessous correspond à une des tables
    # d'association (genre_oeuvre, acteur_oeuvre, ...) : elles permettent
    # de naviguer en Python (ex: `oeuvre.genres_assoc`) sans écrire de SQL.
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
