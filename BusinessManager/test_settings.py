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
STRIPE_PRICE_IDS = {
    "start": {
        "monthly": "price_1SYlwN2cLveabukasUB1Gfp5",
        "yearly": "price_1SYlwe2cLveabukaBBljR9VM",
    },
    "standard": {
        "monthly": "price_1SYlxI2cLveabukamOy0egY7",
        "yearly": "price_1SYlxR2cLveabuka2atcyWd7",
    },
    "pro": {
        "monthly": "price_1SYlxl2cLveabuka76AEloE3",
        "yearly": "price_1SYlxw2cLveabukaJvYLRrp8",
    },
}
STRIPE_PLAN_PRICE_AMOUNTS = {
    "start": {"monthly": 10000, "yearly": 70000},
    "standard": {"monthly": 20000, "yearly": 150000},
    "pro": {"monthly": 40000, "yearly": 500000},
}
GOOGLE_API_KEY = ""
ORS_API_KEY = ""

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
