# blog/admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from django.forms import modelformset_factory
from django.utils.html import format_html
from rangefilter.filters import DateRangeFilter
from .models import Navette, Ligne, Employe


import subprocess
import tempfile
import os
from django.http import FileResponse
from django.urls import path
from django.contrib import admin

def download_backup(request):
    database_url = os.environ.get("DATABASE_URL")

    tmp_file = tempfile.NamedTemporaryFile(delete=False)

    subprocess.run([
        "pg_dump",
        database_url,
        "-f",
        tmp_file.name
    ])

    return FileResponse(
        open(tmp_file.name, 'rb'),
        as_attachment=True,
        filename="backup.sql"
    )
# -----------------------------
# Form et Formset pour ajouter plusieurs Navettes
# -----------------------------
class NavetteForm(forms.ModelForm):
    class Meta:
        model = Navette
        fields = ['ligne', 'adatserv', 'achauffeur', 'aveh', 'rveh', 'rem']

# Formset pour tableau horizontal
NavetteFormSet = modelformset_factory(
    Navette,
    form=NavetteForm,
    extra=5,       # 5 lignes vides pour ajouter
    can_delete=False
)

# -----------------------------
# Admin Navette
# -----------------------------
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
        'bouton_modifier',
        'bouton_add_multiple'
    )
    list_filter = (
        'aveh',
        ('adatserv', DateRangeFilter),
    )

    # Champs calculés
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

    def achauffeur_code(self, obj):
        return obj.achauffeur_id
    achauffeur_code.short_description = "Achauffeur"

    def chauffeur_nom(self, obj):
        return obj.achauffeur.nom_emp if obj.achauffeur else None
    chauffeur_nom.short_description = "Chauffeur"

    # Bouton modifier
    def bouton_modifier(self, obj):
        return format_html(
            '<a class="button" style="background:#007bff; color:white; padding:4px 8px; '
            'border-radius:4px; text-decoration:none;" href="/admin/blog/navette/{}/change/">✏️ Modifier</a>',
            obj.pk
        )
    bouton_modifier.short_description = "Action"

    # Bouton add multiple
    def bouton_add_multiple(self, obj=None):
        return format_html(
            '<a class="button" style="background:#28a745; color:white; padding:4px 8px; '
            'border-radius:4px; text-decoration:none;" href="add-multiple/">➕ Ajouter</a>'
        )
    bouton_add_multiple.short_description = "Ajouter"

    # -----------------------------
    # URLs custom
    # -----------------------------
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('add-multiple/', self.admin_site.admin_view(self.add_multiple), name='navette_add_multiple'),
        ]
        return my_urls + urls

    # -----------------------------
    # Vue add multiple
    # -----------------------------
    def add_multiple(self, request):
        if request.method == "POST":
            formset = NavetteFormSet(request.POST, queryset=Navette.objects.none())
            if formset.is_valid():
                formset.save()
                self.message_user(request, "Navettes ajoutées avec succès")
                return redirect('..')  # retourne à la liste Navette
        else:
            formset = NavetteFormSet(queryset=Navette.objects.none())

        return render(request, "admin/navette_add_multiple.html", {'formset': formset})

    

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

