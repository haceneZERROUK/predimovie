from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Genre(Base):
    """Un genre de film (ex: "Science-fiction", "Comédie")."""

    __tablename__ = "genre"

    id_genre: Mapped[int] = mapped_column(primary_key=True)
    nom_genre: Mapped[str] = mapped_column(String(50), nullable=False)


class GenreOeuvre(Base):
    """Table d'association genre <-> oeuvre (many-to-many) : un film peut
    avoir plusieurs genres, et un genre s'applique à plusieurs films.
    Voir `ActeurOeuvre` dans acteur.py pour une explication plus détaillée
    de ce type de table.
    """

    __tablename__ = "genre_oeuvre"

    id_genre: Mapped[int] = mapped_column(ForeignKey("genre.id_genre"), primary_key=True)
    id_oeuvre: Mapped[int] = mapped_column(ForeignKey("oeuvre.id_oeuvre"), primary_key=True)

    genre: Mapped["Genre"] = relationship()
    oeuvre: Mapped["Oeuvre"] = relationship(back_populates="genres_assoc")  # noqa: F821
