from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Acteur(Base):
    """Une personne qui joue dans un ou plusieurs films (table `acteur`)."""

    __tablename__ = "acteur"

    # primary_key=True : identifiant unique de la ligne, généré automatiquement par la BDD.
    id_acteur: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    date_de_naissance: Mapped[Date] = mapped_column(Date, nullable=True)
    nationalite: Mapped[str] = mapped_column(String(100), nullable=True)


class ActeurOeuvre(Base):
    """Table d'association acteur <-> oeuvre (relation many-to-many).

    Un acteur peut jouer dans plusieurs films, et un film a plusieurs
    acteurs : on ne peut pas relier ça avec une seule clé étrangère, il
    faut une table intermédiaire. `role` stocke en plus le nom du
    personnage joué (ex: "Paul Atreides"), une info propre à CETTE
    association acteur/film et pas à l'acteur ou au film en général.
    """

    __tablename__ = "acteur_oeuvre"

    # ForeignKey("acteur.id_acteur") : pointe vers la colonne id_acteur de la table acteur.
    id_acteur: Mapped[int] = mapped_column(ForeignKey("acteur.id_acteur"), primary_key=True)
    id_oeuvre: Mapped[int] = mapped_column(ForeignKey("oeuvre.id_oeuvre"), primary_key=True)
    # Text plutôt que String(255) : certains doubleurs jouent beaucoup de
    # personnages (dessins animés), le nom du rôle peut dépasser 255 caractères.
    role: Mapped[str] = mapped_column(Text, nullable=True)

    # `relationship` ne crée pas de colonne en BDD : ça permet juste,
    # en Python, d'écrire `mon_association.acteur` pour récupérer l'objet
    # Acteur lié, sans avoir à refaire une requête SQL manuellement.
    acteur: Mapped["Acteur"] = relationship()
    # back_populates="acteurs_assoc" relie cette relation à l'attribut
    # `acteurs_assoc` défini côté Oeuvre, pour que les deux sens de la
    # relation (film -> acteurs et acteur -> film) restent synchronisés.
    oeuvre: Mapped["Oeuvre"] = relationship(back_populates="acteurs_assoc")  # noqa: F821
