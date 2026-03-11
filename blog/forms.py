from django import forms
from django.forms import modelformset_factory
from .models import Navette, Employe, Equipement, Ligne


# ✅ Form pour le formset (lignes vides permises)
class NavetteForm(forms.ModelForm):
    achauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-employe'})
    )
    rchauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-employe'})
    )
    aveh = forms.ModelChoiceField(
        queryset=Equipement.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-equipement'})
    )
    rveh = forms.ModelChoiceField(
        queryset=Equipement.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-equipement'})
    )

    class Meta:
        model = Navette
        fields = ['ligne', 'adatserv', 'achauffeur', 'rchauffeur', 'aveh', 'rveh', 'asens', 'atypsrv', 'nda']
        widgets = {'adatserv': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ligne'].required = False
        self.fields['adatserv'].required = False
        for field_name in ['asens', 'atypsrv', 'nda']:
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        ligne = cleaned_data.get('ligne')
        adatserv = cleaned_data.get('adatserv')
        if not ligne and not adatserv:
            self._errors.clear()
            return cleaned_data
        if ligne and not adatserv:
            self.add_error('adatserv', 'Date requise.')
        if adatserv and not ligne:
            self.add_error('ligne', 'Ligne requise.')
        return cleaned_data

    def clean_aveh(self):
        return self.cleaned_data.get('aveh') or None

    def clean_rveh(self):
        return self.cleaned_data.get('rveh') or None

    def validate_unique(self):
        if not self.cleaned_data.get('ligne') and not self.cleaned_data.get('adatserv'):
            return
        super().validate_unique()


# ✅ Formset utilise NavetteForm
NavetteFormSet = modelformset_factory(
    Navette,
    form=NavetteForm,
    extra=15,
    can_delete=True,
)


# ✅ Form séparé pour l'édition — validation normale, pas de lignes vides
class NavetteEditForm(forms.ModelForm):
    ligne = forms.ModelChoiceField(
        queryset=Ligne.objects.all().order_by('code'),
        required=True,
        widget=forms.Select(attrs={'class': 'select2-ligne'})
    )
    achauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-employe'})
    )
    rchauffeur = forms.ModelChoiceField(
        queryset=Employe.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-employe'})
    )
    aveh = forms.ModelChoiceField(
        queryset=Equipement.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-equipement'})
    )
    rveh = forms.ModelChoiceField(
        queryset=Equipement.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select2-ajax-equipement'})
    )

    class Meta:
        model = Navette
        fields = ['ligne', 'adatserv', 'achauffeur', 'rchauffeur', 'aveh', 'rveh', 'asens']
        widgets = {'adatserv': forms.DateInput(attrs={'type': 'date'})}

    def clean_aveh(self):
        return self.cleaned_data.get('aveh') or None

    def clean_rveh(self):
        return self.cleaned_data.get('rveh') or None