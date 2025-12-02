from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa

def export_navettes_pdf(request):
    # récupère tes filtres
    start = request.GET.get("start")
    end = request.GET.get("end")
    chauffeur = request.GET.get("chauffeur", "").strip()
    vehicule = request.GET.get("vehicule", "").strip()

    navettes = ...  # ⚡ ta requête filtrée (comme tu l’as fait pour la liste HTML)

    html = render_to_string("blog/navette_pdf.html", {
        "navettes": navettes,
        "start": start,
        "end": end,
        "chauffeur": chauffeur,
        "vehicule": vehicule,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="navettes.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)

    return response
