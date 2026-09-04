# Routes admin de gestion des comptes cinema. Pas d'inscription publique,
# c'est l'admin qui cree les comptes.
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func

from backend.auth import utilisateur_admin
from backend.schemas import CompteCreationDemande, CompteReponse
from backend.security import hacher_mot_de_passe
from database.base import SessionLocal
from database.models import Compte, RoleCompte

router = APIRouter()


def _vers_reponse(compte: Compte) -> CompteReponse:
    return CompteReponse(
        id_compte=compte.id_compte,
        mail=compte.mail,
        nom_cinema=compte.nom_cinema,
        date_inscription=compte.date_inscription,
        derniere_connexion=compte.derniere_connexion,
        statut_compte=compte.statut_compte,
    )


@router.get("/comptes", response_model=list[CompteReponse])
def lister_comptes(_utilisateur: dict = Depends(utilisateur_admin)):
    """Liste les comptes cinema. Les comptes admin ne sortent pas ici."""
    session = SessionLocal()
    try:
        comptes = session.query(Compte).filter_by(role=RoleCompte.CINEMA).all()
        return [_vers_reponse(c) for c in comptes]
    finally:
        session.close()


@router.post("/comptes", response_model=CompteReponse, status_code=201)
def creer_compte(
    demande: CompteCreationDemande, _utilisateur: dict = Depends(utilisateur_admin)
) -> CompteReponse:
    session = SessionLocal()
    try:
        # on enregistre le mail en minuscules, et on cherche le doublon sans
        # tenir compte de la casse : sinon on pourrait creer Jean@cine.fr et
        # jean@cine.fr comme deux comptes differents
        mail = demande.mail.strip().lower()
        deja_existant = session.query(Compte).filter(func.lower(Compte.mail) == mail).first()
        if deja_existant is not None:
            raise HTTPException(status_code=409, detail="Un compte existe deja avec ce mail")

        compte = Compte(
            mail=mail,
            mot_de_passe=hacher_mot_de_passe(demande.mot_de_passe),
            role=RoleCompte.CINEMA,
            nom_cinema=demande.nom_cinema,
            date_inscription=date.today(),
            statut_compte=True,
        )
        session.add(compte)
        session.commit()
        session.refresh(compte)
        return _vers_reponse(compte)
    finally:
        session.close()


@router.delete("/comptes/{id_compte}", status_code=204)
def supprimer_compte(id_compte: int, _utilisateur: dict = Depends(utilisateur_admin)):
    """Supprime un compte cinema. Le filtre sur le role empeche de
    supprimer un compte admin depuis cette route."""
    session = SessionLocal()
    try:
        compte = (
            session.query(Compte).filter_by(id_compte=id_compte, role=RoleCompte.CINEMA).first()
        )
        if compte is None:
            raise HTTPException(status_code=404, detail="Compte cinema introuvable")
        session.delete(compte)
        session.commit()
    finally:
        session.close()
