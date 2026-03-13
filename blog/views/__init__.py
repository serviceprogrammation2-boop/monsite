from .views_navette import navette_manage, navette_edit, navette_add, liste_navettes
from .views_ajax import search_employe, search_equipement, search_ligne
from .views_pdf_navette import navettes_pdf, navettes1_pdf, navettes2_pdf, navettes3_pdf
from .views_ligne import ligne_list, ligne_pdf
from .views_equipement import equipement_list, equipement_pdf, equipement1_pdf, equipement2_pdf, equipement3_pdf

# Rapports et chauffeurs encore dans views1.py
from ..views1 import (
    raportjs_pdf, raportjs_sortie_pdf, raportjs1_pdf, raportjs_mois_pdf,
    chauffeurs_pdf, chauffeurs1_pdf, chauffeurs2_pdf, chauffeurs_sortie_pdf
)