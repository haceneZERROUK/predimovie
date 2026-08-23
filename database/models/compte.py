import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class RoleCompte(enum.StrEnum):
    """Les deux rôles possibles pour un compte : soit un exploitant de
    cinéma (qui consulte les prédictions pour son propre cinéma), soit
    l'administrateur du projet (accès complet)."""

    CINEMA = "cinema"
    ADMIN = "admin"


class Compte(Base):
    """Un compte de connexion à l'application Django.

    Choix de conception : un compte = un cinéma (pas de table `cinema`
    séparée). La colonne `nom_cinema` n'est donc renseignée que pour les
    comptes de rôle CINEMA ; elle reste vide (nullable) pour le compte ADMIN.
    """

    __tablename__ = "compte"

    id_compte: Mapped[int] = mapped_column(primary_key=True)
    mail: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mot_de_passe: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleCompte] = mapped_column(Enum(RoleCompte), nullable=False)
    nom_cinema: Mapped[str] = mapped_column(String(255), nullable=True)
    date_inscription: Mapped[date] = mapped_column(Date, nullable=False)
    derniere_connexion: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # sert a desactiver un compte sans le supprimer ; non exploite cote
    # backend/frontend pour l'instant (aucune route ne le passe a False)
    statut_compte: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
