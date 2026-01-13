import tempfile
from pathlib import Path
import os
from django.contrib import messages
from dotenv import load_dotenv  # Added import for load_dotenv
# import dj_database_url  # Added import for dj_database_url
# import wfastcgi


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-x0t)8qx9buoxxbiq#v4hmxdqt&$e(t%#c0=5jj$rthyb1!042@'

# SECURITY WARNING: don't run with debug turned on in production!
# Change it to True while Developing, to load your static files
DEBUG = False


CSRF_TRUSTED_ORIGINS = [
    'https://genie-production-production.up.railway.app',
    "https://app-service-production-4990.up.railway.app",
    'https://genie-production-x8952.sevalla.app',
    'http://127.0.0.1:8000',  # Keep localhost for development
]

ALLOWED_HOSTS = [
    'genie-production-production.up.railway.app',
    "app-service-production-4990.up.railway.app",
    'genie-production-x8952.sevalla.app',
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
        'NAME': os.environ.get('MYSQL_DATABASE', "genie"),
        'USER': os.environ.get('MYSQLUSER', "root"),
        'PASSWORD': os.environ.get('MYSQLPASSWORD', "Admin123"),
        'HOST': os.environ.get('MYSQLHOST', "localhost"),
        'PORT': os.environ.get('MYSQLPORT', "3306"),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 60,
        }},

    'global': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MYSQL_DATABASE_global', "global"),
        'USER': os.environ.get('MYSQLUSER_global', "root"),
        'PASSWORD': os.environ.get('MYSQLPASSWORD_global', "Admin123"),
        'HOST': os.environ.get('MYSQLHOST_global', "localhost"),
        'PORT': os.environ.get('MYSQLPORT_global', "3306"),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 60,
        },
        }
}

DATABASE_ROUTERS = ['IBH.database_router.AppDatabaseRouter']


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
# Use an environment variable for MEDIA_ROOT in production, with a default for local dev
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))


MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}


# Gemini API Key
GEMINI_API_KEY = os.environ.get('google_api_key', 'mock_key_for_development')

External_REDIS_URL = os.environ.get('REDIS_URL', 'redis://default:riercOvPFfeeXIGpKsMnfpgPEDltqVjf@metro.proxy.rlwy.net:45042')

# Celery configuration tuned for stability under high load
CELERY_BROKER_URL = External_REDIS_URL
CELERY_RESULT_BACKEND = External_REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Cairo'

# Limit worker-side concurrency and prefetching to avoid overloading Redis and external APIs,
# but keep defaults high enough for good performance. Override via env vars as needed.
CELERYD_PREFETCH_MULTIPLIER = int(os.environ.get("CELERYD_PREFETCH_MULTIPLIER", "4"))
CELERY_WORKER_CONCURRENCY = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "6"))
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.environ.get("CELERY_WORKER_MAX_TASKS_PER_CHILD", "50"))

# Default task behaviour (can still be overridden per-task)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", str(60 * 5)))  # 15 minutes
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", str(60 * 8)))  # 20 minutes

# AI agent tuning: batch sizes and delays between external API calls
AI_AGENT_CHUNK_SIZE = int(os.environ.get("AI_AGENT_CHUNK_SIZE", "20"))
AI_AGENT_MAX_COMPANIES_PER_TASK = int(os.environ.get("AI_AGENT_MAX_COMPANIES_PER_TASK", "10000"))
AI_AGENT_BATCH_SLEEP_SECONDS = float(os.environ.get("AI_AGENT_BATCH_SLEEP_SECONDS", "1.0"))
AI_AGENT_RETRY_SLEEP_SECONDS = float(os.environ.get("AI_AGENT_RETRY_SLEEP_SECONDS", "1.0"))
