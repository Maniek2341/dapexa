from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0019_alter_paneluser_options'),
        ('uzytkownik', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyrolegroup',
            name='is_system',
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name='companyrolegroup',
            constraint=models.UniqueConstraint(condition=models.Q(('is_system', True)), fields=('company', 'role'), name='unique_system_role_group_per_company'),
        ),
    ]
