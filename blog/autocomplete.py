# blog/autocomplete.py
from dal import autocomplete
from .models import Employe, Equipement

class EmployeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Employe.objects.all()
        if self.q:
            qs = qs.filter(nom_emp__icontains=self.q)
        return qs

class EquipementAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Equipement.objects.all()
        if self.q:
            qs = qs.filter(cod_equ__icontains=self.q)
        return qs
