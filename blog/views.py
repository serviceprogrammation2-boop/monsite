from django.shortcuts import render, redirect
from django.utils.timezone import make_aware
from django.core.paginator import Paginator
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import HttpResponse
import os
import tempfile
from .models import Navette, Ligne, Locatile  # ✅ import correct


from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from django.utils.timezone import now
from .models import Ligne, Navette
from .forms import NavetteFormSet
from django.db.models import Case, When, IntegerField
from django.contrib.auth.decorators import login_required, permission_required

import subprocess
import tempfile
import os

from django.shortcuts import get_object_or_404, redirect, render
from .forms import NavetteEditForm
def navette_add(request):
    if request.method == "POST":
        form = NavetteEditForm(request.POST)
        if form.is_valid():
            form.save()
            # ✅ Si "Enregistrer un autre" → formulaire vide
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

    employes_qs = Employe.objects.all().order_by("nom_emp")
    equipements_qs = Equipement.objects.all()

    lignes_map = {
        "grand jour": [118, 147, 145, 120, 132, 233],
        "jour": [146, 189, 142, 209, 406, 149, 194, 104, 295],
        "nuit": [961, 518, 117, 507, 520, 504, 506, 503, 512, 501, 502, 509, 964, 521],
        "agence": [100, 963, 183, 102, 101, 143, 144],
    }
    codes_lignes = lignes_map.get(auto, [])

    def configure_formset(formset):
        for form in formset.forms:
            form.fields['achauffeur'].queryset = employes_qs
            form.fields['rchauffeur'].queryset = employes_qs
            form.fields['aveh'].queryset = equipements_qs
            form.fields['rveh'].queryset = equipements_qs

    # ✅ Même niveau que configure_formset
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

            initial = {
                "ligne": ligne,
                "adatserv": today,
            }

            if derniere:
                initial["rchauffeur"] = derniere.rchauffeur
                initial["rveh"] = derniere.rveh

            initial_data.append(initial)

    # ✅ if/else au niveau de la fonction, pas dans le if codes_lignes
    if request.method == "POST":
        formset = NavetteFormSet(request.POST, queryset=Navette.objects.none())
        configure_formset(formset)

        if formset.is_valid():
            for form in formset:
                cd = form.cleaned_data
                if not cd or cd.get("DELETE") or not cd.get("ligne") or not cd.get("adatserv"):
                    continue

                obj = form.save(commit=False)

                if auto == "nuit":
                    obj.atypsrv = "N"
                    obj.nda = 2
                elif auto == "jour":
                    obj.atypsrv = "J"
                    obj.nda = 1
                elif auto == "grand jour":
                    obj.atypsrv = "G"
                    obj.nda = 1
                elif auto == "agence":
                    obj.atypsrv = "A"
                    obj.nda = 1

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
            
            # Alternative sans reverse()
            return redirect('/navettes/gestion/')  # ← votre chemin exact

    else:
        # ✅ Toujours vide au chargement
        queryset = Navette.objects.none()
        formset = NavetteFormSet(queryset=queryset, initial=initial_data)
        configure_formset(formset)

    # ✅ Une seule parenthèse fermante
    return render(request, "blog/navette_formset.html", {"formset": formset, "auto": auto})
    
from django.contrib.auth.decorators import login_required
from .models import Employe, Equipement

from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from blog.models import Employe

@login_required
def search_employe(request):
    term = request.GET.get('term', '').strip()
    
    if term:
        employes = Employe.objects.filter(
            Q(mat_emp__icontains=term) |
            Q(nom_emp__icontains=term)
        ).order_by('nom_emp')[:20]  # limite 20 pour performance
    else:
        employes = Employe.objects.none()

    results = [
        {"id": e.pk, "text": f"{e.mat_emp} - {e.nom_emp or '-'}"}
        for e in employes
    ]

    return JsonResponse({"results": results})
def liste_navettes(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    achauffeur = request.GET.get("achauffeur")
    aveh = request.GET.get("aveh")
    sortie = request.GET.get("sortie")

    navettes = Navette.objects.all().order_by('-adatserv')

    # ✅ Par défaut filtrer sur aujourd'hui si aucune date fournie
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
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

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


def navettes_pdf(request):

    # === Mappage des Libellés ===
    MAP_SV = {
        1: "Service Programmation",
        2: "Service Mouvement",
    }

    MAP_SORTIE = {
        1: "Dépôt Ben Arous",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud",
        4: "Convention",
    }

    # --- Base queryset ---
    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")

    # --- Filtres GET ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    achauffeur = request.GET.get("achauffeur")
    aveh = request.GET.get("aveh")
    mode = request.GET.get("mode")

    # === Filtres ===
    if mode == "full":
        if achauffeur:
            navettes = navettes.filter(
                Q(achauffeur__nom_emp__icontains=achauffeur)
                | Q(achauffeur__mat_emp__icontains=achauffeur)
            )
        if aveh:
            navettes = navettes.filter(aveh__icontains=aveh)

    elif mode == "simple":
        if start_str and end_str:
            try:
                start_date = make_aware(datetime.strptime(start_str, "%Y-%m-%d"))
                end_date = make_aware(datetime.strptime(end_str, "%Y-%m-%d"))
                navettes = navettes.filter(adatserv__range=(start_date, end_date))
            except ValueError:
                pass

    else:  # mixte
        if start_str and end_str:
            try:
                start_date = make_aware(datetime.strptime(start_str, "%Y-%m-%d"))
                end_date = make_aware(datetime.strptime(end_str, "%Y-%m-%d"))
                navettes = navettes.filter(adatserv__range=(start_date, end_date))
            except ValueError:
                pass
        if achauffeur:
            navettes = navettes.filter(
                Q(achauffeur__nom_emp__icontains=achauffeur)
                | Q(achauffeur__mat_emp__icontains=achauffeur)
            )
        if aveh:
            navettes = navettes.filter(aveh__icontains=aveh)

    # --- Exclusions ---
    navettes = navettes.exclude(
        Q(achauffeur__isnull=True)
        | Q(achauffeur__nom_emp="")
        | Q(aveh__isnull=True)
        | Q(aveh="")
    )

    # === Tri SV → Sortie → Agence ===
    navettes_sorted = sorted(
        navettes,
        key=lambda n: (
            n.ligne.sv or 0,
            n.ligne.sortie or 0,
            n.ligne.agence or ""
        )
    )

    # === Construction PDF ===
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=navettes.pdf"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph("Liste des Navettes SNTRI", styles['Heading1']))
    elements.append(Spacer(1, 10))
    
    # Récupération des dates depuis l'URL
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    # Format d'affichage
    date_info = ""
    if start_str and end_str:
        date_info = f"Période : {start_str} → {end_str}"
    elif start_str:
        date_info = f"À partir du : {start_str}"
    elif end_str:
        date_info = f"Jusqu'au : {end_str}"

    # Ligne affichée sous le titre
    if date_info:
        date_paragraph = Paragraph(date_info, styles['Normal'])
        elements.append(Spacer(1, 6))  # petit espace
        elements.append(date_paragraph)
        elements.append(Spacer(1, 12))  # espace avant tableau


    from itertools import groupby
    total_global = 0   # ✅ total général

    for sv, group_sv in groupby(navettes_sorted, key=lambda n: n.ligne.sv or 0):
        group_sv_list = list(group_sv)
        total_sv = 0

        # === BOUCLE SORTIE ===
        for sortie, group_sortie in groupby(group_sv_list, key=lambda n: n.ligne.sortie or 0):
            group_sortie_list = list(group_sortie)
            total_sortie = 0

            sortie_label = MAP_SORTIE.get(sortie, "Non renseignée")
            elements.append(Paragraph(f"<b>{sortie_label}</b>", styles['Heading3']))
            elements.append(Spacer(1, 8))

            # === BOUCLE AGENCE ===
            for agence, group_agence in groupby(group_sortie_list, key=lambda n: n.ligne.agence or "Sans Agence"):
                group_list = list(group_agence)

                elements.append(Paragraph(f"<b>Agence :</b> {agence}", styles['Heading4']))

                # === Tableau ===
                data = [['Ligne', 'Origine', 'Destination', 'Klm', 'Chauffeur', 'Véhicule', 'Date Service']]
                for n in group_list:
                    data.append([
                        n.ligne.code if n.ligne else "",
                        n.ligne.origine if n.ligne else "",
                        n.ligne.dest if n.ligne else "",
                        n.ligne.klm if n.ligne and n.ligne.klm else "",
                        n.achauffeur.nom_emp if n.achauffeur else "",
                        n.aveh or "",
                        n.adatserv.strftime("%d/%m/%Y") if n.adatserv else "",
                    ])

                table = Table(data, colWidths=[35, 100, 100, 25, 100, 50, 60])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ]))
                elements.append(table)

                nbr_agence = len(group_list)
                total_sortie += nbr_agence
                total_sv += nbr_agence
                total_global += nbr_agence

                elements.append(Paragraph(f"<b>Total agence {agence} :</b> {nbr_agence} navettes", styles['Normal']))
                elements.append(Spacer(1, 10))

            elements.append(Paragraph(f"<b>{sortie_label}</b> — total navettes = {total_sortie}", styles['Heading3']))
            elements.append(Spacer(1, 14))

        service_label = MAP_SV.get(sv, "Non renseigné")
        elements.append(Paragraph(f"<b>{service_label}</b> — total navettes = {total_sv}", styles['Heading2']))
        elements.append(Spacer(1, 18))

    elements.append(Paragraph(f"<b>TOTAL GÉNÉRAL :</b> {total_global} navettes", styles['Title']))
    elements.append(Spacer(1, 20))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
# === navette1 ===
def navettes1_pdf(request):
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from itertools import groupby
    
    from django.http import HttpResponse
    from django.db.models import Q
    from django.utils.timezone import make_aware
    from datetime import datetime

    # === Mappage des Libellés ===
    MAP_SV = {1: "Service Programmation", 2: "Service Mouvement"}
    MAP_SORTIE = {1: "Dépôt Ben Arous", 2: "Gare Routière Nord", 3: "Gare Routière Sud", 4: "Convention"}
    loc_map = {l.cod_loc: l.lib_loc for l in Locatile.objects.all()}

    # --- Base queryset ---
    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")

    # --- Filtres GET ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    achauffeur = request.GET.get("achauffeur")
    aveh = request.GET.get("aveh")

    if start_str and end_str:
        try:
            start_date = make_aware(datetime.strptime(start_str, "%Y-%m-%d"))
            end_date = make_aware(datetime.strptime(end_str, "%Y-%m-%d"))
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
        except:
            pass

    if achauffeur:
        navettes = navettes.filter(Q(achauffeur__nom_emp__icontains=achauffeur) | Q(achauffeur__mat_emp__icontains=achauffeur))

    if aveh:
        navettes = navettes.filter(aveh__icontains=aveh)

    navettes = navettes.exclude(Q(achauffeur__isnull=True) | Q(aveh__isnull=True) | Q(aveh=""))

    # === Tri SV → Sortie → Agence ===
    navettes_sorted = sorted(navettes, key=lambda n: (n.ligne.sv or 0, n.ligne.sortie or 0, n.ligne.agence or ""))

    # --- PDF ---
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=navettes_synthese_tableau.pdf"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>Synthèse des Navettes SNTRI</b>", styles['Title']))
    elements.append(Spacer(1, 10))

    data = [["Service", "Sortie", "Agence", "Libellé", "Total Navettes", "Total Km"]]

    total_global_navettes = 0
    total_global_km = 0

    for sv, group_sv in groupby(navettes_sorted, key=lambda n: n.ligne.sv):
        group_sv_list = list(group_sv)
        total_sv_navettes = 0
        total_sv_km = 0

        for sortie, group_sortie in groupby(group_sv_list, key=lambda n: n.ligne.sortie):
            group_sortie_list = list(group_sortie)
            total_sortie_navettes = 0
            total_sortie_km = 0

            for agence, group_agence in groupby(group_sortie_list, key=lambda n: n.ligne.agence):
                group_list = list(group_agence)
                total_km = sum(float(n.ligne.klm) for n in group_list if n.ligne and n.ligne.klm)
                total_nb = len(group_list)
                libelle = loc_map.get(agence, "Inconnue")

                data.append([
                    MAP_SV.get(sv, "Service inconnu"),
                    MAP_SORTIE.get(sortie, "Sortie inconnue"),
                    agence,
                    libelle,
                    total_nb,
                    round(total_km, 2)
                ])

                total_sortie_navettes += total_nb
                total_sortie_km += total_km
                total_sv_navettes += total_nb
                total_sv_km += total_km
                total_global_navettes += total_nb
                total_global_km += total_km

            # Ligne total sortie
            data.append([
                MAP_SV.get(sv, "Service inconnu"),
                f"Total {MAP_SORTIE.get(sortie,'')}",
                "",
                "",
                total_sortie_navettes,
                round(total_sortie_km, 2)
            ])

        # Ligne total service
        data.append([
            f"Total {MAP_SV.get(sv,'')}",
            "",
            "",
            "",
            total_sv_navettes,
            round(total_sv_km, 2)
        ])

    # Ligne total global
    data.append([
        "TOTAL GENERAL",
        "",
        "",
        "",
        total_global_navettes,
        round(total_global_km, 2)
    ])

    table = Table(data, colWidths=[120, 120, 50, 120, 70,50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (1, 1), (-1, -1), colors.beige)
    ]))

    elements.append(table)
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response

