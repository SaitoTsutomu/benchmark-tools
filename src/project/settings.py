import os
from ast import literal_eval
from pathlib import Path

from django.urls import reverse_lazy

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-l6et0%$5mdn3*&-ajw7l(6%iyp9rhw5q=hj5y918a-8$z*5gvp"  # noqa: S105

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = literal_eval(os.environ.get("DEBUG", "False"))
ALLOWED_HOSTS = ["127.0.0.1", os.environ.get("ALLOWED_HOST", "localhost")]


# Application definition

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "project.urls"
LOGOUT_REDIRECT_URL = "/admin/login/?next=/admin/core/result/"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {filename}:{lineno} {message}",
            "datefmt": "%d/%b/%Y %H:%M:%S",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "LiteLLM": {
            "level": "WARNING",
        },
    },
}


# Unfold

UNFOLD = {
    "SITE_TITLE": "Benchmark",
    "SITE_HEADER": "ベンチマークツール",
    "SIDEBAR": {
        "navigation": [
            {
                "title": "メニュー",
                "separator": True,
                "items": [
                    {
                        "title": "ダッシュボード",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": "LLMモデル",
                        "icon": "smart_toy",
                        "link": reverse_lazy("admin:core_llmmodel_changelist"),
                    },
                    {
                        "title": "テスト項目",
                        "icon": "quiz",
                        "link": reverse_lazy("admin:core_item_changelist"),
                    },
                    {
                        "title": "テストグループ",
                        "icon": "dataset",
                        "link": reverse_lazy("admin:core_group_changelist"),
                    },
                    {
                        "title": "テスト結果",
                        "icon": "bar_chart",
                        "link": reverse_lazy("admin:core_result_changelist"),
                    },
                ],
            }
        ],
    },
}
