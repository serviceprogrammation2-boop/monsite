from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_alter_ligne_options_alter_navette_options_and_more'),
    ]

    operations = [
        migrations.RunPython(
            code=lambda apps, schema_editor: None,
            reverse_code=lambda apps, schema_editor: None
        ),
    ]