def navettes2_pdf(request):
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from itertools import groupby
    
    from django.http import HttpResponse
    from django.db.models import Q
    from django.utils.timezone import make_aware
    from datetime import datetime

    # === Mappage des Libellés ===
    MAP_SV = {1: "Service Programmation", 2: "Service Mouvement"}
    MAP_SORTIE = {1: "Dépôt Ben Arous", 2: "Gare Routière Nord", 3: "Gare Routière Sud", 4: "Convention"}
    loc_map = {l.cod_loc: l.lib_loc for l in Locatile.objects.all()}

    # --- Base queryset ---
    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")

    # --- Filtres GET ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    

    if start_str and end_str:
        try:
            start_date = make_aware(datetime.strptime(start_str, "%Y-%m-%d"))
            end_date = make_aware(datetime.strptime(end_str, "%Y-%m-%d"))
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
        except:
            pass


   

    # === Tri SV → Sortie → Agence ===
    navettes_sorted = sorted(navettes, key=lambda n: (n.ligne.sv or 0, n.ligne.sortie or 0, n.ligne.agence or ""))

    # --- PDF ---
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=navettes_synthese_tableau.pdf"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>Synthèse des Navettes SNTRI</b>", styles['Title']))
    elements.append(Spacer(1, 10))
    # Sous-titre : période sélectionnée
    periode_texte = ""
    if start_str and end_str:
        periode_texte = f"Période : {start_str} → {end_str}"
    elif start_str:
        periode_texte = f"Date : {start_str}"
    elif end_str:
        periode_texte = f"Date : {end_str}"

    if periode_texte:
        elements.append(Paragraph(f"<b>{periode_texte}</b>", styles['Heading4']))
        elements.append(Spacer(1, 8))


    data = [["Service", "Sortie", "Agence", "Libellé", "Total Navettes", "Total Km"]]

    total_global_navettes = 0
    total_global_km = 0

    for sv, group_sv in groupby(navettes_sorted, key=lambda n: n.ligne.sv):
        group_sv_list = list(group_sv)
        total_sv_navettes = 0
        total_sv_km = 0

        for sortie, group_sortie in groupby(group_sv_list, key=lambda n: n.ligne.sortie):
            group_sortie_list = list(group_sortie)
            total_sortie_navettes = 0
            total_sortie_km = 0

            for agence, group_agence in groupby(group_sortie_list, key=lambda n: n.ligne.agence):
                group_list = list(group_agence)
                total_km = sum(float(n.ligne.klm) for n in group_list if n.ligne and n.ligne.klm)
                total_nb = len(group_list)
                libelle = loc_map.get(agence, "Inconnue")

                data.append([
                    MAP_SV.get(sv, "Service inconnu"),
                    MAP_SORTIE.get(sortie, "Sortie inconnue"),
                    agence,
                    libelle,
                    total_nb,
                    round(total_km, 2)
                ])

                total_sortie_navettes += total_nb
                total_sortie_km += total_km
                total_sv_navettes += total_nb
                total_sv_km += total_km
                total_global_navettes += total_nb
                total_global_km += total_km

            # Ligne total sortie
            data.append([
                "",  # service vide
                f"Total {MAP_SORTIE.get(sortie,'')}",
                "",
                "",
                total_sortie_navettes,
                round(total_sortie_km, 2)
            ])

        # Ligne total service
        data.append([
            f"Total {MAP_SV.get(sv,'')}",
            "",
            "",
            "",
            total_sv_navettes,
            round(total_sv_km, 2)
        ])

    # Ligne total global
    data.append([
        "TOTAL GENERAL",
        "",
        "",
        "",
        total_global_navettes,
        round(total_global_km, 2)
    ])

    table = Table(data, colWidths=[120, 120, 50, 120, 70,50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (1, 1), (-1, -1), colors.beige)
    ]))

    elements.append(table)
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response

def navettes3_pdf(request):

    MAP_SORTIE = {
        1: "Dépôt Ben Arous",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud",
        4: "Convention",
    }

    navettes = Navette.objects.select_related("ligne", "achauffeur")

    # --- Filtres date ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__date__range=(start_date, end_date))
        except:
            pass

    # --- Tri ---
    navettes_sorted = navettes.order_by("ligne__sortie", "ligne__code", "adatserv")

    # --- PDF ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport.pdf"'

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet  

    styles = getSampleStyleSheet()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    elements = []

    # --- Titre ---
    elements.append(Paragraph("<b>Liste Journalière des Navettes SNTRI</b>", styles['Title']))

    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
        elements.append(Spacer(1, 10))

    from itertools import groupby

    # === GROUP BY SORTIE ===
    for sortie, group_sortie in groupby(navettes_sorted, key=lambda n: n.ligne.sortie or 0):
        group_sortie = list(group_sortie)

        sortie_label = MAP_SORTIE.get(sortie, "Non renseignée")
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>{sortie_label}</b>", styles['Heading2']))

        # === SOUS-GROUPE PAR CODE ===
        for code, group_code in groupby(group_sortie, key=lambda n: n.ligne.code if n.ligne else "???"):
            code_list = list(group_code)

            elements.append(Paragraph(f"<b>Code : {code}</b>", styles['Heading3']))
            elements.append(Spacer(1, 4))

            # === Tableau principal ===
            data = [['ord','Ligne','Origine','Destination','Agence','Date',
                     'A.Mle','A.Chauffeur','R.Mle','R.Chauffeur',
                     'A.Véhicule','R.Véhicule','KM','KM Effectif']]

            for n in code_list:

                km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
                coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
                coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
                km_effectif = km * coef_aller + km * coef_retour

                data.append([
                    n.ligne.ord if n.ligne else "",
                    n.ligne.code if n.ligne else "",
                    n.ligne.origine if n.ligne else "",
                    n.ligne.dest if n.ligne else "",
                    n.ligne.agence if n.ligne else "",
                    n.adatserv.strftime("%d") if n.adatserv else "",
                    n.achauffeur.mat_emp if n.achauffeur else "",
                    n.achauffeur.nom_emp if n.achauffeur else "",
                    n.rchauffeur.mat_emp if n.rchauffeur else "",
                    n.rchauffeur.nom_emp if n.rchauffeur else "",
                    n.aveh if n.aveh else "",
                    n.rveh if n.rveh else "",
                    km,
                    km_effectif
                ])

            table = Table(
                data,
                colWidths=[20,30,90,100,40,25,35,130,35,130,45,45,40,60]
            )
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER')
            ]))

            elements.append(table)
            elements.append(Spacer(1, 12))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response



    
def raportjs_pdf(request):

    MAP_SORTIE = {
        1: "Dépôt Ben Arous",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud",
        4: "Convention",
    }

    navettes = Navette.objects.select_related("ligne", "achauffeur")

    # --- Filtres date ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__date__range=(start_date, end_date))
        except:
            pass

    # --- Tri journalier + sortie ---
    navettes_sorted = navettes.order_by("adatserv", "ligne__sortie", "ligne__ord")

    # --- PDF ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport.pdf"'

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet  

    styles = getSampleStyleSheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    elements = []
    agences_totaux = {}


    # --- Titre ---
    elements.append(Paragraph("<b>Liste Journalière des Navettes SNTRI</b>", styles['Title']))

    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
        elements.append(Spacer(1, 10))

    from itertools import groupby

    total_global = 0

    # === TOTALS GLOBAUX ===
    grand_total_navettes = 0
    grand_total_km = 0
    grand_total_achauff = set()
    grand_total_rchauff = set()
    grand_total_aveh = set()
    grand_total_rveh = set()
    grand_total_km_effectif = 0

    # === GROUP ONLY BY SORTIE ===
    
    for sortie, group_sortie in groupby(navettes_sorted, key=lambda n: n.ligne.sortie or 0):
        group_list = list(group_sortie)
        sortie_label = MAP_SORTIE.get(sortie, "Non renseignée")

        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>{sortie_label}</b>", styles['Heading2']))

        # === Tableau (avec colonne AGENCE ajoutée) ===
        data = [['ord', 'Ligne', 'Origine', 'Destination', 'Agence', 'date', 'A.Mle', 'A.Chauffeur', 
                 'R.Mle', 'R.Chauffeur', 'A.Véhicule', 'R.Véhicule', 'KM', 'KM Effectif']]

        # Comptage agence
        agence_counter = {}

        for n in group_list:
            agence = n.ligne.agence or "Sans agence"
            agence_counter[agence] = agence_counter.get(agence, 0) + 1

            km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0

            coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
            coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0

            km_effectif = km * coef_aller + km * coef_retour


            data.append([
                
                n.ligne.ord if n.ligne else "",
                n.ligne.code if n.ligne else "",
                n.ligne.origine if n.ligne else "",
                n.ligne.dest if n.ligne else "",
                n.ligne.agence if n.ligne else "",
                n.adatserv.strftime("%d") if n.adatserv else "",
                n.achauffeur.mat_emp if n.achauffeur else "",
                n.achauffeur.nom_emp if n.achauffeur else "",
                n.rchauffeur.mat_emp if n.rchauffeur else "",
                n.rchauffeur.nom_emp if n.rchauffeur else "",
                n.aveh if n.aveh else "",
                n.rveh if n.rveh else "",
                km,
                km_effectif,   # ✅ nouvelle colonne
            ])

        table = Table(data, colWidths=[20, 30, 80, 100, 40, 20, 30, 140, 30, 140, 50, 50, 35, 40])

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 10))

        # === RÉCAPITULATIF PAR SORTIE ===
        total_navettes = len(group_list)
        total_km = (sum(float(n.ligne.klm) for n in group_list if n.ligne and n.ligne.klm))*2

        total_achauff = len(set(n.achauffeur.mat_emp for n in group_list if n.achauffeur))
        total_rchauff = len(set(
            n.rchauffeur.mat_emp
            for n in group_list
            if n.rchauffeur and n.rchauffeur.mat_emp != "30000"
        ))


        total_chf = total_achauff + total_rchauff


        total_aveh = len(set(n.aveh for n in group_list if n.aveh))
        total_rveh = len(set(n.rveh for n in group_list if n.rveh))

        total_veh = total_aveh + total_rveh

        # ✅ Nouvelle colonne : Différence
        diff_amle = total_navettes - total_achauff

        # === Calcul total KM structuré pour ce groupe de sortie ===
        total_km_effectif = 0

        for n in group_list:
            km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0

            coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
            coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0

            km_effectif = km * coef_aller + km * coef_retour
            total_km_effectif += km_effectif


        recap_data = [
            ["Total Navettes", "Total KM", "A.Mle", "R.Mle", "Total Chauffeurs", "A.Véh", "R.Véh", "Total Véhicules", "Lignes Supprimées", "Total KM Effectif"],
            [
                total_navettes,
                round(total_km, 2),
                total_achauff,
                total_rchauff,
                total_chf,              # ✅ ajout colonne chauffeurs
                total_aveh,
                total_rveh,
                total_veh,              # ✅ ajout colonne véhicules
                diff_amle,
                round(total_km_effectif, 2)
            ]
        ]



        recap_table = Table(recap_data, colWidths=[80, 80, 60, 60, 90, 60, 60, 90, 90, 90])

        recap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        # → On cumule dans les totaux globaux
        grand_total_navettes += total_navettes
        grand_total_km += total_km
        grand_total_achauff.update(set(n.achauffeur.mat_emp for n in group_list if n.achauffeur and n.achauffeur.mat_emp != "30000"))
        grand_total_rchauff.update(set(n.rchauffeur.mat_emp for n in group_list if n.rchauffeur and n.rchauffeur.mat_emp != "30000"))
        grand_total_aveh.update(set(n.aveh for n in group_list if n.aveh))
        grand_total_rveh.update(set(n.rveh for n in group_list if n.rveh))
        grand_total_km_effectif += total_km_effectif


        elements.append(recap_table)
        elements.append(Spacer(1, 15))

        # === RÉCAPITULATIF GÉNÉRAL (Sous forme de tableau) ===

        elements.append(Spacer(1, 18))
        elements.append(Paragraph("<b>RÉCAPITULATIF GÉNÉRAL</b>", styles['Heading2']))
        elements.append(Spacer(1, 6))

        # Calcul différence globale A.Mle manquants
        diff_global = grand_total_navettes - len(grand_total_achauff)

        recap_global_data = [
            ["Total Navettes", "Total KM", "A.Mle", "R.Mle", "A.Véh", "R.Véh", "Différence", "Total KM Effectif"],
            [
                grand_total_navettes,
                round(grand_total_km, 2),
                len(grand_total_achauff),
                len(grand_total_rchauff),
                len(grand_total_aveh),
                len(grand_total_rveh),
                diff_global,
                round(grand_total_km_effectif, 2)
            ]
        ]

        recap_global_table = Table(recap_global_data, colWidths=[80, 80, 60, 60, 60, 60, 80, 100])

        recap_global_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.6, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(recap_global_table)
        elements.append(Spacer(1, 20))




    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response

