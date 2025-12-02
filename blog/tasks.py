import cx_Oracle
from django.conf import settings
from background_task import background
from blog.models import Navette, Ligne, Employe
from datetime import datetime

@background(schedule=0)  # Exécute immédiatement la première fois
def sync_navettes_additive():
    try:
        conn = cx_Oracle.connect(
            user=settings.ORACLE_GMAO['user'],
            password=settings.ORACLE_GMAO['password'],
            dsn=settings.ORACLE_GMAO['dsn'],
            encoding="UTF-8"
        )
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Erreur connexion Oracle : {e}")
        return

    cursor.execute("""
        SELECT 
            LIGNE, ASENS, ATYPSERV, NDA, ADATSERV,
            "ACHAUFFEUR", "RCHAUFFEUR", AVEH, RVEH,
            NDR, AGS, REM
        FROM NAVETTE
        WHERE ASUPP = 0
    """)

    rows = cursor.fetchall()
    print(f"📦 {len(rows)} enregistrements Oracle trouvés.")

    for row in rows:
        ligne_code = row[0]
        asens = row[1]
        atypsrv = row[2]
        nda = row[3]
        adatserv = row[4]   # <- on prend ADATSERV par index
        if hasattr(adatserv, "date"):
            adatserv = adatserv.date()  # convertit datetime -> date
                    

        ligne_obj = Ligne.objects.filter(code=ligne_code).first()
        if not ligne_obj:
            continue

        ach = Employe.objects.filter(mat_emp=row[5]).first() if row[5] else None
        rch = Employe.objects.filter(mat_emp=row[6]).first() if row[6] else None

        navette, created = Navette.objects.update_or_create(
            ligne=ligne_obj,
            asens=row[1],
            atypsrv=row[2],
            adatserv=adatserv,
            defaults={
                "nda": row[3],
                "achauffeur": Employe.objects.filter(mat_emp=row[5]).first() if row[5] else None,
                "rchauffeur": Employe.objects.filter(mat_emp=row[6]).first() if row[6] else None,
                "aveh": row[7],
                "rveh": row[8],
                "ndr": row[9],
                "ags": row[10],
                "rem": row[11],
            }
        )



    cursor.close()
    conn.close()
    print("✅ Synchronisation additive terminée !")
