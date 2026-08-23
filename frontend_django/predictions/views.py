from datetime import date

import jwt
from django.contrib import messages
from django.shortcuts import redirect, render

from predictions.api_client import (
    ErreurAPI,
    films_a_venir,
    historique_predictions,
    metriques_brutes,
)
from predictions.api_client import login as appel_login
from predictions.api_client import predict as appel_predict
from predictions.api_client import relancer_predictions as appel_relancer
from predictions.decorators import admin_requis, connexion_requise
from predictions.metrics_parser import parser_metriques


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
        # le role n'est pas dans la reponse de /auth/login, il est encode
        # dans le token lui-meme : on le lit juste pour l'affichage, la
        # verification de securite se fait cote backend a chaque appel.
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


@connexion_requise
def top10_view(request):
    token = request.session["token"]
    try:
        films = films_a_venir(token)
    except ErreurAPI as erreur:
        messages.error(request, str(erreur))
        return render(request, "predictions/top10.html", {"predictions": []})

    # on lance une prediction par film pas encore sorti ; si l'un d'eux
    # plante (film mal renseigne en base par exemple), on le passe et on
    # continue avec les autres plutot que de faire planter toute la page
    predictions = []
    for film in films:
        try:
            resultat = appel_predict(film["id_oeuvre"], token)
        except ErreurAPI:
            continue
        # l'API renvoie une date ISO (ex: "2026-12-16") en texte brut : on
        # la parse en vraie date pour que le template puisse l'afficher au
        # format francais (jj/mm/aaaa) avec le filtre |date
        texte_date_sortie = film.get("date_sortie")
        resultat["date_sortie"] = (
            date.fromisoformat(texte_date_sortie) if texte_date_sortie else None
        )
        predictions.append(resultat)

    # /films-a-venir ne renvoie deja que les films du mercredi a venir (pas
    # tout ce qui sort dans les mois qui viennent), pas besoin de couper a 10
    predictions.sort(key=lambda p: p["entrees_premiere_semaine_predites"], reverse=True)

    return render(request, "predictions/top10.html", {"predictions": predictions})


@admin_requis
def historique_view(request):
    token = request.session["token"]
    try:
        historique = historique_predictions(token)
    except ErreurAPI as erreur:
        messages.error(request, str(erreur))
        historique = []
    return render(request, "predictions/historique.html", {"historique": historique})


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
