from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Production(Base):
    """Une société de production (ex: "Warner Bros")."""

    __tablename__ = "production"

    id_production: Mapped[int] = mapped_column(primary_key=True)
    nom_societe: Mapped[str] = mapped_column(String(255), nullable=False)
    pays: Mapped[str] = mapped_column(String(100), nullable=True)
    date_fondation: Mapped[Date] = mapped_column(Date, nullable=True)


class ProductionOeuvre(Base):
    """Table d'association production <-> oeuvre (many-to-many) : une
    société peut produire plusieurs films, et un film peut avoir plusieurs
    sociétés de production (co-production). Voir `ActeurOeuvre` dans
    acteur.py pour une explication plus détaillée de ce type de table.
    """

    __tablename__ = "production_oeuvre"

    id_production: Mapped[int] = mapped_column(
        ForeignKey("production.id_production"), primary_key=True
    )
    id_oeuvre: Mapped[int] = mapped_column(ForeignKey("oeuvre.id_oeuvre"), primary_key=True)

    production: Mapped["Production"] = relationship()
    oeuvre: Mapped["Oeuvre"] = relationship(back_populates="productions_assoc")  # noqa: F821
