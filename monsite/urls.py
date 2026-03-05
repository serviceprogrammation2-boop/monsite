from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Admin classique
    path('admin/', admin.site.urls),

    
    # Routes de ton app blog
    path('', include('blog.urls')),

    # Login / Logout standard
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]