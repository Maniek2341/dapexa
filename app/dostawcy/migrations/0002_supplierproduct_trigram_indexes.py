from django.contrib.postgres.indexes import GinIndex
from django.db import migrations, models


def create_trigram_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "supp_prod_name_trgm" '
            'ON "dostawcy_supplierproduct" USING gin ("name" gin_trgm_ops)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "supp_prod_sku_trgm" '
            'ON "dostawcy_supplierproduct" USING gin ("sku" gin_trgm_ops)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "supp_prod_ean_trgm" '
            'ON "dostawcy_supplierproduct" USING gin ("ean" gin_trgm_ops)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "supp_prod_mfr_trgm" '
            'ON "dostawcy_supplierproduct" USING gin ("manufacturer" gin_trgm_ops)'
        )


def drop_trigram_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for name in (
            "supp_prod_name_trgm", "supp_prod_sku_trgm",
            "supp_prod_ean_trgm", "supp_prod_mfr_trgm",
        ):
            cursor.execute(f'DROP INDEX IF EXISTS "{name}"')


class Migration(migrations.Migration):
    dependencies = [("dostawcy", "0001_initial")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(create_trigram_indexes, drop_trigram_indexes)],
            state_operations=[
                migrations.AddIndex(
                    model_name="supplierproduct",
                    index=GinIndex(fields=["name"], opclasses=["gin_trgm_ops"], name="supp_prod_name_trgm"),
                ),
                migrations.AddIndex(
                    model_name="supplierproduct",
                    index=GinIndex(fields=["sku"], opclasses=["gin_trgm_ops"], name="supp_prod_sku_trgm"),
                ),
                migrations.AddIndex(
                    model_name="supplierproduct",
                    index=GinIndex(fields=["ean"], opclasses=["gin_trgm_ops"], name="supp_prod_ean_trgm"),
                ),
                migrations.AddIndex(
                    model_name="supplierproduct",
                    index=GinIndex(fields=["manufacturer"], opclasses=["gin_trgm_ops"], name="supp_prod_mfr_trgm"),
                ),
            ],
        ),
    ]
