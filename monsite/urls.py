from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from blog.views import download_backup   # 👈 AJOUTE CETTE LIGNE

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blog.urls')),

    # 🔴 AJOUTE CETTE LIGNE
    path('admin/backup-db/', download_backup, name='backup_db'),

    # Login / Logout standard
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]