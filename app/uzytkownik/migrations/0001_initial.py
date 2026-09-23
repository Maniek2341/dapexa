import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0019_alter_paneluser_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyRoleGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('role', models.CharField(choices=[('owner', 'Właściciel'), ('manager', 'Manager'), ('biuro', 'Biuro'), ('podwykonawca', 'Podwykonawca'), ('employee', 'Pracownik'), ('client', 'Klient')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permission_groups', to='core.company')),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='company_role_group', to='auth.group')),
            ],
            options={
                'verbose_name': 'Grupa uprawnień roli',
                'verbose_name_plural': 'Grupy uprawnień ról',
                'ordering': ['role', 'name'],
                'constraints': [models.UniqueConstraint(fields=('company', 'name'), name='unique_role_group_name_per_company')],
            },
        ),
    ]
