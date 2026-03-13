from io import BytesIO
from datetime import datetime
from itertools import groupby

from django.http import HttpResponse
from django.db.models import Q
from django.utils.timezone import make_aware

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from ..models import Navette, Locatile

MAP_SV = {1: "Service Programmation", 2: "Service Mouvement"}
MAP_SORTIE = {1: "Dépôt Ben Arous", 2: "Gare Routière Nord", 3: "Gare Routière Sud", 4: "Convention"}


def _filter_navettes(request, navettes):
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    achauffeur = request.GET.get("achauffeur")
    aveh = request.GET.get("aveh")
    mode = request.GET.get("mode", "")

    if start_str and end_str:
        try:
            start_date = make_aware(datetime.strptime(start_str, "%Y-%m-%d"))
            end_date = make_aware(datetime.strptime(end_str, "%Y-%m-%d"))
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
        except ValueError:
            pass

    if achauffeur:
        navettes = navettes.filter(
            Q(achauffeur__nom_emp__icontains=achauffeur) | Q(achauffeur__mat_emp__icontains=achauffeur)
        )
    if aveh:
        navettes = navettes.filter(aveh__icontains=aveh)

    return navettes, start_str, end_str


def navettes_pdf(request):
    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")
    navettes, start_str, end_str = _filter_navettes(request, navettes)
    navettes = navettes.exclude(
        Q(achauffeur__isnull=True) | Q(achauffeur__nom_emp="") | Q(aveh__isnull=True) | Q(aveh="")
    )
    navettes_sorted = sorted(navettes, key=lambda n: (n.ligne.sv or 0, n.ligne.sortie or 0, n.ligne.agence or ""))

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=navettes.pdf"
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Liste des Navettes SNTRI", styles['Heading1']), Spacer(1, 10)]

    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
        elements.append(Spacer(1, 12))

    total_global = 0
    for sv, group_sv in groupby(navettes_sorted, key=lambda n: n.ligne.sv or 0):
        group_sv_list = list(group_sv)
        total_sv = 0
        for sortie, group_sortie in groupby(group_sv_list, key=lambda n: n.ligne.sortie or 0):
            group_sortie_list = list(group_sortie)
            total_sortie = 0
            sortie_label = MAP_SORTIE.get(sortie, "Non renseignée")
            elements.append(Paragraph(f"<b>{sortie_label}</b>", styles['Heading3']))
            elements.append(Spacer(1, 8))
            for agence, group_agence in groupby(group_sortie_list, key=lambda n: n.ligne.agence or "Sans Agence"):
                group_list = list(group_agence)
                elements.append(Paragraph(f"<b>Agence :</b> {agence}", styles['Heading4']))
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
                nbr = len(group_list)
                total_sortie += nbr
                total_sv += nbr
                total_global += nbr
                elements.append(Paragraph(f"<b>Total agence {agence} :</b> {nbr} navettes", styles['Normal']))
                elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"<b>{sortie_label}</b> — total = {total_sortie}", styles['Heading3']))
            elements.append(Spacer(1, 14))
        service_label = MAP_SV.get(sv, "Non renseigné")
        elements.append(Paragraph(f"<b>{service_label}</b> — total = {total_sv}", styles['Heading2']))
        elements.append(Spacer(1, 18))

    elements.append(Paragraph(f"<b>TOTAL GÉNÉRAL :</b> {total_global} navettes", styles['Title']))
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


