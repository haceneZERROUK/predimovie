from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Prediction(Base):
    """Le resultat d'une prediction du modele ML pour un film, avec la
    date a laquelle elle a ete calculee.

    Alimentee via /predictions/relancer (backend/predictions_admin.py),
    declenche a la main par un admin (bouton "Relancer les predictions"),
    pour que les cinemas voient une prediction deja calculee sans attendre
    un appel au modele.

    nom_francais est duplique depuis `oeuvre` (au lieu d'une jointure) pour
    que l'appli client puisse afficher le nom du film directement.
    """

    __tablename__ = "prediction"

    id_prediction: Mapped[int] = mapped_column(primary_key=True)
    id_oeuvre: Mapped[int] = mapped_column(ForeignKey("oeuvre.id_oeuvre"), nullable=False)
    nom_francais: Mapped[str] = mapped_column(String(255), nullable=False)
    entrees_premiere_semaine_predites: Mapped[int] = mapped_column(Integer, nullable=False)
    date_prediction: Mapped[datetime] = mapped_column(DateTime, nullable=False)
