from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Realisateur(Base):
    """Un réalisateur ou une réalisatrice de film."""

    __tablename__ = "realisateur"

    id_realisateur: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    date_de_naissance: Mapped[Date] = mapped_column(Date, nullable=True)
    nationalite: Mapped[str] = mapped_column(String(100), nullable=True)


class RealisateurOeuvre(Base):
    """Table d'association realisateur <-> oeuvre."""

    __tablename__ = "realisateur_oeuvre"

    id_realisateur: Mapped[int] = mapped_column(
        ForeignKey("realisateur.id_realisateur"), primary_key=True
    )
    id_oeuvre: Mapped[int] = mapped_column(ForeignKey("oeuvre.id_oeuvre"), primary_key=True)

    realisateur: Mapped["Realisateur"] = relationship()
    oeuvre: Mapped["Oeuvre"] = relationship(back_populates="realisateurs_assoc")  # noqa: F821
