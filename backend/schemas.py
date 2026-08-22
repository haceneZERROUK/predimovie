# Schemas Pydantic : la forme des donnees qui rentrent et sortent de l'API.
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
