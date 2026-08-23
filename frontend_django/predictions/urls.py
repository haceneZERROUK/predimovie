from django.urls import path

from predictions import views

app_name = "predictions"

urlpatterns = [
    path("", views.landing_view, name="landing"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("accueil/", views.accueil_view, name="accueil"),
    path("top10/", views.top10_view, name="top10"),
    path("historique/", views.historique_view, name="historique"),
    path("relancer/", views.relancer_view, name="relancer"),
    path("monitoring/", views.monitoring_view, name="monitoring"),
    path("comptes/", views.comptes_view, name="comptes"),
    path("comptes/creer/", views.creer_compte_view, name="creer_compte"),
    path(
        "comptes/<int:id_compte>/supprimer/", views.supprimer_compte_view, name="supprimer_compte"
    ),
]
