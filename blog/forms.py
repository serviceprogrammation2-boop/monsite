# blog/forms.py
from django import forms
from django.forms import modelformset_factory
from .models import Navette, Employe, Equipement
from django.db.models import Q

class NavetteForm(forms.ModelForm):
    achauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-employe'})
    )

    rchauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-employe'})
    )

    aveh = forms.ModelChoiceField(
        queryset=Equipement.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-equipement'})
    )

    rveh = forms.ModelChoiceField(
        queryset=Equipement.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-equipement'})
    )

    class Meta:
        model = Navette
        fields = ['ligne', 'adatserv', 'achauffeur', 'rchauffeur', 'aveh', 'rveh']
        widgets = {
            'adatserv': forms.DateInput(attrs={'type': 'date'}),
        }

    # 🔹 Transformer les champs vides en None
    def clean_aveh(self):
        return self.cleaned_data.get('aveh') or None

    def clean_rveh(self):
        return self.cleaned_data.get('rveh') or None


NavetteFormSet = modelformset_factory(
    Navette,
    form=NavetteForm,
    extra=15,
    can_delete=True
)
