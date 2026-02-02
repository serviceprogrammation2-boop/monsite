# blog/utils.py
from datetime import datetime, date
from django.utils.timezone import make_aware
from .models import Navette


# =========================
# SAFE DATE POUR PDF
# =========================
def safe_date(d):
    """
    Retourne une date formatée jj/mm/aaaa ou '-'
    """
    if not d:
        return "-"
    if isinstance(d, (datetime, date)):
        return d.strftime("%d/%m/%Y")
    return str(d)


# =========================
# FILTRE NAVETTES PAR PÉRIODE (PDF)
# =========================
def apply_navette_period_filter(queryset, start_date=None, end_date=None):
    """
    Filtre les navettes par période (dates simples)
    """
    if start_date:
        queryset = queryset.filter(adatserv__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(adatserv__date__lte=end_date)
    return queryset


# =========================
# FILTRE NAVETTES (VUES HTML)
# =========================
def get_filtered_navettes(request):
    navettes = Navette.objects.all().order_by('-adatserv')

    start_str = request.GET.get("start", "")
    end_str   = request.GET.get("end", "")
    chauffeur = request.GET.get("chauffeur", "")
    vehicule  = request.GET.get("vehicule", "")

    if start_str and end_str:
        try:
            start_date = make_aware(datetime.strptime(start_str, "%Y-%m-%d"))
            end_date   = make_aware(
                datetime.strptime(end_str, "%Y-%m-%d")
            ).replace(hour=23, minute=59, second=59)

            navettes = navettes.filter(adatserv__range=[start_date, end_date])
        except Exception:
            pass

    if chauffeur.strip():
        navettes = navettes.filter(achauffeur__nom_emp__icontains=chauffeur)

    if vehicule.strip():
        navettes = navettes.filter(aveh__icontains=vehicule)

    return navettes, start_str, end_str, chauffeur, vehicule
