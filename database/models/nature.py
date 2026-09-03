from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Nature(Base):
    """Le type d'oeuvre ("Film", "Serie"). Une oeuvre n'a qu'une nature."""

    __tablename__ = "nature"

    id_nature: Mapped[int] = mapped_column(primary_key=True)
    nom_nature: Mapped[str] = mapped_column(String(50), nullable=False)

    # les oeuvres qui ont cette nature
    oeuvres: Mapped[list["Oeuvre"]] = relationship(back_populates="nature")  # noqa: F821
