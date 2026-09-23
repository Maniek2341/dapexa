from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gwarancja', '0004_warrantyclaimattachment_folder'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='warrantyclaim',
            options={'ordering': ['-created_at'], 'permissions': [('access_warranty_claim_list', 'Dostęp do widoku: warranty claim list'), ('access_warranty_claim_create', 'Dostęp do widoku: warranty claim create'), ('access_warranty_detail', 'Dostęp do widoku: warranty detail'), ('access_warranty_claim_mark_reported', 'Dostęp do widoku: warranty claim mark reported'), ('access_warranty_claim_mark_repaired', 'Dostęp do widoku: warranty claim mark repaired'), ('access_warranty_delete', 'Dostęp do widoku: warranty delete'), ('access_warranty_edit', 'Dostęp do widoku: warranty edit')], 'verbose_name': 'Zgłoszenie gwarancyjne', 'verbose_name_plural': 'Zgłoszenia gwarancyjne'},
        ),
    ]