from datetime import datetime
from io import BytesIO
from itertools import groupby

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from .models import Navette


def raportjs_sortie_pdf(request):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from datetime import datetime
    from io import BytesIO

    MAP_SORTIE = {
        1: "Dépôt Ben Arous",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud",
        4: "Convention",
    }

    # --- Queryset ---  
    navettes = Navette.objects.select_related("ligne")

    # --- Filtre dates ---
    start_str = request.GET.get("start", "").strip()
    end_str = request.GET.get("end", "").strip()

    if start_str and end_str:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        navettes = navettes.filter(adatserv__date__range=(start_date, end_date))

    # --- Filtre sortie ---
    sortie_raw = request.GET.get("sortie", "").strip()
    sortie_label = "Toutes sorties"

    if sortie_raw:
        try:
            sortie_int = int(sortie_raw)
            navettes = navettes.filter(ligne__sortie=sortie_int)
            sortie_label = MAP_SORTIE.get(sortie_int, sortie_raw)
        except:
            navettes = navettes.filter(ligne__sortie__icontains=sortie_raw)
            sortie_label = sortie_raw

    # --- Liste des dates ---
    dates = sorted({n.adatserv for n in navettes})

    # --- Récupération lignes distinctes ---
    lignes = (
        navettes
        .values_list(
            "ligne__code",
            "ligne__origine",
            "ligne__dest"
        )
        .distinct()
        .order_by("ligne__code")
    )

    # --- Structure matrix ---
    matrix = {}
    for code, origine, dest in lignes:
        matrix[code] = {
            "code": code or "",
            "origine": origine or "",
            "dest": dest or "",
            "data": {d: set() for d in dates},  # set() pour véhicules distincts
            "total": 0,
        }

    # --- Remplissage matrix ---
    for n in navettes:
        d = n.adatserv
        code = n.ligne.code
        veh = n.aveh

        if veh:
            matrix[code]["data"][d].add(veh)

    # --- Total par ligne ---
    for code in matrix:
        total = 0
        for d in dates:
            total += len(matrix[code]["data"][d])
        matrix[code]["total"] = total

    # --- Totaux par date ---
    total_par_date = {d: 0 for d in dates}
    for code in matrix:
        for d in dates:
            total_par_date[d] += len(matrix[code]["data"][d])

    total_general = sum(total_par_date.values())

    # === PDF ===
    buffer = BytesIO()
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=20, leftMargin=20,
        topMargin=20, bottomMargin=20
    )

    elements = []
    elements.append(Paragraph("<b>Matrice Véhicules A.VEH par Ligne</b>", styles["Title"]))
    elements.append(Paragraph(f"Sortie : <b>{sortie_label}</b>", styles["Normal"]))
    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # === Construction tableau ===
    header = ["Code", "Origine", "Destination"] + [d.strftime("%d") for d in dates] + ["Total Ligne"]
    table_data = [header]

    for code, row in matrix.items():
        line = [
            row["code"],
            row["origine"],
            row["dest"],
        ]
        for d in dates:
            line.append(len(row["data"][d]))   # nombre distinct de A.VEH
        line.append(row["total"])
        table_data.append(line)

    # --- Ligne total général ---
    total_row = ["", "", "TOTAL"]
    for d in dates:
        total_row.append(total_par_date[d])
    total_row.append(total_general)
    table_data.append(total_row)

    # === Table ===
    table = Table(table_data)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (3, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(table)
    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="matrice_vehicules.pdf"'
    response.write(pdf)
    return response


def raportjs1_pdf(request):

    MAP_SORTIE = {
        1: "Gare Routière Sud",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud1",
        4: "Convention",
    }

    navettes = Navette.objects.select_related("ligne", "achauffeur")

    # --- Filtres date ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__date__range=(start_date, end_date))
        except:
            pass

    # --- Tri journalier + sortie ---
    navettes_sorted = navettes.order_by("adatserv", "ligne__sortie", "ligne__ord")

    # --- PDF ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport.pdf"'

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet  

    styles = getSampleStyleSheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    elements = []
    agences_totaux = {}


    # --- Titre ---
    elements.append(Paragraph("<b>Liste des Navettes SNTRI</b>", styles['Title']))

    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
        elements.append(Spacer(1, 10))

    from itertools import groupby

    big_table_data = [
        ["Date", "Depart", "Total Lignes", "T.KM estimer", "chauf.A", "chauf.R",
        "Total Chaufs", "Véh.A", "Véh.R", "Total Véh",
        "Lignes Supprimées", "T.KM Effectif"]
    ]

    # Totaux globaux
    grand_total_navettes = 0
    grand_total_km = 0
    grand_total_achauff = set()
    grand_total_rchauff = set()
    grand_total_aveh = set()
    grand_total_rveh = set()
    grand_total_km_effectif = 0

    # === GROUP BY DATE ===
    for date_serv, group_date in groupby(navettes_sorted, key=lambda n: n.adatserv):

        group_date_list = list(group_date)
        first_row_for_date = True

        # Totaux pour la date
        date_total_nav = 0
        date_total_km = 0
        date_total_ach = set()
        date_total_rch = set()
        date_total_aveh = set()
        date_total_rveh = set()
        date_total_kmeff = 0

        # GROUP BY SORTIE
        for sortie, group_sortie in groupby(group_date_list, key=lambda n: n.ligne.sortie or 0):

            group_list = list(group_sortie)
            sortie_label = MAP_SORTIE.get(sortie, "Non renseignée")

            # Calculs
            total_navettes = len(group_list)
            total_km = sum(float(n.ligne.klm) for n in group_list if n.ligne and n.ligne.klm) * 2
            total_achauff = len(set(n.achauffeur.mat_emp for n in group_list if n.achauffeur))
            total_rchauff = len(set(n.rchauffeur.mat_emp for n in group_list if n.rchauffeur and n.rchauffeur.mat_emp != "30000"))
            total_chf = total_achauff + total_rchauff
            total_aveh = len(set(n.aveh for n in group_list if n.aveh))
            total_rveh = len(set(n.rveh for n in group_list if n.rveh))
            total_veh = total_aveh + total_rveh
            diff_amle = total_navettes - total_achauff

            total_km_effectif = sum(
                (float(n.ligne.klm) if n.ligne and n.ligne.klm else 0) *
                ((1 if n.achauffeur and n.achauffeur.mat_emp != "30000" else 0) +
                (1 if n.rchauffeur and n.rchauffeur.mat_emp != "30000" else 0))
                for n in group_list
            )

            # Ligne tableau
            big_table_data.append([
                date_serv.strftime('%d/%m/%Y') if first_row_for_date else "",
                sortie_label,
                total_navettes, round(total_km, 2),
                total_achauff, total_rchauff, total_chf,
                total_aveh, total_rveh, total_veh,
                diff_amle, round(total_km_effectif, 2)
            ])

            first_row_for_date = False

            # Cumuls date
            date_total_nav += total_navettes
            date_total_km += total_km
            date_total_ach.update(set(n.achauffeur.mat_emp for n in group_list if n.achauffeur))
            date_total_rch.update(set(n.rchauffeur.mat_emp for n in group_list if n.rchauffeur))
            date_total_aveh.update(set(n.aveh for n in group_list if n.aveh))
            date_total_rveh.update(set(n.rveh for n in group_list if n.rveh))
            date_total_kmeff += total_km_effectif

        # === Ligne récap de la DATE ===
        big_table_data.append([
            "", "TOTAL DATE",
            date_total_nav, round(date_total_km, 2),
            len(date_total_ach), len(date_total_rch), len(date_total_ach) + len(date_total_rch),
            len(date_total_aveh), len(date_total_rveh), len(date_total_aveh) + len(date_total_rveh),
            date_total_nav - len(date_total_ach),
            round(date_total_kmeff, 2)
        ])

        # Cumuls globaux
        grand_total_navettes += date_total_nav
        grand_total_km += date_total_km
        grand_total_achauff.update(date_total_ach)
        grand_total_rchauff.update(date_total_rch)
        grand_total_aveh.update(date_total_aveh)
        grand_total_rveh.update(date_total_rveh)
        grand_total_km_effectif += date_total_kmeff

    # === GRAND RÉCAP GLOBAL ===
    big_table_data.append([
        "", "TOTAL GÉNÉRAL",
        grand_total_navettes, round(grand_total_km, 2),
        len(grand_total_achauff), len(grand_total_rchauff),
        len(grand_total_achauff)+len(grand_total_rchauff),
        len(grand_total_aveh), len(grand_total_rveh),
        len(grand_total_aveh)+len(grand_total_rveh),
        grand_total_navettes - len(grand_total_achauff),
        round(grand_total_km_effectif, 2)
    ])

    # Création du tableau final
    table = Table(big_table_data, colWidths=[65, 95, 65, 65, 45, 45, 75, 45, 45, 75, 75, 90])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.6, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)





    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response


from datetime import datetime
from io import BytesIO
from itertools import groupby

from django.http import HttpResponse
from django.db.models.functions import TruncDate

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from .models import Navette


