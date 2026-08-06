from .base import *

SECRET_KEY = "CHANGE_ME"

DEBUG = False

ALLOWED_HOSTS = [
    "your-domain.com",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "esg360",
        "USER": "postgres",
        "PASSWORD": "",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

CORS_ALLOWED_ORIGINS = [
    "https://your-frontend-domain.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://your-frontend-domain.com",
]