def navettes1_pdf(request):
    loc_map = {l.cod_loc: l.lib_loc for l in Locatile.objects.all()}
    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")
    navettes, start_str, end_str = _filter_navettes(request, navettes)
    navettes = navettes.exclude(Q(achauffeur__isnull=True) | Q(aveh__isnull=True) | Q(aveh=""))
    navettes_sorted = sorted(navettes, key=lambda n: (n.ligne.sv or 0, n.ligne.sortie or 0, n.ligne.agence or ""))

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=navettes_synthese.pdf"
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph("<b>Synthèse des Navettes SNTRI</b>", styles['Title']), Spacer(1, 10)]

    data = [["Service", "Sortie", "Agence", "Libellé", "Total Navettes", "Total Km"]]
    total_global_navettes = 0
    total_global_km = 0

    for sv, group_sv in groupby(navettes_sorted, key=lambda n: n.ligne.sv):
        group_sv_list = list(group_sv)
        total_sv_navettes = total_sv_km = 0
        for sortie, group_sortie in groupby(group_sv_list, key=lambda n: n.ligne.sortie):
            group_sortie_list = list(group_sortie)
            total_sortie_navettes = total_sortie_km = 0
            for agence, group_agence in groupby(group_sortie_list, key=lambda n: n.ligne.agence):
                group_list = list(group_agence)
                total_km = sum(float(n.ligne.klm) for n in group_list if n.ligne and n.ligne.klm)
                total_nb = len(group_list)
                libelle = loc_map.get(agence, "Inconnue")
                data.append([MAP_SV.get(sv, ""), MAP_SORTIE.get(sortie, ""), agence, libelle, total_nb, round(total_km, 2)])
                total_sortie_navettes += total_nb
                total_sortie_km += total_km
                total_sv_navettes += total_nb
                total_sv_km += total_km
                total_global_navettes += total_nb
                total_global_km += total_km
            data.append([MAP_SV.get(sv, ""), f"Total {MAP_SORTIE.get(sortie,'')}", "", "", total_sortie_navettes, round(total_sortie_km, 2)])
        data.append([f"Total {MAP_SV.get(sv,'')}", "", "", "", total_sv_navettes, round(total_sv_km, 2)])

    data.append(["TOTAL GENERAL", "", "", "", total_global_navettes, round(total_global_km, 2)])
    table = Table(data, colWidths=[120, 120, 50, 120, 70, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(table)
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


def navettes2_pdf(request):
    loc_map = {l.cod_loc: l.lib_loc for l in Locatile.objects.all()}
    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")
    navettes, start_str, end_str = _filter_navettes(request, navettes)
    navettes_sorted = sorted(navettes, key=lambda n: (n.ligne.sv or 0, n.ligne.sortie or 0, n.ligne.agence or ""))

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=navettes_synthese.pdf"
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph("<b>Synthèse des Navettes SNTRI</b>", styles['Title']), Spacer(1, 10)]

    if start_str and end_str:
        elements.append(Paragraph(f"<b>Période : {start_str} → {end_str}</b>", styles['Heading4']))
        elements.append(Spacer(1, 8))

    data = [["Service", "Sortie", "Agence", "Libellé", "Total Navettes", "Total Km"]]
    total_global_navettes = 0
    total_global_km = 0

    for sv, group_sv in groupby(navettes_sorted, key=lambda n: n.ligne.sv):
        group_sv_list = list(group_sv)
        total_sv_navettes = total_sv_km = 0
        for sortie, group_sortie in groupby(group_sv_list, key=lambda n: n.ligne.sortie):
            group_sortie_list = list(group_sortie)
            total_sortie_navettes = total_sortie_km = 0
            for agence, group_agence in groupby(group_sortie_list, key=lambda n: n.ligne.agence):
                group_list = list(group_agence)
                total_km = sum(float(n.ligne.klm) for n in group_list if n.ligne and n.ligne.klm)
                total_nb = len(group_list)
                libelle = loc_map.get(agence, "Inconnue")
                data.append([MAP_SV.get(sv, ""), MAP_SORTIE.get(sortie, ""), agence, libelle, total_nb, round(total_km, 2)])
                total_sortie_navettes += total_nb
                total_sortie_km += total_km
                total_sv_navettes += total_nb
                total_sv_km += total_km
                total_global_navettes += total_nb
                total_global_km += total_km
            data.append(["", f"Total {MAP_SORTIE.get(sortie,'')}", "", "", total_sortie_navettes, round(total_sortie_km, 2)])
        data.append([f"Total {MAP_SV.get(sv,'')}", "", "", "", total_sv_navettes, round(total_sv_km, 2)])

    data.append(["TOTAL GENERAL", "", "", "", total_global_navettes, round(total_global_km, 2)])
    table = Table(data, colWidths=[120, 120, 50, 120, 70, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (1, 1), (-1, -1), colors.beige),
    ]))
    elements.append(table)
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


def navettes3_pdf(request):
    navettes = Navette.objects.select_related("ligne", "achauffeur")
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__date__range=(start_date, end_date))
        except Exception:
            pass

    navettes_sorted = navettes.order_by("ligne__sortie", "ligne__code", "adatserv")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport.pdf"'

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = [Paragraph("<b>Liste Journalière des Navettes SNTRI</b>", styles['Title'])]

    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
        elements.append(Spacer(1, 10))

    for sortie, group_sortie in groupby(navettes_sorted, key=lambda n: n.ligne.sortie or 0):
        group_sortie = list(group_sortie)
        sortie_label = MAP_SORTIE.get(sortie, "Non renseignée")
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>{sortie_label}</b>", styles['Heading2']))

        for code, group_code in groupby(group_sortie, key=lambda n: n.ligne.code if n.ligne else "???"):
            code_list = list(group_code)
            elements.append(Paragraph(f"<b>Code : {code}</b>", styles['Heading3']))
            elements.append(Spacer(1, 4))

            data = [['ord', 'Ligne', 'Origine', 'Destination', 'Agence', 'Date',
                     'A.Mle', 'A.Chauffeur', 'R.Mle', 'R.Chauffeur',
                     'A.Véhicule', 'R.Véhicule', 'KM', 'KM Effectif']]

            for n in code_list:
                km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
                coef_a = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
                coef_r = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
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
                    n.aveh or "", n.rveh or "", km, km * coef_a + km * coef_r
                ])

            table = Table(data, colWidths=[20, 30, 90, 100, 40, 25, 35, 130, 35, 130, 45, 45, 40, 60])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))

    doc.build(elements)
    return response