from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0035_alter_paneluser_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="stripe_event_created",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="stripe_checkout_session_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="subscription",
            name="stripe_checkout_attempt",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="StripeWebhookEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(max_length=120)),
                ("event_created", models.PositiveBigIntegerField(default=0)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
