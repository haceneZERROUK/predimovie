# Decorateurs maison pour proteger les vues. On ne se sert pas du systeme
# d'auth Django (django.contrib.auth) : les comptes vivent dans la table
# `compte` cote backend FastAPI, pas dans la base sqlite de Django. Le
# token JWT recu au login est juste garde dans la session Django.
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def connexion_requise(vue):
    @wraps(vue)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("token"):
            messages.warning(request, "Connecte-toi pour acceder a cette page.")
            return redirect("predictions:login")
        return vue(request, *args, **kwargs)

    return wrapper


def admin_requis(vue):
    @wraps(vue)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("token"):
            messages.warning(request, "Connecte-toi pour acceder a cette page.")
            return redirect("predictions:login")
        if request.session.get("role") != "admin":
            messages.error(request, "Reserve aux administrateurs.")
            return redirect("predictions:accueil")
        return vue(request, *args, **kwargs)

    return wrapper
