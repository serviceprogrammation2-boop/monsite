from django import forms
from django.forms import modelformset_factory
from .models import Navette

class NavetteForm(forms.ModelForm):
    class Meta:
        model = Navette
        fields = ['ligne', 'adatserv', 'achauffeur', 'aveh', 'rveh', 'rem']
        widgets = {
            'adatserv': forms.DateInput(attrs={'type': 'date'}),
        }

# ⚠️ Ici on ne met pas queryset
NavetteFormSet = modelformset_factory(
    Navette,
    form=NavetteForm,
    extra=10,
    can_delete=True
)
