from django.urls import path
from . import views, reports

urlpatterns = [
    path('navettes/', views.liste_navettes, name='liste_navettes'),
    path("navettes/pdf/", views.navettes_pdf, name="navettes_pdf"),
    path("navettes1/pdf/", views.navettes1_pdf, name="navettes1_pdf"),
    path("navettes2/pdf/", views.navettes2_pdf, name="navettes2_pdf"),
    path("navettes3/pdf/", views.navettes3_pdf, name="navettes3_pdf"),
    
    path("raportjs/pdf/", views.raportjs_pdf, name="raportjs_pdf"),
    path("raportjs_sortie/pdf/", views.raportjs_sortie_pdf, name="raportjs_sortie_pdf"),
    path("raportjs1/pdf/", views.raportjs1_pdf, name="raportjs1_pdf"),
    path("raportjs_mois/pdf/", views.raportjs_mois_pdf, name="raportjs_mois_pdf"),
    
    path("chauffeurs/pdf/", views.chauffeurs_pdf, name="chauffeurs_pdf"),
    path("chauffeurs1/pdf/", views.chauffeurs1_pdf, name="chauffeurs1_pdf"),
    path("chauffeurs2/pdf/", views.chauffeurs2_pdf, name="chauffeurs2_pdf"),
    path("chauffeurs_sortie/pdf/", views.chauffeurs_sortie_pdf, name="chauffeurs_sortie_pdf"),
    path("lignes/", views.ligne_list, name="ligne_list"),
    path('export/pdf/', reports.export_navettes_pdf, name='export_navettes_pdf'),
    path("lignes/pdf/", views.ligne_pdf, name="ligne_pdf"),
    
    path('equipements/', views.equipement_list, name='equipement_list'),
    path('equipements/pdf/', views.equipement_pdf, name='equipement_pdf'),
    path('equipement1/pdf/', views.equipement1_pdf, name='equipement1_pdf'),
    path('equipement2/pdf/', views.equipement2_pdf, name='equipement2_pdf'),
    path('equipement3/pdf/', views.equipement3_pdf, name='equipement3_pdf'),
]
