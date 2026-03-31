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

# Modèles
from ..models import Navette, Ligne, Employe, Equipement, Locatile

# Utils
from ..utils import safe_date, safe_float, safe_int, parse_date_iso, apply_navette_period_filter, MAP_SORTIE

# Forms
from ..forms import NavetteEditForm, NavetteFormSet

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
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
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

def raportjs_pdf(request):

    MAP_SORTIE = {
        1: "Dépôt Ben Arous",
        2: "Gare Routière Nord",
        3: "Gare Routière Sud",
        4: "Convention",
    }

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from itertools import groupby
    from io import BytesIO

    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    navettes = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
        except:
            pass

    navettes_sorted = list(navettes.order_by("adatserv", "ligne__sortie", "ligne__ord"))

    styles = getSampleStyleSheet()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20, leftMargin=20,
        topMargin=20, bottomMargin=20
    )

    elements = []
    elements.append(Paragraph("<b>Liste Journalière des Navettes SNTRI</b>", styles['Title']))
    if start_str and end_str:
        elements.append(Paragraph(f"Période : {start_str} → {end_str}", styles['Normal']))
    elements.append(Spacer(1, 10))

    grand = {"navettes": 0, "km": 0, "km_eff": 0, "achauff": set(), "rchauff": set(), "aveh": set(), "rveh": set()}

    for sortie, group_sortie in groupby(navettes_sorted, key=lambda n: n.ligne.sortie if n.ligne else 0):
        group_list = list(group_sortie)
        sortie_label = MAP_SORTIE.get(sortie, "Non renseignée")

        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>{sortie_label}</b>", styles['Heading2']))

        data = [['Ord', 'Ligne', 'Origine', 'Destination', 'Agence', 'Date',
                 'A.Mle', 'A.Chauffeur', 'R.Mle', 'R.Chauffeur', 'A.Veh', 'R.Veh', 'KM', 'KM Eff']]

        achauff_set, rchauff_set = set(), set()
        aveh_set, rveh_set = set(), set()
        total_km_eff = 0

        for n in group_list:
            km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0

            try:
                a = n.achauffeur
                amat = a.mat_emp if a else ""
                anom = a.nom_emp if a else ""
                coef_a = 1 if a and amat != "30000" else 0
                if a: achauff_set.add(amat)
            except Employe.DoesNotExist:
                amat = anom = ""
                coef_a = 0

            try:
                r = n.rchauffeur
                rmat = r.mat_emp if r else ""
                rnom = r.nom_emp if r else ""
                coef_r = 1 if r and rmat != "30000" else 0
                if r and rmat != "30000": rchauff_set.add(rmat)
            except Employe.DoesNotExist:
                rmat = rnom = ""
                coef_r = 0

            km_eff = km * coef_a + km * coef_r
            total_km_eff += km_eff

            if n.aveh: aveh_set.add(str(n.aveh))
            if n.rveh: rveh_set.add(str(n.rveh))

            data.append([
                n.ligne.ord if n.ligne else "",
                n.ligne.code if n.ligne else "",
                n.ligne.origine if n.ligne else "",
                n.ligne.dest if n.ligne else "",
                n.ligne.agence if n.ligne else "",
                n.adatserv.strftime("%d/%m") if n.adatserv else "",
                amat, anom, rmat, rnom,
                str(n.aveh) if n.aveh else "",
                str(n.rveh) if n.rveh else "",
                round(km, 1), round(km_eff, 1),
            ])

        table = Table(data, colWidths=[20, 30, 75, 95, 38, 25, 30, 130, 30, 130, 48, 48, 32, 38])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 6))

        # Récap par sortie
        total_km = sum(float(n.ligne.klm) for n in group_list if n.ligne and n.ligne.klm) * 2
        recap_data = [
            ["Navettes", "KM", "A.Mle", "R.Mle", "Chauffeurs", "A.Véh", "R.Véh", "Véhicules", "Diff", "KM Effectif"],
            [len(group_list), round(total_km, 1), len(achauff_set), len(rchauff_set),
             len(achauff_set) + len(rchauff_set), len(aveh_set), len(rveh_set),
             len(aveh_set) + len(rveh_set), len(group_list) - len(achauff_set), round(total_km_eff, 1)]
        ]
        recap_table = Table(recap_data, colWidths=[65, 65, 55, 55, 80, 55, 55, 80, 55, 80])
        recap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
        ]))
        elements.append(recap_table)
        elements.append(Spacer(1, 12))

        # Cumul global
        grand["navettes"] += len(group_list)
        grand["km"] += total_km
        grand["km_eff"] += total_km_eff
        grand["achauff"].update(achauff_set)
        grand["rchauff"].update(rchauff_set)
        grand["aveh"].update(aveh_set)
        grand["rveh"].update(rveh_set)

    # Récap global
    elements.append(Paragraph("<b>RÉCAPITULATIF GÉNÉRAL</b>", styles['Heading2']))
    recap_global_data = [
        ["Navettes", "KM", "A.Mle", "R.Mle", "A.Véh", "R.Véh", "Différence", "KM Effectif"],
        [grand["navettes"], round(grand["km"], 1), len(grand["achauff"]), len(grand["rchauff"]),
         len(grand["aveh"]), len(grand["rveh"]), grand["navettes"] - len(grand["achauff"]), round(grand["km_eff"], 1)]
    ]
    recap_global_table = Table(recap_global_data, colWidths=[70, 70, 60, 60, 60, 60, 80, 100])
    recap_global_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(recap_global_table)

    doc.build(elements)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport.pdf"'
    response.write(buffer.getvalue())
    buffer.close()
    return response
from datetime import datetime
from io import BytesIO
from itertools import groupby

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from ..models import Navette


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
        navettes = navettes.filter(adatserv__range=(start_date, end_date))

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
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
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

from ..models import Navette


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
            navettes_qs = navettes_qs.filter(adatserv__range=(start_date, end_date))
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
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
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
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
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
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
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
            navettes = navettes.filter(adatserv__range=(start_date, end_date))
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
