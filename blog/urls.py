from django.urls import path
from .views import (
    navette_manage, navette_edit, navette_add, liste_navettes,
    search_employe, search_equipement, search_ligne,
    navettes_pdf, navettes1_pdf, navettes2_pdf, navettes3_pdf,
    raportjs_pdf, raportjs_sortie_pdf, raportjs1_pdf, raportjs_mois_pdf,
    chauffeurs_pdf, chauffeurs1_pdf, chauffeurs2_pdf, chauffeurs_sortie_pdf,
    ligne_list, ligne_pdf, ligne_excel,
    equipement_list, equipement_pdf, equipement1_pdf, equipement2_pdf, equipement3_pdf
)
from . import reports


urlpatterns = [

    path('', navette_manage, name='home'),
    path('navette/<int:id>/edit/', navette_edit, name='navette_edit'),
    path('navettes/ajouter/', navette_add, name='navette_add'),
    path('ajax/ligne/', search_ligne, name='search_ligne'),

    path('navettes/', liste_navettes, name='liste_navettes'),
    path('navettes/gestion/', navette_manage, name='navette_manage'),

    path('ajax/employe/', search_employe, name='search_employe'),
    path('ajax/equipement/', search_equipement, name='search_equipement'),

    path("navettes/pdf/", navettes_pdf, name="navettes_pdf"),
    path("navettes1/pdf/", navettes1_pdf, name="navettes1_pdf"),
    path("navettes2/pdf/", navettes2_pdf, name="navettes2_pdf"),
    path("navettes3/pdf/", navettes3_pdf, name="navettes3_pdf"),

    path("raportjs/pdf/", raportjs_pdf, name="raportjs_pdf"),
    path("raportjs_sortie/pdf/", raportjs_sortie_pdf, name="raportjs_sortie_pdf"),
    path("raportjs1/pdf/", raportjs1_pdf, name="raportjs1_pdf"),
    path("raportjs_mois/pdf/", raportjs_mois_pdf, name="raportjs_mois_pdf"),

    path("chauffeurs/pdf/", chauffeurs_pdf, name="chauffeurs_pdf"),
    path("chauffeurs1/pdf/", chauffeurs1_pdf, name="chauffeurs1_pdf"),
    path("chauffeurs2/pdf/", chauffeurs2_pdf, name="chauffeurs2_pdf"),
    path("chauffeurs_sortie/pdf/", chauffeurs_sortie_pdf, name="chauffeurs_sortie_pdf"),

    path("lignes/", ligne_list, name="ligne_list"),
    path('export/pdf/', reports.export_navettes_pdf, name='export_navettes_pdf'),
    path("lignes/pdf/", ligne_pdf, name="ligne_pdf"),
    path("lignes/excel/", ligne_excel, name="ligne_excel"),

    path('equipements/', equipement_list, name='equipement_list'),
    path('equipements/pdf/', equipement_pdf, name='equipement_pdf'),
    path('equipement1/pdf/', equipement1_pdf, name='equipement1_pdf'),
    path('equipement2/pdf/', equipement2_pdf, name='equipement2_pdf'),
    path('equipement3/pdf/', equipement3_pdf, name='equipement3_pdf'),
]