def raportjs_mois_pdf(request):
    """Rapport mensuel des navettes — version optimisée et corrigée."""
    MAP_SORTIE = {
        1: "Gare Routière Sud",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud1",
        4: "Convention",
    }

    # Base queryset (sélection des relations nécessaires)
    navettes_qs = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")

    # --- Lecture et parsing des filtres ---
    start_str = request.GET.get("start", "").strip()
    end_str = request.GET.get("end", "").strip()
    sortie_raw = request.GET.get("sortie", "").strip()

    # Dates : on normalise en date (pas datetime) pour TruncDate/date range
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            navettes_qs = navettes_qs.filter(adatserv__date__range=(start_date, end_date))
        except ValueError:
            # si parse échoue, on ignore le filtre date
            pass

    # Sortie : si numérique on filtre par égalité, sinon on ignore ou on fait icontains
    if sortie_raw:
        try:
            sortie_int = int(sortie_raw)
            navettes_qs = navettes_qs.filter(ligne__sortie=sortie_int)
        except ValueError:
            # si ce n'est pas un entier, on cherche par substring
            navettes_qs = navettes_qs.filter(ligne__sortie__icontains=sortie_raw)

    # --- Annotate pour le groupement par date et tri ---
    navettes_qs = navettes_qs.annotate(date_serv=TruncDate('adatserv'))
    # Order must match the groupby keys: date_serv, ligne__sortie, ligne__ord
    navettes_sorted = navettes_qs.order_by('date_serv', 'ligne__sortie', 'ligne__ord', 'adatserv')

    # --- Préparation du PDF (reportlab) ---
    styles = getSampleStyleSheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20
    )
    elements = []

    elements.append(Paragraph("<b>Liste des Navettes SNTRI</b>", styles['Title']))
    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
        elements.append(Spacer(1, 10))

    # En-têtes du tableau
    big_table_data = [
        ["Date", "Depart", "Total Lignes", "T.KM estimer", "chauf.A", "chauf.R",
         "Total Chaufs", "Véh.A", "Véh.R", "Total Véh", "Lignes Supprimées", "T.KM Effectif"]
    ]

    # Totaux globaux
    grand_total_navettes = 0
    grand_total_km = 0
    grand_total_achauff = set()
    grand_total_rchauff = set()
    grand_total_aveh = set()
    grand_total_rveh = set()
    grand_total_km_effectif = 0
    grand_total_diff = 0

    # === GROUP BY DATE_SERV (TruncDate) ===
    # groupby requires the iterable to be sorted by the same key (we ordered by date_serv)
    for date_serv, group_date in groupby(navettes_sorted, key=lambda n: n.date_serv):
        group_date_list = list(group_date)
        first_row_for_date = True

        # Totaux pour la date
        date_total_nav = 0
        date_total_km = 0
        date_total_ach = set()
        date_total_rch = set()
        date_total_aveh = set()
        date_total_rveh = set()
        date_total_kmeff = 0
        date_total_dif = 0

        # === GROUP BY SORTIE DANS LA DATE ===
        # On groupe par la valeur brute ligne.sortie (peut être int ou str selon ton modèle)
        for sortie_key, group_sortie in groupby(group_date_list, key=lambda n: (n.ligne.sortie if n.ligne else None)):
            group_list = list(group_sortie)

            # Traduction label sortie via MAP_SORTIE si possible
            sortie_label = "Non renseignée"
            if sortie_key is not None:
                try:
                    sortie_int = int(sortie_key)
                    sortie_label = MAP_SORTIE.get(sortie_int, str(sortie_key))
                except Exception:
                    sortie_label = str(sortie_key)

            # Calculs par groupe
            total_navettes = len(group_list)
            total_km = sum(
                (float(n.ligne.klm) if n.ligne and n.ligne.klm else 0)
                for n in group_list
            ) * 2  # tu doublés le km estimé, je conserve la logique
            total_achauff = len(set(n.achauffeur.mat_emp for n in group_list if getattr(n, 'achauffeur', None)))
            total_rchauff = len(set(
                n.rchauffeur.mat_emp for n in group_list
                if getattr(n, 'rchauffeur', None) and getattr(n.rchauffeur, 'mat_emp', None) != "30000"
            ))
            total_chf = total_achauff + total_rchauff
            total_aveh = len(set(n.aveh for n in group_list if n.aveh))
            total_rveh = len(set(n.rveh for n in group_list if n.rveh))
            total_veh = total_aveh + total_rveh
            diff_amle = total_navettes - total_achauff

            total_km_effectif = sum(
                (float(n.ligne.klm) if n.ligne and n.ligne.klm else 0) *
                ((1 if getattr(n, 'achauffeur', None) and getattr(n.achauffeur, 'mat_emp', None) != "30000" else 0) +
                 (1 if getattr(n, 'rchauffeur', None) and getattr(n.rchauffeur, 'mat_emp', None) != "30000" else 0))
                for n in group_list
            )

            # Ajouter la ligne au tableau
            big_table_data.append([
                date_serv.strftime('%d/%m/%Y') if first_row_for_date and date_serv else "",
                sortie_label,
                total_navettes, round(total_km, 2),
                total_achauff, total_rchauff, total_chf,
                total_aveh, total_rveh, total_veh,
                diff_amle, round(total_km_effectif, 2)
            ])

            first_row_for_date = False

            # Cumuls date
            date_total_nav += total_navettes
            date_total_km += total_km
            date_total_ach.update(set(n.achauffeur.mat_emp for n in group_list if getattr(n, 'achauffeur', None)))
            date_total_rch.update(set(n.rchauffeur.mat_emp for n in group_list if getattr(n, 'rchauffeur', None)))
            date_total_aveh.update(set(n.aveh for n in group_list if n.aveh))
            date_total_rveh.update(set(n.rveh for n in group_list if n.rveh))
            date_total_kmeff += total_km_effectif
            date_total_dif += diff_amle

        # Ligne récap de la date
        big_table_data.append([
            "", "TOTAL DATE",
            date_total_nav, round(date_total_km, 2),
            len(date_total_ach), len(date_total_rch), len(date_total_ach) + len(date_total_rch),
            len(date_total_aveh), len(date_total_rveh), len(date_total_aveh) + len(date_total_rveh),
            date_total_nav - len(date_total_ach),
            round(date_total_kmeff, 2)
        ])

        # Cumuls globaux
        grand_total_navettes += date_total_nav
        grand_total_km += date_total_km
        grand_total_achauff.update(date_total_ach)
        grand_total_rchauff.update(date_total_rch)
        grand_total_aveh.update(date_total_aveh)
        grand_total_rveh.update(date_total_rveh)
        grand_total_km_effectif += date_total_kmeff
        grand_total_diff += date_total_dif

    # Grand récapitulatif
    big_table_data.append([
        "", "TOTAL GÉNÉRAL",
        grand_total_navettes, round(grand_total_km, 2),
        len(grand_total_achauff), len(grand_total_rchauff),
        len(grand_total_achauff) + len(grand_total_rchauff),
        len(grand_total_aveh), len(grand_total_rveh),
        len(grand_total_aveh) + len(grand_total_rveh),
        grand_total_diff,
        round(grand_total_km_effectif, 2)
    ])

    # Création du tableau reportlab et stylisation
    table = Table(big_table_data, colWidths=[65, 95, 65, 65, 45, 45, 75, 45, 45, 75, 75, 90])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.6, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)

    # Build PDF into buffer puis renvoyer la réponse HTTP
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport.pdf"'
    response.write(pdf_data)
    return response



def chauffeurs_pdf(request):

    MAP_SORTIE = {
        1: "Dépôt Ben Arous",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud",
        4: "Convention",
    }

    navettes = Navette.objects.select_related("ligne", "achauffeur")

    # --- Filtres date ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__date__range=(start_date, end_date))
        except:
            pass
    achauffeur = request.GET.get("achauffeur")
        
    if achauffeur:
        navettes = navettes.filter(Q(achauffeur__nom_emp__icontains=achauffeur) | Q(achauffeur__mat_emp__icontains=achauffeur))

    

    navettes = navettes.exclude(Q(achauffeur__isnull=True))

    # --- Tri journalier + sortie ---
    navettes_sorted = navettes.order_by("adatserv", "ligne__sortie", "ligne__ord")

    # --- PDF ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport.pdf"'

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet  

    styles = getSampleStyleSheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    elements = []
    agences_totaux = {}

    # --- Titre ---
    elements.append(Paragraph("<b>Liste des Navettes Par Chauffeur</b>", styles['Title']))
    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
        elements.append(Spacer(1, 10))

    from itertools import groupby
    
    # === TITRES COLONNES ===
    data = [[
        'A.Mle', 'A.Chauffeur',
        'Ord', 'Ligne', 'Origine', 'Destination', 'Agence',
        'Date', 'R.Mle', 'A.Véhicule',
        'KM', 'KM Effectif'
    ]]

    # Tri par chauffeur, puis date + ordre
    navettes_sorted = navettes_sorted.order_by(
        "achauffeur__mat_emp", "adatserv", "ligne__ord"
    )

    recap_rows = []
    recap_chauffeurs_data = [] 
    # En-tête du tableau récap
    recap_chauffeurs_data.append([
        "Mle"
        "Chauffeur",
        "Navettes",
        "Jours",
        "Km théorique",
        "Km effectif"
    ])


    # Totaux généraux
    grand_nav = 0
    grand_km = 0
    grand_kmeff = 0


    # Groupement par chauffeur aller
    for (mat, nom), group_navs in groupby(navettes_sorted, key=lambda n: (
        n.achauffeur.mat_emp if n.achauffeur else "",
        n.achauffeur.nom_emp if n.achauffeur else ""
    )):

        group_navs = list(group_navs)

        
        # ✅ Supprimer les navettes sans chauffeur aller → elles ne seront PAS affichées
        group_navs = [n for n in group_navs if n.achauffeur]

        # ✅ Calcul correct du nombre de jours distincts
        jours = len({n.adatserv for n in group_navs if n.adatserv})

         
        # Totaux chauffeur
        ch_nav = 0
        ch_km = 0
        ch_kmeff = 0

        first = True

       

        
        for n in group_navs:
            km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
            coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
            coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
            km_effectif = km * coef_aller + km * coef_retour

            data.append([
                mat if first else "",
                nom if first else "",
                n.ligne.ord if n.ligne else "",
                n.ligne.code if n.ligne else "",
                n.ligne.origine if n.ligne else "",
                n.ligne.dest if n.ligne else "",
                n.ligne.agence if n.ligne else "",
                n.adatserv.strftime("%d/%m/%Y") if n.adatserv else "",
                n.rchauffeur.mat_emp if n.rchauffeur else "",
                n.aveh if n.aveh else "",
                f"{km:.1f}",
                f"{km_effectif:.1f}",
            ])

            first = False

            ch_nav += 1
            ch_km += km * 2
            ch_kmeff += km_effectif

        # LIGNE RÉCAP CHAUFFEUR
        recap_rows.append(len(data))  # On mémorise cette ligne
        data.append([
            "", "",f"TOTAL  (Navettes: {ch_nav} | Jours: {jours})", "", "", "", "", "", "", "",
            
            round(ch_km, 2), round(ch_kmeff, 2)
        ])

        # --- Sauvegarde pour le tableau récap ---
        recap_chauffeurs_data.append([
           mat.upper(),          # mat chauffeur
           nom.upper(),          # Nom chauffeur
            ch_nav,               # Nombre navettes
            jours,                # Nombre jours
            round(ch_km, 2),      # Total km théorique
            round(ch_kmeff, 2)    # Km effectif
        ])



        grand_nav += ch_nav
        grand_km += ch_km
        grand_kmeff += ch_kmeff

    # === RÉCAP GÉNÉRAL ===
    recap_general_row = len(data)
    data.append([
        "", "", "", "",f"TOTAL GÉNÉRAL  (Navettes: {grand_nav})", "", "", "", "",round(grand_km, 2), "",
        
         round(grand_kmeff, 2)
    ])

    # Ajout total général à la liste récap
    recap_chauffeurs_data.append([
        "TOTAL GÉNÉRAL",
        grand_nav,
        "",   # pas de jours total
        round(grand_km, 2),
        round(grand_kmeff, 2)
    ])



    table = Table(data, colWidths=[40, 80, 15, 30, 80, 80, 40, 50, 40, 40, 35, 45])

    # Style spécial : lignes récap + ligne total général
    recap_style = []

    for row in recap_rows:
        recap_style += [
            ('BACKGROUND', (0, row), (-1, row), colors.HexColor("#E6F2FF")),  # bleu clair doux
            ('FONTNAME', (0, row), (-1, row), 'Helvetica-Bold'),
            ('LINEABOVE', (0, row), (-1, row), 1.2, colors.darkblue),
            ('LINEBELOW', (0, row), (-1, row), 1.2, colors.darkblue),
        ]


    # Style TOTAL GENERAL → fond bleu foncé + texte blanc
    recap_style.append(('BACKGROUND', (0, recap_general_row), (-1, recap_general_row), colors.darkblue))
    recap_style.append(('TEXTCOLOR', (0, recap_general_row), (-1, recap_general_row), colors.whitesmoke))
    recap_style.append(('FONTNAME', (0, recap_general_row), (-1, recap_general_row), 'Helvetica-Bold'))

    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ] + recap_style))

    elements.append(table)
    elements.append(Spacer(1, 10))

    # Deuxième tableau : Récapitulatif des chauffeurs
    recap_table = Table(
        recap_chauffeurs_data,
        colWidths=[60, 120, 60, 80, 80]
    )

    recap_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),  # TOTAL GÉNÉRAL gris clair
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>Récapitulatif des Chauffeurs</b>", styles['Heading4']))
    elements.append(Spacer(1, 5))
    elements.append(recap_table)


    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def chauffeurs1_pdf(request):

    from io import BytesIO
    from datetime import datetime
    from itertools import groupby

    from django.http import HttpResponse
    from django.db.models import Q
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    MAP_SORTIE = {1: "Dépôt Ben Arous",2: "Gare Routière Nord",3: "Gare Routière Sud",4: "Convention"}

    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")

    # --- Filtres dates ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__date__range=(start_date, end_date))
        except:
            pass

    # --- Filtre chauffeur ---
    achauffeur = request.GET.get("achauffeur")
    if achauffeur:
        navettes = navettes.filter(Q(achauffeur__nom_emp__icontains=achauffeur) | 
                                   Q(achauffeur__mat_emp__icontains=achauffeur))

    navettes = navettes.exclude(achauffeur__isnull=True).order_by("adatserv", "achauffeur__mat_emp")

    # --- Extraire dates uniques (colonnes) ---
    dates = sorted({n.adatserv for n in navettes})

    # --- Extraire chauffeurs uniques (lignes) ---
    chauffeurs = sorted({
        (n.achauffeur.mat_emp, n.achauffeur.nom_emp) 
        for n in navettes if n.achauffeur
    })

    # --- Construction matrice ---
    # pivot[(mat,nom)][date] = list codes
    pivot = { (mat,nom): {d: [] for d in dates} for (mat,nom) in chauffeurs }
    total_km_chauffeur = { (mat,nom): 0 for (mat,nom) in chauffeurs }
    total_km_date = { d: 0 for d in dates }

    for n in navettes:
        mat = n.achauffeur.mat_emp
        nom = n.achauffeur.nom_emp
        d = n.adatserv
        code = n.ligne.code if n.ligne else ""

        km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
        coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
        coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
        km_effectif = km * coef_aller + km * coef_retour

        pivot[(mat,nom)][d].append(code)
        total_km_chauffeur[(mat,nom)] += km_effectif
        total_km_date[d] += km_effectif

    # --- Préparation tableau PDF ---
    styles = getSampleStyleSheet()
    buffer = BytesIO()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="matrice_chauffeurs.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), leftMargin=20,rightMargin=20,topMargin=20,bottomMargin=20)

    elements = []
    elements.append(Paragraph("<b>État Matriciel des Navettes par Chauffeur</b>", styles['Title']))
    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # En-têtes
    header = ["Chauffeur"] + [d.strftime("%d") for d in dates] + ["Total KM"]
    data = [header]

    # Remplissage lignes
    for (mat, nom) in chauffeurs:
        row = [f"{mat} - {nom}"]
        for d in dates:
            codes = pivot[(mat,nom)][d]
            cell = ", ".join(codes) if codes else ""
            row.append(cell)
        row.append(f"{total_km_chauffeur[(mat,nom)]:.1f}")
        data.append(row)

    # Dernière ligne = total par date
    total_row = ["TOTAL KM / Jour"] + [f"{total_km_date[d]:.1f}" for d in dates] + [f"{sum(total_km_chauffeur.values()):.1f}"]
    data.append(total_row)

    table = Table(data, colWidths=[170] + [20]*len(dates) + [40])

    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))

    elements.append(table)
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response

