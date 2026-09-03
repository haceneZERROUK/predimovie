# On importe tous les modeles ici pour qu'ils soient enregistres sur
# Base.metadata, c'est ce que lisent Alembic et les tests.
from database.models.acteur import Acteur, ActeurOeuvre
from database.models.compte import Compte, RoleCompte
from database.models.genre import Genre, GenreOeuvre
from database.models.nature import Nature
from database.models.oeuvre import Oeuvre
from database.models.prediction import Prediction
from database.models.production import Production, ProductionOeuvre
from database.models.realisateur import Realisateur, RealisateurOeuvre

__all__ = [
    "Acteur",
    "ActeurOeuvre",
    "Compte",
    "RoleCompte",
    "Genre",
    "GenreOeuvre",
    "Nature",
    "Oeuvre",
    "Prediction",
    "Production",
    "ProductionOeuvre",
    "Realisateur",
    "RealisateurOeuvre",
]
