import os

import environ
from django.contrib.messages import constants as message_constants
from .jazzmin_admin import JAZZMIN_SETTINGS

root = environ.Path(__file__) - 3
BASE_DIR = root()
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

DEBUG = env.bool('DEBUG', True)
SECRET_KEY = env.str('SECRET_KEY', None)
USE_HTTPS = env.bool('USE_HTTPS', False)
FACEAPI_URL = env.str('FACEAPI_URL')

INSTALLED_APPS = [
    'apps.admin_dashboard',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django.contrib.sites',
    'corsheaders',
    'rest_framework',
    "drf_standardized_errors",
    'django_filters',
    'apps.users.apps.UserConfig',
    'apps.quizzes.apps.QuizzesConfig',
    'crispy_forms',
    'crispy_bootstrap4',
    'apps.user_face_id'
]

LANGUAGE_CODE = 'ru'

LANGUAGES = (
    ('en', 'English'),
    ('ru', 'Russian'),
)
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Ensure message tags are defined
MESSAGE_TAGS = {
    message_constants.DEBUG: 'debug',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            "builtins": ["apps.quizzes.templatetags.customtags"],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = None
# if env.str("DB_USER", None) is not None and env.str("DB_PASSWORD", None) is not None:
#     DATABASES = {
#         'default': {
#             'ENGINE': env.str('DB_ENGINE'),
#             'NAME': env.str('DB_NAME'),
#             'USER': env.str('DB_USER'),
#             'PASSWORD': env.str('DB_PASSWORD'),
#             'HOST': env.str('DB_HOST'),
#             'PORT': env.str('DB_PORT'),
#         }
#     }

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

public_root = root.path('public/')
MEDIA_ROOT = public_root('media')
MEDIA_URL = env.str('MEDIA_URL', default='media/')
STATIC_ROOT = public_root('static')
STATIC_URL = env.str('STATIC_URL', default='static/')

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = 'login'

SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
# AUTH_USER_MODEL = "users.CustomUser"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# REST_FRAMEWORK settings

REST_FRAMEWORK = {
    'DATETIME_FORMAT': "%m/%d/%Y %I:%M%P",
    # 'DEFAULT_AUTHENTICATION_CLASSES': [
    #     # 'rest_framework.authentication.SessionAuthentication',
    #     'rest_framework.authentication.TokenAuthentication',
    # ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    "EXCEPTION_HANDLER": "drf_standardized_errors.handler.exception_handler"
}
if USE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
