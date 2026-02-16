# blog/forms.py
from django import forms
from django.forms import modelformset_factory
from .models import Navette, Employe, Equipement
from django.db.models import Q

class NavetteForm(forms.ModelForm):
    achauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.filter(mat_emp__gte=14650),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )

    rchauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.filter(mat_emp__gte=14650),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )

    aveh = forms.ModelChoiceField(
        queryset=Equipement.objects.filter(
        Q(cod_equ__gte='00250', cod_equ__lte='00530') |
        Q(cod_equ__gte='02001', cod_equ__lte='04090')
    ),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )

    rveh = forms.ModelChoiceField(
        queryset=Equipement.objects.filter(
        Q(cod_equ__gte='00250', cod_equ__lte='00530') |
        Q(cod_equ__gte='02001', cod_equ__lte='04090')
    ),
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
