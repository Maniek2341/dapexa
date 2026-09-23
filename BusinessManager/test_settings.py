"""Isolated test settings; never connect to the deployment database or services."""
import atexit
from tempfile import TemporaryDirectory

from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
_test_media = TemporaryDirectory(prefix="dapexa-test-media-")
atexit.register(_test_media.cleanup)
MEDIA_ROOT = _test_media.name
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
STRIPE_SECRET_KEY = ""
STRIPE_WEBHOOK_SECRET = ""
GOOGLE_API_KEY = ""
ORS_API_KEY = ""
