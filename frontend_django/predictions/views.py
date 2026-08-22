import jwt
from django.contrib import messages
from django.shortcuts import redirect, render

from predictions.api_client import ErreurAPI
from predictions.api_client import login as appel_login
from predictions.decorators import connexion_requise


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
