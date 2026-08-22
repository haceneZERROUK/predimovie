from django.urls import path

from predictions import views

app_name = "predictions"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.accueil_view, name="accueil"),
]
