from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gwarancja', '0005_alter_warrantyclaim_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='warrantyclaim',
            options={'ordering': ['-created_at'], 'permissions': [('access_warranty_claim_list', 'Wyświetlanie listy zgłoszeń gwarancyjnych'), ('access_warranty_claim_create', 'Dodawanie zgłoszeń gwarancyjnych'), ('access_warranty_detail', 'Wyświetlanie szczegółów zgłoszenia gwarancyjnego'), ('access_warranty_claim_mark_reported', 'Oznaczanie reklamacji jako zgłoszonej'), ('access_warranty_claim_mark_repaired', 'Oznaczanie reklamacji jako naprawionej'), ('access_warranty_delete', 'Usuwanie zgłoszeń gwarancyjnych'), ('access_warranty_edit', 'Edytowanie zgłoszeń gwarancyjnych')], 'verbose_name': 'Zgłoszenie gwarancyjne', 'verbose_name_plural': 'Zgłoszenia gwarancyjne'},
        ),
    ]
