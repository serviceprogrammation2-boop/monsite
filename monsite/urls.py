from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),   # <-- ajoute cette ligne
    path('', include('blog.urls')),    # <-- ton app blog reste ici
]
