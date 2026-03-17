from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, IntegerField
from django.contrib.auth.decorators import login_required, permission_required
from datetime import datetime

from ..models import Navette, Ligne, Employe, Equipement
from ..forms import NavetteFormSet, NavetteEditForm


def configure_formset(formset):
    employes_qs = Employe.objects.all().order_by("nom_emp")
    equipements_qs = Equipement.objects.all()
    for form in formset.forms:
        form.fields['achauffeur'].queryset = employes_qs
        form.fields['rchauffeur'].queryset = employes_qs
        form.fields['aveh'].queryset = equipements_qs
        form.fields['rveh'].queryset = equipements_qs


def navette_add(request):
    if request.method == "POST":
        form = NavetteEditForm(request.POST)
        if form.is_valid():
            form.save()
            if request.POST.get("action") == "save_another":
                return redirect('navette_add')
            return redirect('liste_navettes')
    else:
        form = NavetteEditForm()
    return render(request, 'blog/navette_add.html', {'form': form})


def navette_edit(request, id):
    navette = get_object_or_404(Navette, id=id)
    if request.method == "POST":
        form = NavetteEditForm(request.POST, instance=navette)
        if form.is_valid():
            form.save()
            return redirect('liste_navettes')
    else:
        form = NavetteEditForm(instance=navette)
    return render(request, 'blog/navette_edit.html', {'form': form})


@login_required
@permission_required('blog.can_add_navette_form', raise_exception=True)
def navette_manage(request):
    today = now().date()
    auto = request.GET.get("auto") or request.POST.get("auto_value")

    lignes_map = {
        "grand jour": [118, 147, 145, 120, 132, 233],
        "jour":       [146, 189, 142, 209, 406, 149, 194, 104, 295],
        "nuit1":       [961, 518, 117, 507, 520, 504, 506],
        "nuit2":       [503, 512, 501, 502, 509, 964, 521],
        "agence":     [100, 963, 183, 102, 101, 143, 144],
    }
    codes_lignes = lignes_map.get(auto, [])

    initial_data = []
    if codes_lignes:
        preserved_order = Case(
            *[When(code=code, then=pos) for pos, code in enumerate(codes_lignes)],
            output_field=IntegerField()
        )
        lignes = Ligne.objects.filter(code__in=codes_lignes).order_by(preserved_order)
        for ligne in lignes:
            derniere = Navette.objects.filter(
                ligne=ligne,
                adatserv__lt=today
            ).order_by('-adatserv').first()

            initial = {"ligne": ligne, "adatserv": today}
            if derniere:
                initial["rchauffeur"] = derniere.rchauffeur
                initial["rveh"] = derniere.rveh
            initial_data.append(initial)

    if request.method == "POST":
        formset = NavetteFormSet(request.POST, queryset=Navette.objects.none())
        configure_formset(formset)

        if formset.is_valid():
            for form in formset:
                cd = form.cleaned_data
                if not cd or cd.get("DELETE") or not cd.get("ligne") or not cd.get("adatserv"):
                    continue

                obj = form.save(commit=False)

                if auto == "nuit1":
                    obj.atypsrv, obj.nda = "N", 2
                elif auto == "nuit2":
                    obj.atypsrv, obj.nda = "N", 2
                elif auto == "jour":
                    obj.atypsrv, obj.nda = "J", 1
                elif auto == "grand jour":
                    obj.atypsrv, obj.nda = "G", 1
                elif auto == "agence":
                    obj.atypsrv, obj.nda = "A", 1

                if not obj.asens:
                    obj.asens = "A"

                Navette.objects.filter(
                    ligne=obj.ligne,
                    asens=obj.asens,
                    atypsrv=obj.atypsrv,
                    adatserv=obj.adatserv
                ).delete()
                obj.save()

            for form in formset.deleted_forms:
                if form.instance.pk:
                    form.instance.delete()

            return redirect('/navettes/gestion/')

    else:
        queryset = Navette.objects.none()
        formset = NavetteFormSet(queryset=queryset, initial=initial_data)
        configure_formset(formset)

    return render(request, "blog/navette_formset.html", {"formset": formset, "auto": auto})


def liste_navettes(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    achauffeur = request.GET.get("achauffeur")
    aveh = request.GET.get("aveh")
    sortie = request.GET.get("sortie")

    navettes = Navette.objects.all().order_by('-adatserv')

    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            navettes = navettes.filter(adatserv__range=[start_date, end_date])
        except ValueError:
            pass
    else:
        today = now().date()
        navettes = navettes.filter(adatserv=today)
        start = str(today)
        end = str(today)

    if achauffeur:
        navettes = navettes.filter(Q(achauffeur__mat_emp__icontains=achauffeur))
    if aveh:
        navettes = navettes.filter(aveh__icontains=aveh)
    if sortie:
        navettes = navettes.filter(ligne__sortie__icontains=sortie)

    paginator = Paginator(navettes, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "blog/navette_list.html", {
        "page_obj": page_obj,
        "navettes": page_obj.object_list,
        "start": start or "",
        "end": end or "",
        "achauffeur": achauffeur or "",
        "aveh": aveh or "",
        "sortie": sortie or "",
        "request": request,
    })