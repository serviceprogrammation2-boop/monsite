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
    extra=9,
    can_delete=True,
)


class NavetteEditForm(forms.ModelForm):
    
    ligne = forms.ModelChoiceField(
        queryset=Ligne.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'select2-ligne', 'style': 'width:100%'})
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Ligne
        if 'ligne' in self.data:
            try:
                self.fields['ligne'].queryset = Ligne.objects.filter(code=self.data.get('ligne'))
            except Exception:
                pass
        elif self.instance and self.instance.pk:
            self.fields['ligne'].queryset = Ligne.objects.filter(code=self.instance.ligne_id)

        # ✅ Achauffeur
        if 'achauffeur' in self.data:
            try:
                self.fields['achauffeur'].queryset = Employe.objects.filter(pk=self.data.get('achauffeur'))
            except Exception:
                pass
        elif self.instance and self.instance.pk and self.instance.achauffeur:
            self.fields['achauffeur'].queryset = Employe.objects.filter(pk=self.instance.achauffeur.pk)

        # ✅ Rchauffeur
        if 'rchauffeur' in self.data:
            try:
                self.fields['rchauffeur'].queryset = Employe.objects.filter(pk=self.data.get('rchauffeur'))
            except Exception:
                pass
        elif self.instance and self.instance.pk and self.instance.rchauffeur:
            self.fields['rchauffeur'].queryset = Employe.objects.filter(pk=self.instance.rchauffeur.pk)

        # ✅ Aveh
        if 'aveh' in self.data:
            try:
                self.fields['aveh'].queryset = Equipement.objects.filter(pk=self.data.get('aveh'))
            except Exception:
                pass
        elif self.instance and self.instance.pk and self.instance.aveh:
            self.fields['aveh'].queryset = Equipement.objects.filter(pk=self.instance.aveh.pk)

        # ✅ Rveh
        if 'rveh' in self.data:
            try:
                self.fields['rveh'].queryset = Equipement.objects.filter(pk=self.data.get('rveh'))
            except Exception:
                pass
        elif self.instance and self.instance.pk and self.instance.rveh:
            self.fields['rveh'].queryset = Equipement.objects.filter(pk=self.instance.rveh.pk)

    def clean_aveh(self):
        return self.cleaned_data.get('aveh') or None

    def clean_rveh(self):
        return self.cleaned_data.get('rveh') or None