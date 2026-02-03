from django.contrib import admin
from rangefilter.filters import DateRangeFilter
from .models import Navette

@admin.register(Navette)
class NavetteAdmin(admin.ModelAdmin):
    list_display = (
        'ligne_code',
        'origine',
        'destination',
        'klm',
        'adatserv',
        'achauffeur_code',
        'chauffeur_nom',
        'aveh',
    )
    list_filter = (
    'aveh',
    ('adatserv', DateRangeFilter),  # filtre entre 2 dates
)
    def ligne_code(self, obj):
        return obj.ligne.code
    ligne_code.short_description = "Ligne"

    def origine(self, obj):
        return obj.ligne.origine
    origine.short_description = "Origine"

    def destination(self, obj):
        return obj.ligne.dest
    destination.short_description = "Destination"

    def klm(self, obj):
        return obj.ligne.klm
    klm.short_description = "Km"

    # 🔹 garde le champ brut tel qu'il est dans la table navette
    def achauffeur_code(self, obj):
        return obj.achauffeur_id  # Django ajoute automatiquement "_id"
    achauffeur_code.short_description = "Achauffeur"

    # 🔹 affiche le nom de l'employé lié
    def chauffeur_nom(self, obj):
        return obj.achauffeur.nom_emp if obj.achauffeur else None
    chauffeur_nom.short_description = "Chauffeur"
    
from django.contrib import admin
from django.utils.html import format_html
from .models import Ligne


@admin.register(Ligne)
class LigneAdmin(admin.ModelAdmin):

    list_display = (
        'code', 'origine', 'dest', 'agence', 'klm', 'actif',
        'boutons_actions'
    )

    list_filter = ('actif', 'agence')
    search_fields = ('code', 'origine', 'dest', 'agence')
    ordering = ('code',)

    def boutons_actions(self, obj):
        return format_html(
            '''
            <a class="button"
               style="background:#007bff; color:white;
                      padding:4px 8px; border-radius:4px;
                      text-decoration:none; margin-right:6px;"
               href="/admin/blog/ligne/{}/change/">
               ✏️ Modifier
            </a>
            <a class="button"
               style="background:#28a745; color:white;
                      padding:4px 8px; border-radius:4px;
                      text-decoration:none;"
               target="_blank"
               href="https://www.google.com/maps/dir/?api=1&origin={}&destination={}">
               🗺️ Itinéraire
            </a>
            ''',
            obj.pk,
            obj.origine,
            obj.dest
        )

    boutons_actions.short_description = "Actions"

from django.contrib import admin
from django.utils.html import format_html
from .models import Equipement

@admin.register(Equipement)
class EquipementAdmin(admin.ModelAdmin):
    list_display = ('cod_equ', 'des_equ', 'mrq_equ', 'mod_equ', 'dat_aqu_equ', 'cod_sta', 'bouton_modifier')
    search_fields = ('cod_equ', 'des_equ', 'mrq_equ', 'mod_equ')
    list_filter = ('cod_sta', 'mrq_equ')

    def bouton_modifier(self, obj):
        return format_html(
            '<a class="button" style="background:#007bff; color:white; padding:4px 8px; border-radius:4px; text-decoration:none;" href="{}">✏️ Modifier</a>',
            f'/admin/blog/equipement/{obj.pk}/change/'
        )

    bouton_modifier.short_description = "Action"