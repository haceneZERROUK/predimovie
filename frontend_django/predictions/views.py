from datetime import date, datetime, timedelta

import jwt
from django.contrib import messages
from django.shortcuts import redirect, render

from predictions.api_client import (
    ErreurAPI,
    films_a_venir,
    historique_predictions,
    lister_comptes,
    metriques_brutes,
)
from predictions.api_client import creer_compte as appel_creer_compte
from predictions.api_client import login as appel_login
from predictions.api_client import predict as appel_predict
from predictions.api_client import relancer_predictions as appel_relancer
from predictions.api_client import supprimer_compte as appel_supprimer_compte
from predictions.decorators import admin_requis, connexion_requise
from predictions.metrics_parser import parser_metriques


def landing_view(request):
    """Page d'accueil publique, accessible sans etre connecte."""
    return render(request, "predictions/landing.html")


def login_view(request):
    if request.session.get("token"):
        return redirect("predictions:accueil")

    if request.method == "POST":
        mail = request.POST.get("mail", "")
        mot_de_passe = request.POST.get("mot_de_passe", "")
        try:
            resultat = appel_login(mail, mot_de_passe)
        except ErreurAPI as erreur:
            messages.error(request, str(erreur))
            return render(request, "predictions/login.html")

        token = resultat["access_token"]
        # le role est dans le token, pas dans la reponse. On le lit juste
        # pour l'affichage, c'est le backend qui verifie vraiment.
        contenu_token = jwt.decode(token, options={"verify_signature": False})

        request.session["token"] = token
        request.session["mail"] = contenu_token["sub"]
        request.session["role"] = contenu_token["role"]
        return redirect("predictions:accueil")

    return render(request, "predictions/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("predictions:login")


@connexion_requise
def accueil_view(request):
    return render(request, "predictions/accueil.html")


def _prochain_mercredi():
    """Date du prochain mercredi. Recopie du backend, pour garder les
    services independants."""
    aujourdhui = date.today()
    jours_a_ajouter = (2 - aujourdhui.weekday()) % 7
    return aujourdhui + timedelta(days=jours_a_ajouter)


@connexion_requise
def top10_view(request):
    token = request.session["token"]
    # dates affichees par defaut si l'API ne renvoie aucun film
    mercredi = _prochain_mercredi()
    contexte = {"date_debut": mercredi, "date_fin": mercredi + timedelta(days=3)}
    try:
        films = films_a_venir(token)
    except ErreurAPI as erreur:
        messages.error(request, str(erreur))
        return render(request, "predictions/top10.html", {**contexte, "predictions": []})

    # une prediction par film. Si l'une plante on passe au suivant plutot
    # que de casser toute la page.
    predictions = []
    for film in films:
        try:
            resultat = appel_predict(film["id_oeuvre"], token)
        except ErreurAPI:
            continue
        # l'API renvoie la date en texte ISO, on la parse pour que le
        # filtre |date du template puisse la formater
        texte_date_sortie = film.get("date_sortie")
        resultat["date_sortie"] = (
            date.fromisoformat(texte_date_sortie) if texte_date_sortie else None
        )
        resultat["synopsis"] = film.get("synopsis")
        predictions.append(resultat)

    # pas besoin de couper a 10, l'API ne renvoie que la semaine a venir
    predictions.sort(key=lambda p: p["entrees_premiere_semaine_predites"], reverse=True)

    # pourcentage par rapport au premier du classement, juste pour la
    # petite jauge du template
    plus_haute_prediction = (
        predictions[0]["entrees_premiere_semaine_predites"] if predictions else 0
    )
    for prediction in predictions:
        prediction["part_du_max"] = (
            round(100 * prediction["entrees_premiere_semaine_predites"] / plus_haute_prediction)
            if plus_haute_prediction
            else 0
        )

    # on recale les dates du titre sur la semaine des films renvoyes :
    # l'API peut retomber sur la semaine d'avant si le scraping n'est pas
    # encore passe. On affiche toujours mercredi -> samedi.
    dates_films = [p["date_sortie"] for p in predictions if p["date_sortie"]]
    if dates_films:
        premiere_date = min(dates_films)
        mercredi_de_la_semaine = premiere_date - timedelta(days=(premiere_date.weekday() - 2) % 7)
        contexte = {
            "date_debut": mercredi_de_la_semaine,
            "date_fin": mercredi_de_la_semaine + timedelta(days=3),
        }

    return render(request, "predictions/top10.html", {**contexte, "predictions": predictions})


def _gravite_ecart(ecart, reel):
    """Classe l'ecart selon son amplitude et pas son signe : se tromper de
    500k en moins est aussi grave que 500k en plus."""
    if ecart is None or not reel:
        return "text-ink-tertiary"
    pct = abs(ecart) / reel
    if pct < 0.2:
        return "text-green-400"
    if pct < 0.5:
        return "text-yellow-400"
    return "text-red-400"


@admin_requis
def historique_view(request):
    token = request.session["token"]
    semaine_choisie = request.GET.get("semaine") or ""
    try:
        resultat = historique_predictions(token, semaine=semaine_choisie or None)
    except ErreurAPI as erreur:
        messages.error(request, str(erreur))
        resultat = {"predictions": [], "semaines_disponibles": []}
    for ligne in resultat["predictions"]:
        ligne["gravite"] = _gravite_ecart(ligne["ecart"], ligne["entrees_premiere_semaine_reelles"])
    contexte = {
        "historique": resultat["predictions"],
        # meme parsing des dates que dans top10_view
        "semaines_disponibles": [date.fromisoformat(s) for s in resultat["semaines_disponibles"]],
        "semaine_choisie": semaine_choisie,
    }
    return render(request, "predictions/historique.html", contexte)


@admin_requis
def relancer_view(request):
    token = request.session["token"]
    if request.method == "POST":
        try:
            resultat = appel_relancer(token)
            messages.success(request, f"{resultat['nombre_predictions']} predictions recalculees.")
        except ErreurAPI as erreur:
            messages.error(request, str(erreur))
    return redirect("predictions:accueil")


@admin_requis
def monitoring_view(request):
    token = request.session["token"]
    try:
        texte = metriques_brutes(token)
        metriques = parser_metriques(texte)
    except ErreurAPI as erreur:
        messages.error(request, str(erreur))
        metriques = None
    return render(request, "predictions/monitoring.html", {"metriques": metriques})


@admin_requis
def comptes_view(request):
    token = request.session["token"]
    try:
        comptes = lister_comptes(token)
    except ErreurAPI as erreur:
        messages.error(request, str(erreur))
        comptes = []

    # pareil, les dates arrivent en texte et il faut les parser
    for compte in comptes:
        compte["date_inscription"] = date.fromisoformat(compte["date_inscription"])
        if compte["derniere_connexion"]:
            compte["derniere_connexion"] = datetime.fromisoformat(compte["derniere_connexion"])

    return render(request, "predictions/comptes.html", {"comptes": comptes})


@admin_requis
def creer_compte_view(request):
    if request.method == "POST":
        token = request.session["token"]
        mail = request.POST.get("mail", "")
        mot_de_passe = request.POST.get("mot_de_passe", "")
        nom_cinema = request.POST.get("nom_cinema", "")
        try:
            appel_creer_compte(mail, mot_de_passe, nom_cinema, token)
            messages.success(request, f"Compte cree pour {nom_cinema}.")
            return redirect("predictions:comptes")
        except ErreurAPI as erreur:
            messages.error(request, str(erreur))

    return render(request, "predictions/creer_compte.html")


@admin_requis
def supprimer_compte_view(request, id_compte):
    if request.method == "POST":
        token = request.session["token"]
        try:
            appel_supprimer_compte(id_compte, token)
            messages.success(request, "Compte cinema supprime.")
        except ErreurAPI as erreur:
            messages.error(request, str(erreur))
    return redirect("predictions:comptes")
