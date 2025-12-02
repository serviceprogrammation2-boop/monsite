from django.contrib import admin
from .models import Navette, Ligne, Employe, Equipement

@admin.register(Navette)
class NavetteAdmin(admin.ModelAdmin):
    list_display = ('nda', 'get_ligne', 'get_destination', 'get_chauffeur', 'get_vehicule', 'date_service')
    list_filter = ('ligne', 'chauffeur', 'vehicule', 'date_service')
    search_fields = ('nda', 'ligne__description', 'chauffeur__nom', 'chauffeur__prenom')

    def get_ligne(self, obj):
        return obj.ligne.description if obj.ligne else "-"
    get_ligne.short_description = "Ligne"

    def get_destination(self, obj):
        # exemple : si ta table Ligne a une destination, sinon on ajoute un champ plus tard
        return obj.ligne.description if obj.ligne else "-"
    get_destination.short_description = "Destination"

    def get_chauffeur(self, obj):
        return f"{obj.chauffeur.nom} {obj.chauffeur.prenom}" if obj.chauffeur else "-"
    get_chauffeur.short_description = "Chauffeur"

    def get_vehicule(self, obj):
        return obj.vehicule.designation if obj.vehicule else "-"
    get_vehicule.short_description = "Véhicule"



