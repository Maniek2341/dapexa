import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


class EncryptedTextField(models.TextField):
    """Encrypt values in PostgreSQL while exposing plaintext only in process."""

    prefix = "fernet$"

    @staticmethod
    def _cipher():
        secret = getattr(settings, "SUPPLIER_FEED_ENCRYPTION_KEY", "")
        if not secret:
            raise ImproperlyConfigured("Brak klucza szyfrowania URL-i feedów dostawców.")
        key = base64.urlsafe_b64encode(hashlib.sha256(str(secret).encode()).digest())
        return Fernet(key)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        if value.startswith(self.prefix):
            return value
        return self.prefix + self._cipher().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        value = super().to_python(value)
        if not value or not value.startswith(self.prefix):
            return value
        try:
            return self._cipher().decrypt(value[len(self.prefix):].encode()).decode()
        except InvalidToken as exc:
            raise ImproperlyConfigured(
                "Nie można odszyfrować URL-a feedu. Sprawdź SUPPLIER_FEED_ENCRYPTION_KEY."
            ) from exc
