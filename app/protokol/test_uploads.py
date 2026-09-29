import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.core.models import Company, PanelUser, Subscription
from app.klient.models import Client
from app.protokol.models import Protocol, ProtokolImage


class ProtocolAttachmentUploadTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.settings_override.enable()

        self.company = Company.objects.create(name="Firma testowa")
        self.user = PanelUser.objects.create_user(
            email="protocol-upload@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.OWNER,
        )
        Subscription.objects.create(
            company=self.company,
            owner=self.user,
            package=Subscription.Package.START,
            status=Subscription.STATUS_ACTIVE,
        )
        self.client_record = Client.objects.create(
            company=self.company,
            name="Klient testowy",
        )

    def tearDown(self):
        self.settings_override.disable()
        self.media_directory.cleanup()

    def test_create_protocol_saves_multiple_attachments(self):
        self.client.force_login(
            self.user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        now = timezone.localtime(timezone.now())
        response = self.client.post(
            reverse("protokol_add"),
            {
                "client": str(self.client_record.pk),
                "title": "Protokół testowy",
                "end_time": now.strftime("%Y-%m-%dT%H:%M"),
                "rodzaj_prac": Protocol.RodzajPrac.NAPRAWA,
                "urzadzenia-TOTAL_FORMS": "0",
                "urzadzenia-INITIAL_FORMS": "0",
                "attachments": [
                    SimpleUploadedFile(
                        "zdjecie.png",
                        b"test-image-content",
                        content_type="image/png",
                    ),
                    SimpleUploadedFile(
                        "raport.pdf",
                        b"%PDF-test-content",
                        content_type="application/pdf",
                    ),
                ],
            },
        )

        self.assertRedirects(response, reverse("protokol_add"))
        protocol = Protocol.objects.get(company=self.company)
        attachments = list(protocol.protokolimg.order_by("original_name"))
        self.assertEqual(len(attachments), 2)
        self.assertEqual(
            [(item.original_name, item.kind) for item in attachments],
            [
                ("raport.pdf", ProtokolImage.Kind.FILE),
                ("zdjecie.png", ProtokolImage.Kind.IMAGE),
            ],
        )
        for attachment in attachments:
            self.assertTrue(attachment.file.storage.exists(attachment.file.name))
            self.assertEqual(attachment.uploaded_by, self.user)
