from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_alter_paneluser_role"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="paneluser",
            options={
                "permissions": [
                    (
                        "delete_company_employee",
                        "Może usuwać pracowników swojej firmy",
                    ),
                ],
                "verbose_name": "Użytkownik",
                "verbose_name_plural": "Użytkownicy",
            },
        ),
    ]
