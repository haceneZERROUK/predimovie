# Schemas Pydantic : la forme des donnees qui rentrent et sortent de l'API.
from datetime import date, datetime

from pydantic import BaseModel


class ConnexionDemande(BaseModel):
    mail: str
    mot_de_passe: str


class ConnexionReponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PredictionDemande(BaseModel):
    id_oeuvre: int


class PredictionReponse(BaseModel):
    id_oeuvre: int
    nom_francais: str
    entrees_premiere_semaine_predites: int


class FilmAVenir(BaseModel):
    id_oeuvre: int
    nom_francais: str
    date_sortie: date | None = None
    synopsis: str | None = None


class RelanceReponse(BaseModel):
    nombre_predictions: int


class HistoriquePrediction(BaseModel):
    nom_francais: str
    # nullable : des films sont sortis sans qu'on ait stocke de prediction
    entrees_premiere_semaine_predites: int | None
    entrees_premiere_semaine_reelles: int
    date_prediction: datetime | None
    ecart: int | None


class HistoriqueReponse(BaseModel):
    predictions: list[HistoriquePrediction]
    # les semaines qui ont de l'historique, pour le menu deroulant du
    # front, la plus recente en premier
    semaines_disponibles: list[date]


class CompteCreationDemande(BaseModel):
    mail: str
    mot_de_passe: str
    nom_cinema: str


class CompteReponse(BaseModel):
    id_compte: int
    mail: str
    nom_cinema: str | None
    date_inscription: date
    derniere_connexion: datetime | None
    statut_compte: bool
