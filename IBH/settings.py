"""
Django settings for IBH project.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import tempfile
from pathlib import Path
import os
# import wfastcgi


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-x0t)8qx9buoxxbiq#v4hmxdqt&$e(t%#c0=5jj$rthyb1!042@'

# SECURITY WARNING: don't run with debug turned on in production!
# Change it to True while Developing, to load your static files
DEBUG = True


CSRF_TRUSTED_ORIGINS = [
    'https://genie-production-production.up.railway.app',
    'http://127.0.0.1:8000',  # Keep localhost for development
]

ALLOWED_HOSTS = [
    'genie-production-production.up.railway.app',
    '127.0.0.1',
    'localhost',
]


# Application definition

INSTALLED_APPS = [
    # 'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
    'administrator',
    'operations_team_leader',
    'leads',
    'sales_manager',
    'operations_manager',
    'sales',
    'api',
    'ai_agent',
    "rest_framework",
    # "debug_toolbar",
    # 'widget_tweaks',
]

# # for debug_toolbar
# INTERNAL_IPS = [
#     "127.0.0.1",
# ]

ASGI_APPLICATION = 'IBH.asgi.application'

# Session will expire when the browser is closed
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


CHANNEL_LAYERS = {
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
}

TIME_ZONE = 'Africa/Cairo'
USE_TZ = True


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # "debug_toolbar.middleware.DebugToolbarMiddleware",
]



ROOT_URLCONF = 'IBH.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'main.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'IBH.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'railway',
        'USER': 'root',
        'PASSWORD': 'QcieGmwVSuAnLuXBRLKpImOJhKIWSEjR',  # MySQL server pass is 'admin@ibh'
        'HOST': 'mysql.railway.internal',  # or the IP address of your MySQL server '192.168.0.200'
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 60,
        }},

    'railway': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'railway',
        'USER': 'root',
        'PASSWORD': 'KeImhTyLXCUfJUdIFZHEbdAzoDrMswHU',
        'HOST': 'tramway.proxy.rlwy.net',
        'PORT': '38352',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 60,
        },
    }
}

DATABASE_ROUTERS = ['IBH.database_router.AppBasedRouter']


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'UTC'
USE_I18N = True

# USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_URL = '/static/'  # URL to access static files

# Where static files will be collected for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Add any extra locations for static files during development
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),  # Do not include STATIC_ROOT here
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module}.py {name} process:{process:d} thread:{thread:d} line:{lineno} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(tempfile.gettempdir(), 'general.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # Log all activities from your apps
        '': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        # Add other apps here as needed
    },
}

LOGIN_URL='/login'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')