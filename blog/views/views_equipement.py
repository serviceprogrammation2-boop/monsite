from io import BytesIO
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from statistics import mean
from collections import defaultdict

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

from ..models import Equipement, Navette
from ..utils import safe_date, apply_navette_period_filter


def equipement_list(request):
    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()

    equipements = Equipement.objects.all()

    if cod_fam_equ:
        equipements = equipements.filter(cod_fam_equ=cod_fam_equ)
    if mod_equ:
        equipements = equipements.filter(mod_equ__icontains=mod_equ)
    if cod_sta:
        cod_sta_list = [s.strip() for s in cod_sta.split(",") if s.strip()]
        equipements = equipements.filter(cod_sta__in=cod_sta_list)

    equipements = equipements.order_by("cod_equ")

    today = date.today()
    for eq in equipements:
        if eq.dat_ins_equ:
            diff = relativedelta(today, eq.dat_ins_equ)
            eq.age = f"{diff.years} ans {diff.months} mois {diff.days} jours"
        else:
            eq.age = "-"

    paginator = Paginator(equipements, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "blog/equipement_list.html", {
        "page_obj": page_obj,
        "cod_fam_equ": cod_fam_equ,
        "mod_equ": mod_equ,
        "cod_sta": cod_sta,
        "total_count": equipements.count(),
    })


