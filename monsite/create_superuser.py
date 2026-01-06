

import os
import django
import sys

# Ajouter le dossier parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Définir le module de settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monsite.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Créer le superuser si il n'existe pas
username = 'hedi1'
email = 'serviceprogrammation2@gmail.com'
password = 'H1di@2026'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Superuser '{username}' créé !")
else:
    print(f"Superuser '{username}' existe déjà.")
