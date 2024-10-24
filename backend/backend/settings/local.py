from .base import *

if env.str('DB_ENGINE', None) is not None:
    DATABASES = {
        'default': {
            'ENGINE': env.str('DB_ENGINE'),
            'NAME': env.str('DB_NAME'),
            'USER': env.str('DB_USER'),
            'PASSWORD': env.str('DB_PASSWORD'),
            'HOST': env.str('DB_HOST'),
            'PORT': env.str('DB_PORT'),
        }
    }
elif DATABASES is None:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

if DEBUG:
    INSTALLED_APPS += ('debug_toolbar',)
    MIDDLEWARE += 'debug_toolbar.middleware.DebugToolbarMiddleware',
    INTERNAL_IPS = [
        "127.0.0.1",
    ]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True

# if DEBUG:
#     INSTALLED_APPS.append("django_browser_reload")
#     MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")

ALLOWED_HOSTS = ["*"]