def chauffeurs2_pdf(request):
    from io import BytesIO
    from datetime import datetime
    from itertools import groupby
    from django.http import HttpResponse
    from django.db.models import Q
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib import colors

    MAP_SORTIE = {
        1: "Dépôt Ben Arous",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud",
        4: "Convention"
    }

    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")

    # --- Filtres dates ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__date__range=(start_date, end_date))
        except:
            pass

    # --- Filtre chauffeur ---
    achauffeur = request.GET.get("achauffeur")
    if achauffeur:
        navettes = navettes.filter(
            Q(achauffeur__nom_emp__icontains=achauffeur)
            | Q(achauffeur__mat_emp__icontains=achauffeur)
        )

    navettes = navettes.exclude(achauffeur__isnull=True).order_by("adatserv", "achauffeur__mat_emp")

    # --- Dates et chauffeurs uniques ---
    dates = sorted({n.adatserv for n in navettes})
    chauffeurs = sorted({
        (n.achauffeur.mat_emp, n.achauffeur.nom_emp)
        for n in navettes if n.achauffeur
    })

    # --- Tables de travail ---
    pivot = { (mat,nom): {d: [] for d in dates} for (mat,nom) in chauffeurs }
    total_km_chauffeur = { (mat,nom): 0 for (mat,nom) in chauffeurs }
    total_km_date = { d: 0 for d in dates }

    for n in navettes:
        mat = n.achauffeur.mat_emp
        nom = n.achauffeur.nom_emp
        d = n.adatserv
        code = n.ligne.code if n.ligne else ""

        km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
        coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
        coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
        km_effectif = km * coef_aller + km * coef_retour

        pivot[(mat,nom)][d].append(code)
        total_km_chauffeur[(mat,nom)] += km_effectif
        total_km_date[d] += km_effectif

    # --- PDF ---
    styles = getSampleStyleSheet()
    buffer = BytesIO()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="matrice_chauffeurs.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    elements = []

    # --- Titre principal ---
    elements.append(Paragraph("<b>État Matriciel des Navettes par Chauffeur</b>", styles['Title']))
    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # --- Groupement par sortie ---
    sorties_trouvees = sorted({n.ligne.sortie for n in navettes if n.ligne})
    chauffeur_sortie_count = {(mat, nom): {} for (mat, nom) in chauffeurs}

    for n in navettes:
        if n.ligne and n.ligne.sortie:
            key = (n.achauffeur.mat_emp, n.achauffeur.nom_emp)
            chauffeur_sortie_count[key][n.ligne.sortie] = chauffeur_sortie_count[key].get(n.ligne.sortie, 0) + 1

    pivot_sortie = {}
    for (mat, nom), sorties in chauffeur_sortie_count.items():
        if sorties:
            meilleure_sortie = max(sorties, key=sorties.get)
            pivot_sortie.setdefault(meilleure_sortie, []).append((mat, nom))

    # --- Style sous-titre ---
    subtitle_style = ParagraphStyle(
        'SousTitreGauche',
        parent=styles['Heading2'],
        alignment=TA_LEFT,
        fontSize=14,
        leading=16,
        spaceAfter=8,
        leftIndent=0
    )

    # --- Tableaux par sortie ---
        # --- Tableaux par sortie ---
    for sortie in sorties_trouvees:
        titre = Paragraph(f"<b>{MAP_SORTIE.get(sortie, f'Sortie {sortie}')}</b>", subtitle_style)
        elements.append(titre)
        elements.append(Spacer(1, 8))

        # --- Extraire agences pour cette sortie ---
        agences = sorted({
            n.ligne.agence
            for n in navettes
            if n.ligne and n.ligne.sortie == sortie and n.ligne.agence
        })

        # --- Parcourir chaque agence ---
        for agence in agences:
            # Sous-sous-titre (nom agence)
            agence_style = ParagraphStyle(
                'SousTitreAgence',
                parent=styles['Heading3'],
                alignment=TA_LEFT,
                fontSize=12,
                leading=14,
                spaceAfter=6,
                leftIndent=15
            )

            elements.append(Paragraph(f"<b>Agence : {agence}</b>", agence_style))
            elements.append(Spacer(1, 4))

            # En-tête tableau
            header = ["Chauffeur"] + [d.strftime("%d") for d in dates] + ["Total KM"]
            data = [header]

            # Chauffeurs appartenant à cette agence
            chauffeurs_agence = [
                (mat, nom)
                for (mat, nom) in pivot_sortie.get(sortie, [])
                if any(
                    n.ligne and n.ligne.agence == agence and n.achauffeur.mat_emp == mat
                    for n in navettes
                )
            ]

            for (mat, nom) in chauffeurs_agence:
                row = [f"{mat} - {nom}"]
                for d in dates:
                    codes = pivot[(mat, nom)][d]
                    cell = ", ".join(codes) if codes else ""
                    row.append(cell)
                row.append(f"{total_km_chauffeur[(mat, nom)]:.1f}")
                data.append(row)

            # Totaux agence
            nb_chauffeurs_agence = len(chauffeurs_agence)
            total_agence = sum(total_km_chauffeur[(mat, nom)] for (mat, nom) in chauffeurs_agence)
            data.append(["Nbre Chauffeurs : " + str(nb_chauffeurs_agence)] + [""] * len(dates) + [""])
            data.append(["TOTAL KM / Agence"] + [""] * len(dates) + [f"{total_agence:.1f}"])

            # Création du tableau
            table = Table(data, colWidths=[170] + [20]*len(dates) + [40])
            table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.4, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (1,1), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 10))

        # Saut de page après chaque sortie
        elements.append(PageBreak())


    # === Synthèse Générale (dernière page) ===
    total_global_chauffeurs = len(chauffeurs)
    total_global_km = sum(total_km_chauffeur.values())

    elements.append(PageBreak())
    elements.append(Paragraph("<b>Synthèse Générale</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # --- Totaux par sortie ---
    elements.append(Paragraph("<b>Totaux par Sortie</b>", styles['Heading2']))
    sortie_totaux = [["Sortie", "Nbre Chauffeurs", "Total KM"]]

    for sortie in sorties_trouvees:
        chauffeurs_sortie = pivot_sortie.get(sortie, [])
        nb_chauffeurs_sortie = len(chauffeurs_sortie)
        total_sortie = sum(total_km_chauffeur[(mat, nom)] for (mat, nom) in chauffeurs_sortie)
        sortie_totaux.append([
            MAP_SORTIE.get(sortie, f"Sortie {sortie}"),
            nb_chauffeurs_sortie,
            f"{total_sortie:.1f}"
        ])

    table_sorties = Table(sortie_totaux, colWidths=[200, 100, 100])
    table_sorties.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
    ]))
    elements.append(table_sorties)
    elements.append(Spacer(1, 16))

    # --- Totaux par agence ---
    elements.append(Paragraph("<b>Totaux par Agence</b>", styles['Heading2']))
    agence_totaux = [["Agence", "Nbre Chauffeurs", "Total KM"]]

    agences_trouvees = sorted({
        n.ligne.agence for n in navettes if n.ligne and n.ligne.agence
    })

    for agence in agences_trouvees:
        chauffeurs_agence = set()
        total_agence = 0
        for n in navettes:
            if n.ligne and n.ligne.agence == agence and n.achauffeur:
                chauffeurs_agence.add(n.achauffeur.mat_emp)

                km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
                coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
                coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
                km_effectif = km * coef_aller + km * coef_retour
                total_agence += km_effectif

        agence_totaux.append([
            agence,
            len(chauffeurs_agence),
            f"{total_agence:.1f}"
        ])

    table_agences = Table(agence_totaux, colWidths=[200, 100, 100])
    table_agences.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
    ]))
    elements.append(table_agences)
    elements.append(Spacer(1, 16))

    # --- Totaux globaux ---
    elements.append(Paragraph("<b>Totaux Généraux</b>", styles['Heading2']))
    synthese = [
        ["Total Chauffeurs (tous)", total_global_chauffeurs],
        ["Total KM Global", f"{total_global_km:.1f}"]
    ]

    table_synth = Table(synthese, colWidths=[200, 100])
    table_synth.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(table_synth)


    # --- Génération PDF ---
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response

