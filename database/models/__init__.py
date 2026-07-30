# On importe ici tous les modèles (une classe = une table) pour qu'ils
# soient enregistrés sur `Base.metadata` dès qu'on importe `database.models`.
# C'est ce fichier qu'Alembic (les migrations) et les tests utilisent pour
# connaître l'ensemble des tables à créer.
from database.models.acteur import Acteur, ActeurOeuvre
from database.models.compte import Compte, RoleCompte
from database.models.genre import Genre, GenreOeuvre
from database.models.nature import Nature
from database.models.oeuvre import Oeuvre
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
    "Production",
    "ProductionOeuvre",
    "Realisateur",
    "RealisateurOeuvre",
]
