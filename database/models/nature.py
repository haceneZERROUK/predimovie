from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Nature(Base):
    """Le type d'oeuvre (ex: "Film", "Série"). Relation one-to-many avec
    Oeuvre : une Nature peut correspondre à plusieurs Oeuvres, mais une
    Oeuvre n'a qu'une seule Nature (voir `id_nature` dans oeuvre.py)."""

    __tablename__ = "nature"

    id_nature: Mapped[int] = mapped_column(primary_key=True)
    nom_nature: Mapped[str] = mapped_column(String(50), nullable=False)

    # Liste de toutes les Oeuvres qui ont cette Nature.
    oeuvres: Mapped[list["Oeuvre"]] = relationship(back_populates="nature")  # noqa: F821