def chauffeurs_sortie_pdf(request):
    from io import BytesIO
    from datetime import datetime
    from itertools import groupby
    from django.http import HttpResponse
    from django.db.models import Q
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib import colors

    MAP_SORTIE = {
        1: "Dépôt Ben Arous",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud",
        4: "Convention"
    }

    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")

    # --- Filtres dates ---
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__date__range=(start_date, end_date))
        except:
            pass

    # --- Filtre chauffeur ---
    achauffeur = request.GET.get("achauffeur")
    if achauffeur:
        navettes = navettes.filter(
            Q(achauffeur__nom_emp__icontains=achauffeur)
            | Q(achauffeur__mat_emp__icontains=achauffeur)
        )

    navettes = navettes.exclude(achauffeur__isnull=True).order_by("adatserv", "achauffeur__mat_emp")

    # --- Dates et chauffeurs uniques ---
    dates = sorted({n.adatserv for n in navettes})
    chauffeurs = sorted({
        (n.achauffeur.mat_emp, n.achauffeur.nom_emp)
        for n in navettes if n.achauffeur
    })

    # --- Tables de travail ---
    pivot = { (mat,nom): {d: [] for d in dates} for (mat,nom) in chauffeurs }
    total_km_chauffeur = { (mat,nom): 0 for (mat,nom) in chauffeurs }
    total_km_date = { d: 0 for d in dates }

    for n in navettes:
        mat = n.achauffeur.mat_emp
        nom = n.achauffeur.nom_emp
        d = n.adatserv
        code = n.ligne.code if n.ligne else ""

        km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
        coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
        coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
        km_effectif = km * coef_aller + km * coef_retour

        pivot[(mat,nom)][d].append(code)
        total_km_chauffeur[(mat,nom)] += km_effectif
        total_km_date[d] += km_effectif

    # --- PDF ---
    styles = getSampleStyleSheet()
    buffer = BytesIO()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="matrice_chauffeurs.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    elements = []

    # --- Titre principal ---
    elements.append(Paragraph("<b>État Matriciel des Navettes par Chauffeur</b>", styles['Title']))
    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # --- Groupement par sortie ---
    sorties_trouvees = sorted({n.ligne.sortie for n in navettes if n.ligne})
    chauffeur_sortie_count = {(mat, nom): {} for (mat, nom) in chauffeurs}

    for n in navettes:
        if n.ligne and n.ligne.sortie:
            key = (n.achauffeur.mat_emp, n.achauffeur.nom_emp)
            chauffeur_sortie_count[key][n.ligne.sortie] = chauffeur_sortie_count[key].get(n.ligne.sortie, 0) + 1

    pivot_sortie = {}
    for (mat, nom), sorties in chauffeur_sortie_count.items():
        if sorties:
            meilleure_sortie = max(sorties, key=sorties.get)
            pivot_sortie.setdefault(meilleure_sortie, []).append((mat, nom))

    # --- Style sous-titre ---
    subtitle_style = ParagraphStyle(
        'SousTitreGauche',
        parent=styles['Heading2'],
        alignment=TA_LEFT,
        fontSize=14,
        leading=16,
        spaceAfter=8,
        leftIndent=0
    )

    # --- Tableaux par sortie ---
    for sortie in sorties_trouvees:

        # Titre de la sortie
        titre = Paragraph(f"<b>{MAP_SORTIE.get(sortie, f'Sortie {sortie}')}</b>", subtitle_style)
        elements.append(titre)
        elements.append(Spacer(1, 8))

        # En-tête du tableau
        header = ["Chauffeur"] + [d.strftime("%d") for d in dates] + ["T.Nav", "Total KM"]
        data = [header]

        # Tous les chauffeurs affectés à cette sortie
        chauffeurs_sortie = pivot_sortie.get(sortie, [])

        # Total navettes par jour
        total_par_jour = {d: 0 for d in dates}

        for (mat, nom) in chauffeurs_sortie:
            for d in dates:
                total_par_jour[d] += len(pivot[(mat, nom)][d])


        for (mat, nom) in chauffeurs_sortie:
            row = [f"{mat} - {nom}"]

            total_navettes = 0

            for d in dates:
                codes = pivot[(mat, nom)][d]
                nb = len(codes)                  # nombre de navettes du jour
                total_navettes += nb             # cumul pour le total
                cell = ", ".join(codes) if codes else ""
                row.append(cell)

            # Total Navettes
            row.append(str(total_navettes))

            # Total KM
            row.append(f"{total_km_chauffeur[(mat, nom)]:.1f}")

            data.append(row)


        # --- Totaux de sortie ---
        nb_ch = len(chauffeurs_sortie)
        total_km_sortie = sum(total_km_chauffeur[(mat, nom)] for (mat, nom) in chauffeurs_sortie)

        # total navettes sortie
        total_navettes_sortie = sum(
            len(pivot[(mat, nom)][d])
            for (mat, nom) in chauffeurs_sortie
            for d in dates
        )

        # Ligne TOTAL PAR JOUR
        row_total_jour = ["TOTAL / Jour"]
        for d in dates:
            row_total_jour.append(str(total_par_jour[d]))

        # les 2 colonnes finales (Total Navettes, Total KM)
        row_total_jour.append("")   
        row_total_jour.append("")

        data.append(row_total_jour)

        # Ligne totaux
        data.append(["Nbre Chauffeurs : " + str(nb_ch)] + [""] * len(dates) + ["", ""])
        data.append(["TOTAL Navettes / Sortie"] + [""] * len(dates) + [str(total_navettes_sortie), ""])
        data.append(["TOTAL KM / Sortie"] + [""] * len(dates) + ["", f"{total_km_sortie:.1f}"])


        # Tableau
        table = Table(data, colWidths=[170] + [40]*len(dates) + [40])
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.4, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (1,1), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))

        elements.append(table)
        elements.append(PageBreak())


    # === Synthèse Générale (dernière page) ===
    total_global_chauffeurs = len(chauffeurs)
    total_global_km = sum(total_km_chauffeur.values())

    elements.append(PageBreak())
    elements.append(Paragraph("<b>Synthèse Générale</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # --- Totaux par sortie ---
    elements.append(Paragraph("<b>Totaux par Sortie</b>", styles['Heading2']))
    sortie_totaux = [["Sortie", "Nbre Chauffeurs", "Total KM"]]

    for sortie in sorties_trouvees:
        chauffeurs_sortie = pivot_sortie.get(sortie, [])
        nb_chauffeurs_sortie = len(chauffeurs_sortie)
        total_sortie = sum(total_km_chauffeur[(mat, nom)] for (mat, nom) in chauffeurs_sortie)
        sortie_totaux.append([
            MAP_SORTIE.get(sortie, f"Sortie {sortie}"),
            nb_chauffeurs_sortie,
            f"{total_sortie:.1f}"
        ])

    table_sorties = Table(sortie_totaux, colWidths=[200, 100, 100])
    table_sorties.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
    ]))
    elements.append(table_sorties)
    elements.append(Spacer(1, 16))

    # --- Totaux par agence ---
    elements.append(Paragraph("<b>Totaux par Agence</b>", styles['Heading2']))
    agence_totaux = [["Agence", "Nbre Chauffeurs", "Total KM"]]

    agences_trouvees = sorted({
        n.ligne.agence for n in navettes if n.ligne and n.ligne.agence
    })

    for agence in agences_trouvees:
        chauffeurs_agence = set()
        total_agence = 0
        for n in navettes:
            if n.ligne and n.ligne.agence == agence and n.achauffeur:
                chauffeurs_agence.add(n.achauffeur.mat_emp)

                km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
                coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
                coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
                km_effectif = km * coef_aller + km * coef_retour
                total_agence += km_effectif

        agence_totaux.append([
            agence,
            len(chauffeurs_agence),
            f"{total_agence:.1f}"
        ])

    table_agences = Table(agence_totaux, colWidths=[200, 100, 100])
    table_agences.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
    ]))
    elements.append(table_agences)
    elements.append(Spacer(1, 16))

    # --- Totaux globaux ---
    elements.append(Paragraph("<b>Totaux Généraux</b>", styles['Heading2']))
    synthese = [
        ["Total Chauffeurs (tous)", total_global_chauffeurs],
        ["Total KM Global", f"{total_global_km:.1f}"]
    ]

    table_synth = Table(synthese, colWidths=[200, 100])
    table_synth.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(table_synth)

    # --- Génération PDF ---
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response

# ------------------------------
# 🧾 Liste des lignes
# ------------------------------


def ligne_list(request):
    lignes = Ligne.objects.all()

    # --- Filtres déjà existants ---
    code = request.GET.get("code") or request.POST.get("code")
    agence = request.GET.get("agence") or request.POST.get("agence")
    actif = request.GET.get("actif") or request.POST.get("actif")

    # --- Nouveau filtre sortie ---
    sortie = request.GET.get("sortie") or request.POST.get("sortie")

    # --- Filtre par agence ---
    if agence:
        lignes = lignes.filter(agence=agence)

    # --- Filtre par actif ---
    if actif in ["1", "true", "True"]:
        lignes = lignes.filter(actif=1)
    elif actif in ["0", "false", "False"]:
        lignes = lignes.filter(actif=0)

    # --- Filtre par code ---
    if code:
        lignes = lignes.filter(code__icontains=code)

    # --- Filtre par sortie ---
    if sortie:
        lignes = lignes.filter(sortie=sortie)

    # --- Tri : groupe par sortie puis ord ---
    lignes = lignes.order_by("sortie", "ord")

    # --- Pagination ---
    paginator = Paginator(lignes, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "MAP_SORTIE": MAP_SORTIE,
        "sortie": sortie or "",
        "code": code or "",
        "agence": agence or "",
        "actif": actif or "",
        "actif_true": actif in ["1", "true", "True"],
        "actif_false": actif in ["0", "false", "False"],
        "page_obj": page_obj,
        "lignes": page_obj.object_list,
    }

    return render(request, "blog/ligne_list.html", context)


# ------------------------------
# 🖨️ Export PDF des lignes
# ------------------------------

from itertools import groupby
from operator import attrgetter
import tempfile, os
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from weasyprint import HTML, CSS


MAP_SORTIE = {
    1: "Dépôt Ben Arous",
    2: "Gare Routière Nord",
    3: "Gare Routière Sud",
    4: "Convention",
}

def ligne_pdf(request):
    lignes = Ligne.objects.all()

    # --- Filtres ---
    code = request.GET.get("code")
    agence = request.GET.get("agence")
    actif = request.GET.get("actif")

    if agence:
        lignes = lignes.filter(agence=agence)

    if actif in ["1", "true", "True"]:
        lignes = lignes.filter(actif=1)
    elif actif in ["0", "false", "False"]:
        lignes = lignes.filter(actif=0)

    if code:
        lignes = lignes.filter(code__icontains=code)

    # --- Tri avant groupement ---
    lignes = lignes.order_by("sortie", "ord")

    # --- Groupement ---
    groupes = {}
    for sortie, items in groupby(lignes, key=attrgetter("sortie")):
        groupes[sortie] = list(items)

    # --- Rendu HTML ---
    html_string = render_to_string("blog/ligne_pdf.html", {
        "groupes": groupes,
        "map_sortie": MAP_SORTIE,
    })

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=\"lignes.pdf\"'

    tmp_path = os.path.join(tempfile.gettempdir(), "lignes_export.pdf")
    HTML(string=html_string).write_pdf(target=tmp_path)

    with open(tmp_path, 'rb') as f:
        response.write(f.read())

    os.remove(tmp_path)
    return response

@login_required
def search_equipement(request):
    term = request.GET.get('term', '')
    
    equipements = Equipement.objects.filter(
        cod_equ__icontains=term
    )[:20]

    results = [
        {"id": e.pk, "text": f"{e.cod_equ}"}
        for e in equipements
    ]

    return JsonResponse({"results": results})

from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Equipement

def equipement_list(request):
    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()
    start = request.GET.get("start", "").strip()
    end = request.GET.get("end", "").strip()


    equipements = Equipement.objects.all()

    # --- Filtres ---
    
    if cod_fam_equ:
        equipements = equipements.filter(cod_fam_equ=cod_fam_equ)

    if mod_equ:
        equipements = equipements.filter(mod_equ__icontains=mod_equ)

    if cod_sta:
        cod_sta_list = [s.strip() for s in cod_sta.split(",") if s.strip()]
        equipements = equipements.filter(cod_sta__in=cod_sta_list)

    # --- Tri final ---
    equipements = equipements.order_by("cod_equ")

    # --- Calcul de l’âge ---
    today = date.today()
    for eq in equipements:
        if eq.dat_ins_equ:
            diff = relativedelta(today, eq.dat_ins_equ)
            eq.age = f"{diff.years} ans {diff.months} mois {diff.days} jours"
        else:
            eq.age = "-"

    # --- Pagination ---
    paginator = Paginator(equipements, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "cod_fam_equ": cod_fam_equ,
        "mod_equ": mod_equ,
        "cod_sta": cod_sta,
        "total_count": equipements.count(),
    }

    return render(request, "blog/equipement_list.html", context)

from django.http import HttpResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from .models import Equipement

def equipement_pdf(request):
    equipements = Equipement.objects.all().order_by('cod_equ')

    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    cod_equ = request.GET.get("cod_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    dat_aqu_equ = request.GET.get("dat_aqu_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()

    # --- Filtres ---
    if cod_fam_equ:
        equipements = equipements.filter(cod_fam_equ=cod_fam_equ)

    if cod_equ:
        equipements = equipements.filter(cod_equ__icontains=cod_equ)

    if mod_equ:
        equipements = equipements.filter(mod_equ__icontains=mod_equ)

    if dat_aqu_equ:
        equipements = equipements.filter(dat_aqu_equ=dat_aqu_equ)

    if cod_sta:
        cod_sta_list = [s.strip() for s in cod_sta.split(",") if s.strip()]
        equipements = equipements.filter(cod_sta__in=cod_sta_list)

    # --- Génération du PDF ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename=\"equipements.pdf\"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    centered_title = ParagraphStyle(
        'CenteredTitle',
        parent=styles['Heading1'],
        alignment=1,  # Centré
        spaceAfter=12
    )

    # --- Titre centré ---
    title = Paragraph("Liste des vehicules de Parc SNTRI", centered_title)
    elements.append(title)

    # --- Date du jour ---
    today_str = datetime.today().strftime("%d/%m/%Y")
    date_para = Paragraph(f"Date : {today_str}", styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 10))


    
    # --- Filtres affichés ---
    filter_details = []
    if cod_fam_equ:
        filter_details.append(f"Famille: {cod_fam_equ}")
    if cod_equ:
        filter_details.append(f"Code: {cod_equ}")
    if mod_equ:
        filter_details.append(f"Modèle: {mod_equ}")
    if dat_aqu_equ:
        filter_details.append(f"Date acquisition: {dat_aqu_equ}")
    if cod_sta:
        filter_details.append(f"Statut: {cod_sta}")

    

    elements.append(Paragraph("<br/>", styles['Normal']))

    # --- Tableau PDF ---
    data = [[
        'N° Parc', 'Désignation', 'Modèle', 'N° Série',
        'N° de Police', 'Date acquisition', 'Date insription', 'Âge (ans-mois-jour)'
    ]]
    # Calcul âge
    today = date.today()
    for eq in equipements:
        if eq.dat_ins_equ:
            diff = relativedelta(today, eq.dat_ins_equ)
            age = f"{diff.years} ans {diff.months} mois {diff.days} jours"
        else:
            age = "-"



        data.append([
            eq.cod_equ or "",
            eq.des_equ or "",
            eq.mod_equ or "",
            eq.num_ser_equ or "",
            eq.imm_equ or "",
            eq.dat_aqu_equ.strftime("%d/%m/%Y") if eq.dat_aqu_equ else "",
            eq.dat_ins_equ.strftime("%d/%m/%Y") if eq.dat_ins_equ else "",
            str(age),
        ])

    if len(data) == 1:
        elements.append(Paragraph("Aucun enregistrement trouvé.", styles['Normal']))
    else:
        table = Table(data, colWidths=[30, 70, 50, 90, 50, 65, 60, 90])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table)

        # --- Total affiché ---
        total = len(equipements)
        elements.append(Paragraph(f"<br/><b>Total : {total} équipements</b>", styles['Normal']))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response

