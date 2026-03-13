import os
import tempfile
from itertools import groupby
from operator import attrgetter

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from weasyprint import HTML

from ..models import Ligne

MAP_SORTIE = {
    1: "Dépôt Ben Arous",
    2: "Gare Routière Nord",
    3: "Gare Routière Sud",
    4: "Convention",
}


def ligne_list(request):
    lignes = Ligne.objects.all()

    code = request.GET.get("code") or request.POST.get("code")
    agence = request.GET.get("agence") or request.POST.get("agence")
    actif = request.GET.get("actif") or request.POST.get("actif")
    sortie = request.GET.get("sortie") or request.POST.get("sortie")

    if agence:
        lignes = lignes.filter(agence=agence)
    if actif in ["1", "true", "True"]:
        lignes = lignes.filter(actif=1)
    elif actif in ["0", "false", "False"]:
        lignes = lignes.filter(actif=0)
    if code:
        lignes = lignes.filter(code__icontains=code)
    if sortie:
        lignes = lignes.filter(sortie=sortie)

    lignes = lignes.order_by("sortie", "ord")

    paginator = Paginator(lignes, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "blog/ligne_list.html", {
        "MAP_SORTIE": MAP_SORTIE,
        "sortie": sortie or "",
        "code": code or "",
        "agence": agence or "",
        "actif": actif or "",
        "actif_true": actif in ["1", "true", "True"],
        "actif_false": actif in ["0", "false", "False"],
        "page_obj": page_obj,
        "lignes": page_obj.object_list,
    })


def ligne_pdf(request):
    lignes = Ligne.objects.all()

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

    lignes = lignes.order_by("sortie", "ord")

    groupes = {}
    for sortie, items in groupby(lignes, key=attrgetter("sortie")):
        groupes[sortie] = list(items)

    html_string = render_to_string("blog/ligne_pdf.html", {
        "groupes": groupes,
        "map_sortie": MAP_SORTIE,
    })

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="lignes.pdf"'

    tmp_path = os.path.join(tempfile.gettempdir(), "lignes_export.pdf")
    HTML(string=html_string).write_pdf(target=tmp_path)

    with open(tmp_path, 'rb') as f:
        response.write(f.read())
    os.remove(tmp_path)
    return response