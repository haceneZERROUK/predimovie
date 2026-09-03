import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class RoleCompte(enum.StrEnum):
    """Les deux roles possibles : exploitant de cinema ou admin."""

    CINEMA = "cinema"
    ADMIN = "admin"


class Compte(Base):
    """Un compte de connexion. Un compte = un cinema, il n'y a pas de
    table cinema a part. nom_cinema reste vide pour les admins."""

    __tablename__ = "compte"

    id_compte: Mapped[int] = mapped_column(primary_key=True)
    mail: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mot_de_passe: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleCompte] = mapped_column(Enum(RoleCompte), nullable=False)
    nom_cinema: Mapped[str] = mapped_column(String(255), nullable=True)
    date_inscription: Mapped[date] = mapped_column(Date, nullable=False)
    derniere_connexion: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # pour desactiver un compte sans le supprimer. Pas encore utilise,
    # aucune route ne le passe a False.
    statut_compte: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