def equipement1_pdf(request):
    equipements = Equipement.objects.all().order_by('cod_equ')

    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    cod_equ = request.GET.get("cod_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    dat_aqu_equ = request.GET.get("dat_aqu_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()

    # --- Filtres ---
    if cod_fam_equ:
        equipements = equipements.filter(cod_fam_equ=cod_fam_equ)

    if cod_equ:
        equipements = equipements.filter(cod_equ__icontains=cod_equ)

    if mod_equ:
        equipements = equipements.filter(mod_equ__icontains=mod_equ)

    if dat_aqu_equ:
        equipements = equipements.filter(dat_aqu_equ=dat_aqu_equ)

    if cod_sta:
        cod_sta_list = [s.strip() for s in cod_sta.split(",") if s.strip()]
        equipements = equipements.filter(cod_sta__in=cod_sta_list)

    # --- Génération du PDF ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename=\"equipements.pdf\"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    centered_title = ParagraphStyle(
        'CenteredTitle',
        parent=styles['Heading1'],
        alignment=1,  # Centré
        spaceAfter=12
    )

    # --- Titre centré ---
    title = Paragraph("Liste des vehicules de Parc SNTRI", centered_title)
    elements.append(title)

    # --- Date du jour ---
    today_str = datetime.today().strftime("%d/%m/%Y")
    date_para = Paragraph(f"Date : {today_str}", styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 10))


    
    # --- Filtres affichés ---
    filter_details = []
    if cod_fam_equ:
        filter_details.append(f"Famille: {cod_fam_equ}")
    if cod_equ:
        filter_details.append(f"Code: {cod_equ}")
    if mod_equ:
        filter_details.append(f"Modèle: {mod_equ}")
    if dat_aqu_equ:
        filter_details.append(f"Date acquisition: {dat_aqu_equ}")
    if cod_sta:
        filter_details.append(f"Statut: {cod_sta}")

    

    elements.append(Paragraph("<br/>", styles['Normal']))

    # --- Tableau groupé par modèle ---
    data = []
    current_model = None
    model_count = 0
    total_general = 0

    # En-tête du tableau
    header = [
        'N° Parc', 'Modèle', 'N° Série',
        'N° de Police', 'Date acquisition', 'Date insription', 'Âge (ans-mois-jour)'
    ]

    # --- Tableau groupé par modèle ---
    from statistics import mean

    equipements = equipements.order_by('des_equ', 'cod_equ')

    today = date.today()
    current_model = None
    model_rows = []
    model_ages = []
    all_ages = []  # <<< liste des âges pour la moyenne générale
    total_general = 0

    for eq in equipements:

        
        # Si changement de modèle → imprimer le tableau précédent
        if current_model and eq.des_equ != current_model:

            # Calcul âge moyen du modèle
            if model_ages:
                avg_days = mean(model_ages)
                avg_years = avg_days / 365
                avg_age_str = f"{avg_years:.1f} ans (moyenne)"
            else:
                avg_age_str = "-"

            # Titre du modèle
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"<b>Désignation : {current_model}</b>", styles['Heading3']))
            elements.append(Spacer(1, 5))

            # Tableau du modèle
            table = Table(model_rows, colWidths=[30, 70, 70, 90, 50, 70, 70, 90])
            table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
            ]))
            elements.append(table)

            # Résumé modèle
            elements.append(Paragraph(f"<b>Total véhicules : {len(model_rows)-1}</b>", styles['Normal']))
            elements.append(Paragraph(f"<b>Âge moyen : {avg_age_str}</b>", styles['Normal']))
            elements.append(Spacer(1, 12))

            # Reset pour le modèle suivant
            model_rows = []
            model_ages = []



        # Nouveau modèle → créer l’en-tête
        if eq.des_equ != current_model:
            current_model = eq.des_equ
            model_rows.append([
                'N° Parc', 'Modèle', 'marque', 'N° Série',
                'N° Police', 'Date acquisition', 'Date insription', 'Âge'
            ])

        # --- Calcul âge (Ici ! PAS avant) ---
        if eq.dat_ins_equ:
            diff = relativedelta(today, eq.dat_ins_equ)
            age_days = (today - eq.dat_ins_equ).days

            model_ages.append(age_days)  # Pour l'âge moyen du modèle
            all_ages.append(age_days)    # Pour l'âge moyen général  <<< ICI CORRECT

            age = f"{diff.years}a {diff.months}m {diff.days}j"
        else:
            age = "-"

        model_rows.append([
            eq.cod_equ or "",
            eq.mod_equ or "",
            eq.mrq_equ or "",
            eq.num_ser_equ or "",
            eq.imm_equ or "",
            eq.dat_aqu_equ.strftime("%d/%m/%Y") if eq.dat_aqu_equ else "",
            eq.dat_ins_equ.strftime("%d/%m/%Y") if eq.dat_ins_equ else "",
            age
        ])

        total_general += 1


    # --- Dernier modèle à afficher ---
    if current_model:
        if model_ages:
            avg_days = mean(model_ages)
            avg_years = avg_days / 365
            avg_age_str = f"{avg_years:.1f} ans (moyenne)"
        else:
            avg_age_str = "-"

        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>Désignation : {current_model}</b>", styles['Heading3']))
        elements.append(Spacer(1, 5))

        table = Table(model_rows, colWidths=[30, 70, 70, 90, 50, 70, 70, 90])
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        elements.append(table)

        elements.append(Paragraph(f"<b>Total véhicules : {len(model_rows)-1}</b>", styles['Normal']))
        elements.append(Paragraph(f"<b>Âge moyen : {avg_age_str}</b>", styles['Normal']))
        elements.append(Spacer(1, 12))
    
    # --- Âge moyen général ---
    if all_ages:
        avg_days_general = mean(all_ages)
        avg_years_general = avg_days_general / 365
        avg_age_general_str = f"{avg_years_general:.1f} ans"
    else:
        avg_age_general_str = "-"
    # --- Récap général ---
    elements.append(Paragraph(f"<b>Total général véhicules : {total_general}</b>", styles['Heading3']))
    elements.append(Paragraph(f"<b>Âge moyen général : {avg_age_general_str}</b>", styles['Heading3']))
    elements.append(Spacer(1, 10))


    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response


from statistics import mean



# views_equipements.py  (ou coller dans ton fichier views.py)

from io import BytesIO
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from statistics import mean
from itertools import groupby

from django.http import HttpResponse
from django.db.models import Q

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

# Models (adapter les import si tu utilises un module différent)
from .models import Equipement, Navette


# ---------------------------
# Utilitaires
# ---------------------------
def safe_date(d):
    """Formatte une date en DD/MM/YY même si l'année < 1900 (compatible Windows)."""
    if not d:
        return ""
    return f"{d.day:02d}/{d.month:02d}/{d.year % 100:02d}"

