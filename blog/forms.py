# blog/forms.py
from django import forms
from django.forms import modelformset_factory
from .models import Navette, Employe, Equipement

class NavetteForm(forms.ModelForm):
    achauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )

    rchauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )

    aveh = forms.ModelChoiceField(
        queryset=Equipement.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )

    rveh = forms.ModelChoiceField(
        queryset=Equipement.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )

    class Meta:
        model = Navette
        fields = ['ligne', 'adatserv', 'achauffeur', 'rchauffeur', 'aveh', 'rveh']
        widgets = {
            'adatserv': forms.DateInput(attrs={'type': 'date'}),
        }

NavetteFormSet = modelformset_factory(
    Navette,
    form=NavetteForm,
    extra=15,
    can_delete=True
)
