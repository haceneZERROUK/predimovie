# Decorateurs pour proteger les vues. On n'utilise pas django.contrib.auth
# vu que les comptes sont dans la base du backend : on garde juste le token
# JWT dans la session Django.
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def connexion_requise(vue):
    @wraps(vue)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("token"):
            messages.warning(request, "Connectez-vous pour acceder a cette page.")
            return redirect("predictions:login")
        return vue(request, *args, **kwargs)

    return wrapper


def admin_requis(vue):
    @wraps(vue)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("token"):
            messages.warning(request, "Connectez-vous pour acceder a cette page.")
            return redirect("predictions:login")
        if request.session.get("role") != "admin":
            messages.error(request, "Reserve aux administrateurs.")
            return redirect("predictions:accueil")
        return vue(request, *args, **kwargs)

    return wrapper
