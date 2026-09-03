# Petit fichier central pour lire la configuration (variables d'environnement).
# Comme ça, on ne répète pas os.environ.get(...) partout dans le code.
import os

# Clé API pour interroger TMDB (The Movie Database) : synopsis, genres, casting...
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Site source pour les entrées box-office (France + international)
JPBOX_BASE_URL = os.environ.get("JPBOX_BASE_URL", "https://www.jpbox-office.com")

# Codes de "vue" JPBOX pour choisir le pays du classement hebdomadaire
JPBOX_VUE_FRANCE = 2
JPBOX_VUE_INTERNATIONAL = 5

# JPBOX a signalé sur son site des abus de bots IA : on reste discret,
# on s'identifie clairement et on attend un peu entre 2 requêtes.
JPBOX_USER_AGENT = "PredimovieBot/1.0 (projet etudiant, usage academique)"
JPBOX_DELAI_ENTRE_REQUETES = 1.5  # secondes

# JPBOX ne suit que les sorties avec un vrai suivi box-office (les grosses
# sorties) : AlloCiné sert a completer avec les petites sorties (arthouse,
# distribution limitee) que JPBOX ne reference meme pas.
ALLOCINE_BASE_URL = os.environ.get("ALLOCINE_BASE_URL", "https://www.allocine.fr")
ALLOCINE_USER_AGENT = "PredimovieBot/1.0 (projet etudiant, usage academique)"
ALLOCINE_DELAI_ENTRE_REQUETES = 1.5  # secondes

# Clé partagée avec N8n pour protéger les routes /scrape/* : pas de vrais
# utilisateurs ici (pas besoin de JWT), juste un secret à connaître.
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")

# Clé API Anthropic, pour extraire les 3 mots-cles du synopsis (Claude Haiku)
SYNOPSIS_ENRICHMENT_API_KEY = os.environ.get("SYNOPSIS_ENRICHMENT_API_KEY", "")
