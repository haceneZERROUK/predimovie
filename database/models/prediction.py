from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Prediction(Base):
    """Une prediction du modele pour un film, avec sa date de calcul.
    nom_francais est recopie depuis oeuvre pour eviter une jointure a
    l'affichage."""

    __tablename__ = "prediction"

    id_prediction: Mapped[int] = mapped_column(primary_key=True)
    id_oeuvre: Mapped[int] = mapped_column(ForeignKey("oeuvre.id_oeuvre"), nullable=False)
    nom_francais: Mapped[str] = mapped_column(String(255), nullable=False)
    entrees_premiere_semaine_predites: Mapped[int] = mapped_column(Integer, nullable=False)
    date_prediction: Mapped[datetime] = mapped_column(DateTime, nullable=False)