def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def parse_date_iso(s):
    """Renvoie datetime.date ou None (attend 'YYYY-MM-DD')."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def apply_navette_period_filter(qs, start_date, end_date):
    """Filtre queryset Navette sur la période inclusive start..end (dates type date)."""
    if not start_date or not end_date:
        return qs
    # on veut inclure tout le dernier jour -> utiliser < end + 1 day
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return qs.filter(adatserv__gte=start_dt, adatserv__lt=end_dt)


# ---------------------------
# Rendu bloc modèle (séparé)
# ---------------------------
def render_model_block_general(current_model, model_rows, model_ages, navettes_by_veh, styles):
    """
    Crée un bloc PDF pour un modèle d'équipement, avec les véhicules et leurs navettes
    fusionnés dans un seul tableau.
    
    navettes_by_veh : dict cod_equ -> liste de navettes filtrées
    """
    from statistics import mean
    block = []

    # --- Calculs de km, navettes et véhicules ---
    km_model_total = 0.0
    nb_navettes_model = 0
    total_vehicules_model = len(model_rows) - 1  # enlever header

    # Âge moyen
    if model_ages:
        avg_days = mean(model_ages)
        avg_years = avg_days / 365
        avg_age_str = f"{avg_years:.1f} ans"
    else:
        avg_age_str = "-"

    # --- Préparer les données fusionnées ---
    fused_data = [["N° Parc", "Modèle", "Marque", "N° Série", "N° Police",
                   "Date Acqu.", "Date Inscrip.", "Âge", "KM Effectif", "Nbre. Navettes",
                   "Ord", "Code", "Origine", "Destination", "Jour",
                   "A.Chauf", "Nom", "R.Chauf", "Nom",
                   "A.Véh", "R.Véh", "KM Navette", "KM Effectif Navette"]]

    for row in model_rows[1:]:
        cod_equ = row[0]
        km_veh = safe_float(row[8])
        nb_nav = safe_int(row[9])
        km_model_total += km_veh
        nb_navettes_model += nb_nav

        # Ligne véhicule
        fused_data.append(row + [""] * 13)

        # Ajouter les navettes du véhicule
        for n in navettes_by_veh.get(cod_equ, []):
            km = safe_float(n.ligne.klm if n.ligne and n.ligne.klm else 0.0)
            coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
            coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
            km_effectif = km * coef_aller + km * coef_retour

            fused_data.append([""] * 10 + [
                getattr(n.ligne, "ord", "") or "",
                getattr(n.ligne, "code", "") or "",
                getattr(n.ligne, "origine", "") or "",
                getattr(n.ligne, "dest", "") or "",
                safe_date(n.adatserv) if n.adatserv else "",
                n.achauffeur.mat_emp if n.achauffeur else "",
                n.achauffeur.nom_emp if n.achauffeur else "",
                n.rchauffeur.mat_emp if n.rchauffeur else "",
                n.rchauffeur.nom_emp if n.rchauffeur else "",
                getattr(n, "aveh", ""),
                getattr(n, "rveh", ""),
                f"{km:.1f}",
                f"{km_effectif:.1f}"
            ])

    # --- Table fusionnée ---
    block.append(Spacer(1, 10))
    block.append(Paragraph(f"<b>Désignation : {current_model}</b>", styles['Heading3']))
    block.append(Spacer(1, 5))

    table = Table(fused_data, colWidths=[30, 40, 70, 100, 50, 50, 50, 50, 50, 40,
                                         20, 30, 60, 60, 30, 40, 70, 40, 70, 25, 25, 30, 50])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
    ]))

    block.append(table)
    block.append(Spacer(1, 6))

    # Retourne le bloc et le nb de véhicules ayant des navettes
    nb_aveh_disp = sum(1 for row in model_rows[1:] if safe_int(row[9]) > 0)
    return block, nb_aveh_disp


# ---------------------------
# Vue principale : equipement2_pdf
# ---------------------------
def equipement2_pdf(request):
    """
    Génère un PDF listant les véhicules par modèle (grand tableau de véhicules)
    puis, pour chaque véhicule (immédiatement après le tableau du modèle), 
    un sous-tableau listant ses navettes (si présentes).

    Option A : grand tableau véhicules, puis pour chaque véhicule son tableau navettes.
    """
    from io import BytesIO
    from datetime import date, datetime
    from statistics import mean
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from dateutil.relativedelta import relativedelta
    from itertools import groupby

    # --- Récupération des filtres GET ---
    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    cod_equ = request.GET.get("cod_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    dat_aqu_equ = request.GET.get("dat_aqu_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()
    start = request.GET.get("start", "").strip()
    end = request.GET.get("end", "").strip()

    # Parse dates (utilise ta fonction parse_date_iso si tu l'as)
    try:
        start_date = parse_date_iso(start) if start else None
    except Exception:
        start_date = None
    try:
        end_date = parse_date_iso(end) if end else None
    except Exception:
        end_date = None

    # --- Queryset Equipement avec filtres ---
    equipements_qs = Equipement.objects.all()

    if cod_fam_equ:
        equipements_qs = equipements_qs.filter(cod_fam_equ=cod_fam_equ)
    if cod_equ:
        equipements_qs = equipements_qs.filter(cod_equ__icontains=cod_equ)
    if mod_equ:
        equipements_qs = equipements_qs.filter(mod_equ__icontains=mod_equ)
    if dat_aqu_equ:
        try:
            dat_aqu_dt = datetime.strptime(dat_aqu_equ, "%Y-%m-%d").date()
            equipements_qs = equipements_qs.filter(dat_aqu_equ=dat_aqu_dt)
        except Exception:
            equipements_qs = equipements_qs.filter(dat_aqu_equ__icontains=dat_aqu_equ)
    if cod_sta:
        cod_sta_list = [s.strip() for s in cod_sta.split(",") if s.strip()]
        if cod_sta_list:
            equipements_qs = equipements_qs.filter(cod_sta__in=cod_sta_list)

    equipements_qs = equipements_qs.order_by('des_equ', 'cod_equ')

    # --- Préparation du PDF ---
    buffer = BytesIO()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="equipements.pdf"'

    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    centered_title = ParagraphStyle('CenteredTitle', parent=styles['Heading1'], alignment=TA_CENTER, spaceAfter=8)
    normal_left = ParagraphStyle('NormalLeft', parent=styles['Normal'], alignment=TA_LEFT)

    elements = []
    title = Paragraph("Liste des véhicules du Parc SNTRI", centered_title)
    elements.append(title)
    elements.append(Paragraph(f"Date : {date.today().strftime('%d/%m/%Y')}", styles['Normal']))
    if start_date and end_date:
        elements.append(Paragraph(f"Période : {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}", normal_left))
    elements.append(Spacer(1, 8))

    # Totaux généraux
    total_vehicules = 0
    total_general_km = 0.0
    total_general_navettes = 0
    all_ages = []

    today = date.today()

    ################################################################################
    #  GROUPEMENT PAR DES_EQU
    ################################################################################

    equipements = list(equipements_qs)

    # ======================================
    #   Fonction pour calcul de l'âge
    # ======================================
    from datetime import date

    def calcul_age(date_acquisition):
        """Retourne l'âge en années (float, 1 décimale) à partir d'une date."""
        if not date_acquisition:
            return "-"
        try:
            delta = date.today() - date_acquisition
            return f"{delta.days / 365:.1f} ans"
        except Exception:
            return "-"

    ###############################################################################
    # 1) Récupération des navettes pendant la période selectionnée
    ###############################################################################

    navettes_qs = Navette.objects.filter(
        adatserv__date__gte=start_date,
        adatserv__date__lte=end_date
    ).select_related("ligne", "achauffeur", "rchauffeur")

    ###############################################################################
    # 2) Préparation des dictionnaires pour chaque véhicule
    ###############################################################################

    km_by_equ = {}          # KM estimés par véhicule
    km_eff_by_equ = {}      # KM effectifs par véhicule
    navettes_by_equ = {}    # Toutes navettes du véhicule

    for n in navettes_qs:

        # Le code du véhicule utilisé
        code = (n.aveh or "").strip()

        if not code:
            continue  # navette sans véhicule → ignorer

        # --- Initialisation des dictionnaires si 1ère fois ---
        if code not in km_by_equ:
            km_by_equ[code] = 0
            km_eff_by_equ[code] = 0
            navettes_by_equ[code] = []

        # --- KM estimé (via la ligne associée) ---
        km_est = n.ligne.klm or 0
        km_by_equ[code] += km_est

        

        # KM ligne
        km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0

        # KM aller/retour
        coef_aller  = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
        coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0

        km_effectif = km * coef_aller + km * coef_retour

        km_eff_by_equ[code] += km_effectif


        
        # --- Ajouter la navette dans la liste ---
        navettes_by_equ[code].append(n)

    ###############################################################################
    # 3) Boucle des équipements groupés par des_equ
    ###############################################################################

    equipements = sorted(equipements_qs, key=lambda e: e.des_equ)
    current_model = None

    from datetime import date

    total_general_km = 0.0
    total_general_navettes = 0
    all_ages = []


    for eq in equipements:

        # --- Nouveau groupe ---
        if eq.des_equ != current_model:
            current_model = eq.des_equ
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"<b>{current_model}</b>", styles["Heading2"]))
            elements.append(Spacer(1, 6))

        # ================================
        # Calcul de l'âge + stockage
        # ================================
        dat_aqu = eq.dat_aqu_equ
        dat_ins = eq.dat_ins_equ
        if dat_ins:
            diff_days = (date.today() - dat_ins).days
            all_ages.append(diff_days)
            avg_age = f"{diff_days / 365:.1f} ans"
        else:
            avg_age = "-"

        # ================================
        # KM total estimé + effectif
        # ================================
        km_total = km_by_equ.get(eq.cod_equ, 0)
        km_eff_total = km_eff_by_equ.get(eq.cod_equ, 0)

        # -------------------------------------
        # Ajouter aux totaux globaux
        # -------------------------------------
        total_general_km += km_eff_total

        navs = navettes_by_equ.get(eq.cod_equ, [])
        total_general_navettes += len(navs)

        # Stocker les âges pour la moyenne
        if eq.dat_ins_equ:
            delta = date.today() - eq.dat_ins_equ
            all_ages.append(delta.days)


        
        # ================================
        # Entête tableau véhicule
        # ================================
        vehicule_header = [
            "Code", "Modèle", "Marque", "N° Série", "Immat",
            "Date Acq", "Date MEP", "Âge", "KM Est", "KM Eff"
        ]
        # ================================
        # Ligne véhicule
        # ================================
        vehicule_row = [
            eq.cod_equ,
            eq.mod_equ or "",
            eq.mrq_equ or "",
            eq.num_ser_equ or "",
            eq.imm_equ or "",
            dat_aqu.strftime("%d/%m/%Y") if dat_aqu else "-",
            eq.dat_ins_equ.strftime("%d/%m/%Y") if eq.dat_ins_equ else "-",
            avg_age,
            f"{km_total}",
            f"{km_eff_total}",
        ]

        # 👉 Afficher uniquement si KM Effectif > 0
        if km_eff_total > 0:


            vehicule_table = Table([vehicule_header, vehicule_row], repeatRows=1)
            vehicule_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ]))

            elements.append(vehicule_table)
            elements.append(Spacer(1, 4))

        ############################################################################
        #  Contenu : Navettes du véhicule eq.cod_equ
        ############################################################################

        navs = navettes_by_equ.get(eq.cod_equ, [])

        if navs:
           
            sub_data = [[
                "Ord", "Code", "Origine", "Destination", "Jour",
                "A.Chauf", "Nom", "R.Chauf", "Nom",
                "A.Véh", "R.Véh", "KM", "KM Effectif"
            ]]

            for n in navs:
                km = safe_float(n.ligne.klm if n.ligne and n.ligne.klm else 0.0, 0.0)
                coef_aller  = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
                coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
                km_effectif = km * coef_aller + km * coef_retour

                sub_data.append([
                    getattr(n.ligne, "ord", "") or "",
                    getattr(n.ligne, "code", "") or "",
                    getattr(n.ligne, "origine", "") or "",
                    getattr(n.ligne, "dest", "") or "",
                    safe_date(n.adatserv) if n.adatserv else "",
                    n.achauffeur.mat_emp if n.achauffeur else "",
                    n.achauffeur.nom_emp if n.achauffeur else "",
                    n.rchauffeur.mat_emp if n.rchauffeur else "",
                    n.rchauffeur.nom_emp if n.rchauffeur else "",
                    getattr(n, "aveh", "") or "",
                    getattr(n, "rveh", "") or "",
                    f"{km:.1f}",
                    f"{km_effectif:.1f}"
                ])

            sub_table = Table(
                sub_data,
                colWidths=[20, 30, 60, 60, 30, 40, 70, 40, 70, 25, 25, 30, 50]
            )
            sub_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            elements.append(sub_table)
            elements.append(Spacer(1, 6))



    # --- Synthèse générale ---
    elements.append(PageBreak())
    elements.append(Paragraph("<b>Synthèse Générale</b>", styles['Title']))
    elements.append(Spacer(1, 8))

    


    # Âge moyen global
    if all_ages:
        avg_days_general = mean(all_ages)
        avg_years_general = avg_days_general / 365
        avg_age_general_str = f"{avg_years_general:.1f} ans"
    else:
        avg_age_general_str = "-"

    synthese = [
        ["Total véhicules", len(equipements)],
        ["Total km effectif (période)", f"{total_general_km:.1f}"],
        ["Total navettes (période)", total_general_navettes],
        ["Âge moyen général", avg_age_general_str]
    ]


    table_synth = Table(synthese, colWidths=[250, 120])
    table_synth.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))

    elements.append(table_synth)
    elements.append(Spacer(1, 12))

    # --- Build PDF ---
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from statistics import mean
from collections import defaultdict

from .models import Equipement, Navette
from .utils import safe_date, apply_navette_period_filter


def equipement3_pdf(request):

    # =======================
    # 1️⃣ FILTRES ÉQUIPEMENTS
    # =======================
    equipements = Equipement.objects.all().order_by("des_equ", "cod_equ")

    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    cod_equ = request.GET.get("cod_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    dat_aqu_equ = request.GET.get("dat_aqu_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()

    start = request.GET.get("start", "").strip()
    end = request.GET.get("end", "").strip()

    if cod_fam_equ:
        equipements = equipements.filter(cod_fam_equ=cod_fam_equ)
    if cod_equ:
        equipements = equipements.filter(cod_equ__icontains=cod_equ)
    if mod_equ:
        equipements = equipements.filter(mod_equ__icontains=mod_equ)
    if dat_aqu_equ:
        equipements = equipements.filter(dat_aqu_equ=dat_aqu_equ)
    if cod_sta:
        cod_sta_list = [s.strip() for s in cod_sta.split(",") if s.strip()]
        equipements = equipements.filter(cod_sta__in=cod_sta_list)

    # =======================
    # 2️⃣ PÉRIODE NAVETTES
    # =======================
    start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None
    end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else None

    # =======================
    # 3️⃣ CHARGEMENT NAVETTES (UNE SEULE FOIS 🔥)
    # =======================
    navettes_qs = Navette.objects.select_related(
        "ligne", "achauffeur", "rchauffeur"
    )

    navettes_qs = apply_navette_period_filter(
        navettes_qs, start_date, end_date
    )

    navettes_by_veh = defaultdict(list)
    for n in navettes_qs:
        navettes_by_veh[n.aveh].append(n)

    # =======================
    # 4️⃣ INITIALISATION PDF
    # =======================
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Liste des véhicules du Parc SNTRI", styles["Heading1"]))
    elements.append(Paragraph(f"Date : {datetime.today().strftime('%d/%m/%Y')}", styles["Normal"]))

    if start and end:
        elements.append(Paragraph(f"Période : {start} → {end}", styles["Normal"]))

    elements.append(Spacer(1, 10))

    # =======================
    # 5️⃣ VARIABLES TOTAUX
    # =======================
    today = date.today()

    current_model = None
    model_rows = []

    model_total_veh = 0
    model_total_km = 0
    model_total_disp = 0
    model_total_ages = []

    total_general = 0
    total_general_km = 0
    total_general_navettes = 0
    total_general_aveh_disp = 0
    all_ages = []

    # =======================
    # 6️⃣ FONCTION BLOC MODÈLE
    # =======================
    def print_model_block():
        if len(model_rows) <= 1:
            return []

        block = []
        block.append(Spacer(1, 8))
        block.append(Paragraph(f"<b>Désignation : {current_model}</b>", styles["Heading3"]))
        block.append(Spacer(1, 4))

        if model_total_ages:
            avg_age = f"{(mean(model_total_ages) / 365):.1f} ans"
        else:
            avg_age = "-"

        recap_row = [
            "Âge moy :", avg_age, "", "Veh disp :", model_total_disp,
            "", "", "KM :", f"{model_total_km:.1f}"
        ]

        table_data = model_rows + [recap_row]

        table = Table(table_data, colWidths=[45, 80, 60, 100, 55, 50, 50, 50, 40])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))

        block.append(table)
        block.append(Spacer(1, 10))
        return block

    # =======================
    # 7️⃣ PARCOURS ÉQUIPEMENTS
    # =======================
    for eq in equipements:

        if current_model != eq.des_equ:
            elements.extend(print_model_block())

            current_model = eq.des_equ
            model_rows = [[
                "N° Parc", "Modèle", "Marque", "N° Série",
                "N° Police", "Date Acqu.", "Date Inscrip.", "Âge", "KM Effectif"
            ]]

            model_total_veh = 0
            model_total_km = 0
            model_total_disp = 0
            model_total_ages = []

        # --- ÂGE ---
        if eq.dat_ins_equ:
            diff = relativedelta(today, eq.dat_ins_equ)
            age_str = f"{diff.years}a {diff.months}m {diff.days}j"
            age_days = (today - eq.dat_ins_equ).days
            model_total_ages.append(age_days)
            all_ages.append(age_days)
        else:
            age_str = "-"

        # --- NAVETTES ---
        navettes = navettes_by_veh.get(eq.cod_equ, [])

        km_total = 0
        for n in navettes:
            km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
            km_total += km * (
                (1 if n.achauffeur and n.achauffeur.mat_emp != "30000" else 0) +
                (1 if n.rchauffeur and n.rchauffeur.mat_emp != "30000" else 0)
            )

        # --- LIGNE TABLE ---
        model_rows.append([
            eq.cod_equ,
            eq.des_equ,
            eq.mrq_equ,
            eq.num_ser_equ,
            eq.imm_equ,
            safe_date(eq.dat_aqu_equ),
            safe_date(eq.dat_ins_equ),
            age_str,
            f"{km_total:.1f}",
        ])

        # --- TOTAUX ---
        model_total_veh += 1
        model_total_km += km_total
        if km_total > 0:
            model_total_disp += 1

        total_general += 1
        total_general_km += km_total
        total_general_navettes += len(navettes)
        if km_total > 0:
            total_general_aveh_disp += 1

    elements.extend(print_model_block())

    # =======================
    # 8️⃣ RÉCAP GÉNÉRAL
    # =======================
    elements.append(Spacer(1, 15))

    avg_age_general = f"{(mean(all_ages)/365):.1f} ans" if all_ages else "-"

    elements.append(Paragraph(f"<b>Total général véhicules : {total_general}</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>Total véhicules disponibles : {total_general_aveh_disp}</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>Total km effectif : {total_general_km:.1f}</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>Total navettes : {total_general_navettes}</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>Âge moyen général : {avg_age_general}</b>", styles["Heading3"]))

    # =======================
    # 9️⃣ BUILD PDF
    # =======================
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    return HttpResponse(pdf, content_type="application/pdf")
