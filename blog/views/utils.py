from datetime import datetime, timedelta


def safe_date(d):
    """Formate une date en DD/MM/YYYY, retourne '' si None."""
    if not d:
        return ""
    try:
        return d.strftime("%d/%m/%Y")
    except Exception:
        return ""


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
    """Retourne datetime.date ou None depuis 'YYYY-MM-DD'."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def apply_navette_period_filter(qs, start_date, end_date):
    """Filtre queryset Navette sur la période inclusive start..end."""
    if not start_date or not end_date:
        return qs
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return qs.filter(adatserv__gte=start_dt, adatserv__lt=end_dt)