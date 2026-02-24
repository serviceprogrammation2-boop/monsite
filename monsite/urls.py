
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('navettes.urls')),  # 👈 remplace blog par navettes
]