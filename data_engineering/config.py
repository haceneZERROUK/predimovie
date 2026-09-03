# Toute la config du scraper au meme endroit, pour eviter de refaire des
# os.environ.get un peu partout
import os

# cle API TMDB
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# JPBOX, la source des entrees box-office
JPBOX_BASE_URL = os.environ.get("JPBOX_BASE_URL", "https://www.jpbox-office.com")

# codes "vue" JPBOX = le pays du classement
JPBOX_VUE_FRANCE = 2
JPBOX_VUE_INTERNATIONAL = 5

# on s'identifie et on attend entre 2 requetes, le site s'est deja plaint
# des bots qui tapent trop fort
JPBOX_USER_AGENT = "PredimovieBot/1.0 (projet etudiant, usage academique)"
JPBOX_DELAI_ENTRE_REQUETES = 1.5  # secondes

# AlloCine, pour les sorties que JPBOX ne reference pas
ALLOCINE_BASE_URL = os.environ.get("ALLOCINE_BASE_URL", "https://www.allocine.fr")
ALLOCINE_USER_AGENT = "PredimovieBot/1.0 (projet etudiant, usage academique)"
ALLOCINE_DELAI_ENTRE_REQUETES = 1.5  # secondes

# secret partage pour proteger les routes /scrape/*
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")

# cle API Anthropic, pour les mots-cles du synopsis
SYNOPSIS_ENRICHMENT_API_KEY = os.environ.get("SYNOPSIS_ENRICHMENT_API_KEY", "")
