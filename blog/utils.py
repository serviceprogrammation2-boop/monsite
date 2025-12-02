# blog/utils.py
from datetime import datetime
from django.utils.timezone import make_aware
from .models import Navette

def get_filtered_navettes(request):
    navettes = Navette.objects.all().order_by('-adatserv')

    start_str = request.GET.get("start", "")
    end_str   = request.GET.get("end", "")
    chauffeur = request.GET.get("chauffeur", "")
    vehicule  = request.GET.get("vehicule", "")

    if start_str and end_str:
        try:
            start_date = make_aware(datetime.strptime(start_str, "%Y-%m-%d"))
            end_date   = make_aware(datetime.strptime(end_str, "%Y-%m-%d")).replace(hour=23, minute=59, second=59)
            navettes = navettes.filter(adatserv__range=[start_date, end_date])
        except Exception:
            pass

    if chauffeur.strip():
        navettes = navettes.filter(achauffeur__nom_emp__icontains=chauffeur)

    if vehicule.strip():
        navettes = navettes.filter(aveh__icontains=vehicule)

    return navettes, start_str, end_str, chauffeur, vehicule
