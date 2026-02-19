from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'
    def ready(self):
        from django.contrib.auth.models import User, Permission
        try:
            user, created = User.objects.get_or_create(
                username="sortie",
                defaults={"password": "nabil2026"}
            )

            perm = Permission.objects.get(codename="can_add_navette_form")
            user.user_permissions.add(perm)
            user.save()

        except Exception as e:
            print(e)
