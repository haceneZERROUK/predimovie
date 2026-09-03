from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Acteur(Base):
    """Un acteur ou une actrice."""

    __tablename__ = "acteur"

    id_acteur: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    date_de_naissance: Mapped[Date] = mapped_column(Date, nullable=True)
    nationalite: Mapped[str] = mapped_column(String(100), nullable=True)


class ActeurOeuvre(Base):
    """Table d'association acteur <-> oeuvre. Le role (nom du personnage)
    est stocke ici parce qu'il depend du couple acteur/film."""

    __tablename__ = "acteur_oeuvre"

    id_acteur: Mapped[int] = mapped_column(ForeignKey("acteur.id_acteur"), primary_key=True)
    id_oeuvre: Mapped[int] = mapped_column(ForeignKey("oeuvre.id_oeuvre"), primary_key=True)
    # Text et pas String(255) : sur les dessins animes un doubleur peut
    # faire plein de personnages et la liste depasse 255 caracteres
    role: Mapped[str] = mapped_column(Text, nullable=True)

    acteur: Mapped["Acteur"] = relationship()
    oeuvre: Mapped["Oeuvre"] = relationship(back_populates="acteurs_assoc")  # noqa: F821