def _base_equipement_pdf_qs(request):
    """Retourne le queryset équipements filtré selon les paramètres GET communs."""
    equipements = Equipement.objects.all().order_by('cod_equ')
    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    cod_equ = request.GET.get("cod_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    dat_aqu_equ = request.GET.get("dat_aqu_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()

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
    return equipements


def equipement_pdf(request):
    equipements = _base_equipement_pdf_qs(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="equipements.pdf"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    centered_title = ParagraphStyle('CenteredTitle', parent=styles['Heading1'], alignment=1, spaceAfter=12)
    elements.append(Paragraph("Liste des vehicules de Parc SNTRI", centered_title))
    elements.append(Paragraph(f"Date : {datetime.today().strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 10))

    data = [['N° Parc', 'Désignation', 'Modèle', 'N° Série', 'N° de Police',
             'Date acquisition', 'Date inscription', 'Âge (ans-mois-jour)']]

    today = date.today()
    for eq in equipements:
        if eq.dat_ins_equ:
            diff = relativedelta(today, eq.dat_ins_equ)
            age = f"{diff.years} ans {diff.months} mois {diff.days} jours"
        else:
            age = "-"
        data.append([
            eq.cod_equ or "", eq.des_equ or "", eq.mod_equ or "",
            eq.num_ser_equ or "", eq.imm_equ or "",
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
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table)
        elements.append(Paragraph(f"<br/><b>Total : {len(equipements)} équipements</b>", styles['Normal']))

    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


def equipement1_pdf(request):
    equipements = _base_equipement_pdf_qs(request).order_by('des_equ', 'cod_equ')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="equipements.pdf"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    centered_title = ParagraphStyle('CenteredTitle', parent=styles['Heading1'], alignment=1, spaceAfter=12)
    elements.append(Paragraph("Liste des vehicules de Parc SNTRI", centered_title))
    elements.append(Paragraph(f"Date : {datetime.today().strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 10))

    today = date.today()
    current_model = None
    model_rows = []
    model_ages = []
    all_ages = []
    total_general = 0

    for eq in equipements:
        if current_model and eq.des_equ != current_model:
            avg_age_str = f"{(mean(model_ages) / 365):.1f} ans" if model_ages else "-"
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"<b>Désignation : {current_model}</b>", styles['Heading3']))
            elements.append(Spacer(1, 5))
            table = Table(model_rows, colWidths=[30, 70, 70, 90, 50, 70, 70, 90])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            elements.append(table)
            elements.append(Paragraph(f"<b>Total véhicules : {len(model_rows)-1}</b>", styles['Normal']))
            elements.append(Paragraph(f"<b>Âge moyen : {avg_age_str}</b>", styles['Normal']))
            elements.append(Spacer(1, 12))
            model_rows = []
            model_ages = []

        if eq.des_equ != current_model:
            current_model = eq.des_equ
            model_rows.append(['N° Parc', 'Modèle', 'marque', 'N° Série', 'N° Police',
                                'Date acquisition', 'Date inscription', 'Âge'])

        if eq.dat_ins_equ:
            diff = relativedelta(today, eq.dat_ins_equ)
            age_days = (today - eq.dat_ins_equ).days
            model_ages.append(age_days)
            all_ages.append(age_days)
            age = f"{diff.years}a {diff.months}m {diff.days}j"
        else:
            age = "-"

        model_rows.append([
            eq.cod_equ or "", eq.mod_equ or "", eq.mrq_equ or "",
            eq.num_ser_equ or "", eq.imm_equ or "",
            eq.dat_aqu_equ.strftime("%d/%m/%Y") if eq.dat_aqu_equ else "",
            eq.dat_ins_equ.strftime("%d/%m/%Y") if eq.dat_ins_equ else "",
            age
        ])
        total_general += 1

    # Dernier modèle
    if current_model and len(model_rows) > 1:
        avg_age_str = f"{(mean(model_ages) / 365):.1f} ans" if model_ages else "-"
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>Désignation : {current_model}</b>", styles['Heading3']))
        elements.append(Spacer(1, 5))
        table = Table(model_rows, colWidths=[30, 70, 70, 90, 50, 70, 70, 90])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Paragraph(f"<b>Total véhicules : {len(model_rows)-1}</b>", styles['Normal']))
        elements.append(Paragraph(f"<b>Âge moyen : {avg_age_str}</b>", styles['Normal']))
        elements.append(Spacer(1, 12))

    avg_age_general = f"{(mean(all_ages) / 365):.1f} ans" if all_ages else "-"
    elements.append(Paragraph(f"<b>Total général véhicules : {total_general}</b>", styles['Heading3']))
    elements.append(Paragraph(f"<b>Âge moyen général : {avg_age_general}</b>", styles['Heading3']))

    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


def equipement2_pdf(request):
    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    cod_equ_f = request.GET.get("cod_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    dat_aqu_equ = request.GET.get("dat_aqu_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()
    start = request.GET.get("start", "").strip()
    end = request.GET.get("end", "").strip()

    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None
        end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else None
    except Exception:
        start_date = end_date = None

    equipements_qs = Equipement.objects.all()
    if cod_fam_equ:
        equipements_qs = equipements_qs.filter(cod_fam_equ=cod_fam_equ)
    if cod_equ_f:
        equipements_qs = equipements_qs.filter(cod_equ__icontains=cod_equ_f)
    if mod_equ:
        equipements_qs = equipements_qs.filter(mod_equ__icontains=mod_equ)
    if dat_aqu_equ:
        equipements_qs = equipements_qs.filter(dat_aqu_equ__icontains=dat_aqu_equ)
    if cod_sta:
        cod_sta_list = [s.strip() for s in cod_sta.split(",") if s.strip()]
        equipements_qs = equipements_qs.filter(cod_sta__in=cod_sta_list)

    equipements_qs = equipements_qs.order_by('des_equ', 'cod_equ')

    # Navettes sur la période
    navettes_qs = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")
    if start_date and end_date:
        navettes_qs = navettes_qs.filter(
            adatserv__date__gte=start_date,
            adatserv__date__lte=end_date
        )

    km_by_equ = {}
    km_eff_by_equ = {}
    navettes_by_equ = {}

    for n in navettes_qs:
        code = (n.aveh or "").strip()
        if not code:
            continue
        if code not in km_by_equ:
            km_by_equ[code] = 0
            km_eff_by_equ[code] = 0
            navettes_by_equ[code] = []
        km_est = n.ligne.klm or 0
        km_by_equ[code] += km_est
        km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
        coef_aller = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
        coef_retour = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
        km_eff_by_equ[code] += km * coef_aller + km * coef_retour
        navettes_by_equ[code].append(n)

    buffer = BytesIO()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="equipements.pdf"'
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Liste des véhicules du Parc SNTRI", styles['Heading1']))
    elements.append(Paragraph(f"Date : {date.today().strftime('%d/%m/%Y')}", styles['Normal']))
    if start_date and end_date:
        elements.append(Paragraph(f"Période : {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 8))

    today = date.today()
    current_model = None
    total_general_km = 0.0
    total_general_navettes = 0
    all_ages = []

    for eq in sorted(equipements_qs, key=lambda e: e.des_equ):
        if eq.des_equ != current_model:
            current_model = eq.des_equ
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"<b>{current_model}</b>", styles["Heading2"]))
            elements.append(Spacer(1, 6))

        if eq.dat_ins_equ:
            diff_days = (today - eq.dat_ins_equ).days
            all_ages.append(diff_days)
            avg_age = f"{diff_days / 365:.1f} ans"
        else:
            avg_age = "-"

        km_eff_total = km_eff_by_equ.get(eq.cod_equ, 0)
        total_general_km += km_eff_total
        navs = navettes_by_equ.get(eq.cod_equ, [])
        total_general_navettes += len(navs)

        if km_eff_total > 0:
            veh_header = ["Code", "Modèle", "Marque", "N° Série", "Immat",
                          "Date Acq", "Date MEP", "Âge", "KM Est", "KM Eff"]
            veh_row = [
                eq.cod_equ, eq.mod_equ or "", eq.mrq_equ or "", eq.num_ser_equ or "",
                eq.imm_equ or "",
                eq.dat_aqu_equ.strftime("%d/%m/%Y") if eq.dat_aqu_equ else "-",
                eq.dat_ins_equ.strftime("%d/%m/%Y") if eq.dat_ins_equ else "-",
                avg_age, f"{km_by_equ.get(eq.cod_equ, 0)}", f"{km_eff_total}"
            ]
            vt = Table([veh_header, veh_row])
            vt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(vt)
            elements.append(Spacer(1, 4))

        if navs:
            sub_data = [["Ord", "Code", "Origine", "Destination", "Jour",
                         "A.Chauf", "Nom", "R.Chauf", "Nom", "A.Véh", "R.Véh", "KM", "KM Eff"]]
            for n in navs:
                km = float(n.ligne.klm) if n.ligne and n.ligne.klm else 0
                coef_a = 1 if (n.achauffeur and n.achauffeur.mat_emp != "30000") else 0
                coef_r = 1 if (n.rchauffeur and n.rchauffeur.mat_emp != "30000") else 0
                sub_data.append([
                    getattr(n.ligne, "ord", "") or "", getattr(n.ligne, "code", "") or "",
                    getattr(n.ligne, "origine", "") or "", getattr(n.ligne, "dest", "") or "",
                    safe_date(n.adatserv) if n.adatserv else "",
                    n.achauffeur.mat_emp if n.achauffeur else "",
                    n.achauffeur.nom_emp if n.achauffeur else "",
                    n.rchauffeur.mat_emp if n.rchauffeur else "",
                    n.rchauffeur.nom_emp if n.rchauffeur else "",
                    getattr(n, "aveh", "") or "", getattr(n, "rveh", "") or "",
                    f"{km:.1f}", f"{km * coef_a + km * coef_r:.1f}"
                ])
            st = Table(sub_data, colWidths=[20, 30, 60, 60, 30, 40, 70, 40, 70, 25, 25, 30, 50])
            st.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            elements.append(st)
            elements.append(Spacer(1, 6))

    elements.append(PageBreak())
    elements.append(Paragraph("<b>Synthèse Générale</b>", styles['Title']))
    elements.append(Spacer(1, 8))

    avg_age_general = f"{(mean(all_ages) / 365):.1f} ans" if all_ages else "-"
    synthese = [
        ["Total véhicules", len(list(equipements_qs))],
        ["Total km effectif (période)", f"{total_general_km:.1f}"],
        ["Total navettes (période)", total_general_navettes],
        ["Âge moyen général", avg_age_general]
    ]
    ts = Table(synthese, colWidths=[250, 120])
    ts.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(ts)

    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


def equipement3_pdf(request):
    equipements = Equipement.objects.all().order_by("des_equ", "cod_equ")

    cod_fam_equ = request.GET.get("cod_fam_equ", "").strip()
    cod_equ_f = request.GET.get("cod_equ", "").strip()
    mod_equ = request.GET.get("mod_equ", "").strip()
    dat_aqu_equ = request.GET.get("dat_aqu_equ", "").strip()
    cod_sta = request.GET.get("cod_sta", "").strip()
    start = request.GET.get("start", "").strip()
    end = request.GET.get("end", "").strip()

    if cod_fam_equ:
        equipements = equipements.filter(cod_fam_equ=cod_fam_equ)
    if cod_equ_f:
        equipements = equipements.filter(cod_equ__icontains=cod_equ_f)
    if mod_equ:
        equipements = equipements.filter(mod_equ__icontains=mod_equ)
    if dat_aqu_equ:
        equipements = equipements.filter(dat_aqu_equ=dat_aqu_equ)
    if cod_sta:
        cod_sta_list = [s.strip() for s in cod_sta.split(",") if s.strip()]
        equipements = equipements.filter(cod_sta__in=cod_sta_list)

    start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None
    end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else None

    navettes_qs = Navette.objects.select_related("ligne", "achauffeur", "rchauffeur")
    navettes_qs = apply_navette_period_filter(navettes_qs, start_date, end_date)

    navettes_by_veh = defaultdict(list)
    for n in navettes_qs:
        navettes_by_veh[n.aveh].append(n)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Liste des véhicules du Parc SNTRI", styles["Heading1"]))
    elements.append(Paragraph(f"Date : {datetime.today().strftime('%d/%m/%Y')}", styles["Normal"]))
    if start and end:
        elements.append(Paragraph(f"Période : {start} → {end}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    today = date.today()
    current_model = None
    model_rows = []
    model_total_km = 0
    model_total_disp = 0
    model_total_ages = []
    total_general = 0
    total_general_km = 0
    total_general_navettes = 0
    total_general_aveh_disp = 0
    all_ages = []

    def print_model_block():
        if len(model_rows) <= 1:
            return []
        block = []
        avg_age = f"{(mean(model_total_ages) / 365):.1f} ans" if model_total_ages else "-"
        recap_row = ["Âge moy :", avg_age, "", "Veh disp :", model_total_disp,
                     "", "", "KM :", f"{model_total_km:.1f}"]
        table = Table(model_rows + [recap_row], colWidths=[45, 80, 60, 100, 55, 50, 50, 50, 40])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        block.append(Spacer(1, 8))
        block.append(Paragraph(f"<b>Désignation : {current_model}</b>", styles["Heading3"]))
        block.append(Spacer(1, 4))
        block.append(table)
        block.append(Spacer(1, 10))
        return block

    for eq in equipements:
        if current_model != eq.des_equ:
            elements.extend(print_model_block())
            current_model = eq.des_equ
            model_rows = [["N° Parc", "Modèle", "Marque", "N° Série",
                            "N° Police", "Date Acqu.", "Date Inscrip.", "Âge", "KM Effectif"]]
            model_total_km = 0
            model_total_disp = 0
            model_total_ages = []

        if eq.dat_ins_equ:
            diff = relativedelta(today, eq.dat_ins_equ)
            age_str = f"{diff.years}a {diff.months}m {diff.days}j"
            age_days = (today - eq.dat_ins_equ).days
            model_total_ages.append(age_days)
            all_ages.append(age_days)
        else:
            age_str = "-"

        navs = navettes_by_veh.get(eq.cod_equ, [])
        km_total = sum(
            float(n.ligne.klm if n.ligne and n.ligne.klm else 0) *
            ((1 if n.achauffeur and n.achauffeur.mat_emp != "30000" else 0) +
             (1 if n.rchauffeur and n.rchauffeur.mat_emp != "30000" else 0))
            for n in navs
        )

        model_rows.append([
            eq.cod_equ, eq.des_equ, eq.mrq_equ, eq.num_ser_equ, eq.imm_equ,
            safe_date(eq.dat_aqu_equ), safe_date(eq.dat_ins_equ), age_str, f"{km_total:.1f}"
        ])

        model_total_km += km_total
        model_total_disp += 1 if km_total > 0 else 0
        total_general += 1
        total_general_km += km_total
        total_general_navettes += len(navs)
        if km_total > 0:
            total_general_aveh_disp += 1

    elements.extend(print_model_block())
    elements.append(Spacer(1, 15))

    avg_age_general = f"{(mean(all_ages)/365):.1f} ans" if all_ages else "-"
    elements.append(Paragraph(f"<b>Total général véhicules : {total_general}</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>Total véhicules disponibles : {total_general_aveh_disp}</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>Total km effectif : {total_general_km:.1f}</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>Total navettes : {total_general_navettes}</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>Âge moyen général : {avg_age_general}</b>", styles["Heading3"]))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return HttpResponse(pdf, content_type="application/pdf")