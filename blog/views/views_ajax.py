from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from ..models import Employe, Equipement, Ligne



def search_employe(request):
    term = request.GET.get('term', '').strip()
    if term:
        employes = Employe.objects.filter(
            Q(mat_emp__icontains=term) | Q(nom_emp__icontains=term)
        ).order_by('nom_emp')[:20]
    else:
        employes = Employe.objects.none()

    results = [
        {"id": e.pk, "text": f"{e.mat_emp} - {e.nom_emp or '-'}"}
        for e in employes
    ]
    return JsonResponse({"results": results})



def search_equipement(request):
    term = request.GET.get('term', '')
    equipements = Equipement.objects.filter(cod_equ__icontains=term)[:20]
    results = [{"id": e.pk, "text": f"{e.cod_equ}"} for e in equipements]
    return JsonResponse({"results": results})


def search_ligne(request):
    term = request.GET.get('term', '')
    lignes = Ligne.objects.filter(
        Q(code__icontains=term) | Q(origine__icontains=term) | Q(dest__icontains=term)
    ).order_by('code')[:20]
    
    results = [{'id': l.code, 'text': f"{l.code} - {l.dest} → {l.origine}"} for l in lignes]
    return JsonResponse({'results': results})