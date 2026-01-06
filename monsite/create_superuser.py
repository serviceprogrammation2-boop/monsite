import os
import django

# 🔹 On indique à Django quel settings utiliser
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monsite.settings')
django.setup()

from django.contrib.auth.models import User

# 🔹 Définir ici ton superuser
USERNAME = 'hedi1'
EMAIL = 'serviceprogrammation2@gmail.com'
PASSWORD = 'H1di@2026'  # Choisis un mot de passe sûr

# 🔹 Vérifier si le superuser existe déjà
if not User.objects.filter(username=USERNAME).exists():
    User.objects.create_superuser(username=USERNAME, email=EMAIL, password=PASSWORD)
    print(f"Superuser '{USERNAME}' créé avec succès !")
else:
    print(f"Superuser '{USERNAME}' existe déjà.")
