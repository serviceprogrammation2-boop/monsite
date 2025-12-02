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
    total_rows = len(rows)
    print(f"📦 {total_rows} enregistrements Oracle trouvés.")

    total_insert = 0
    total_update = 0

    for i, row in enumerate(rows, start=1):
        ligne_code = row[0]
        asens = row[1]
        atypsrv = row[2]
        nda = row[3]
        adatserv = row[4]

        ligne_obj = Ligne.objects.filter(code=ligne_code).first()
        if not ligne_obj:
            continue

        ach = Employe.objects.filter(mat_emp=row[5]).first() if row[5] else None
        rch = Employe.objects.filter(mat_emp=row[6]).first() if row[6] else None

        navette, created = Navette.objects.update_or_create(
            ligne=ligne_obj,
            asens=asens,
            atypsrv=atypsrv,
            adatserv=adatserv,
            defaults={
                "nda": nda,
                "achauffeur": ach,
                "rchauffeur": rch,
                "aveh": row[7],
                "rveh": row[8],
                "ndr": row[9],
                "ags": row[10],
                "rem": row[11]
            }
        )

        if created:
            total_insert += 1
        else:
            total_update += 1

        # Afficher la progression toutes les 500 lignes
        if i % 500 == 0 or i == total_rows:
            print(f"🔄 {i}/{total_rows} traitées — ➕ {total_insert} insérées, ♻️ {total_update} mises à jour")

    cursor.close()
    conn.close()
    print("✅ Synchronisation additive terminée !")
    print(f"📊 Total insérés : {total_insert}, Total mis à jour : {total_update}")
