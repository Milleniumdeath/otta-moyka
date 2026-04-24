"""
AutoMoyka Django Settings
"""

from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ===========================================================
# XAVFSIZLIK
# ===========================================================
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# ===========================================================
# ILOVALAR
# ===========================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Uchinchi tomon
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'rest_framework',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',
    'channels',

    # Loyiha ilovalari
    'accounts',
    'core',
    'owner',
    'worker',
    'customer',
    'finance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    # Sessiya timeout middleware (10 daqiqa)
    'accounts.middleware.SessionTimeoutMiddleware',
]

ROOT_URLCONF = 'automoyka.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'automoyka.wsgi.application'
ASGI_APPLICATION = 'automoyka.asgi.application'

# ===========================================================
# MA'LUMOTLAR BAZASI
# ===========================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
    # PostgreSQL (production uchun):
    # 'default': {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': config('DB_NAME'),
    #     'USER': config('DB_USER'),
    #     'PASSWORD': config('DB_PASSWORD'),
    #     'HOST': config('DB_HOST', default='localhost'),
    #     'PORT': config('DB_PORT', default='5432'),
    # }
}

# ===========================================================
# AUTENTIFIKATSIYA
# ===========================================================
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# 2. SOCIALACCOUNT_PROVIDERS — faqat shu qolsin (ortiqchasini olib tashlang)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# Django Allauth sozlamalari


ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'   # hozircha 'none', keyinroq 'mandatory'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_SESSION_REMEMBER = True



LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/accounts/redirect/'
LOGOUT_REDIRECT_URL = '/'

# ===========================================================
# SESSIYA SOZLAMALARI (10 daqiqa timeout)
# ===========================================================
SESSION_COOKIE_AGE = 600  # 10 daqiqa (soniyalarda)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ===========================================================
# EMAIL SOZLAMALARI
# ===========================================================
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@automoyka.uz')

# ===========================================================
# STATIC VA MEDIA FAYLLAR
# ===========================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===========================================================
# REDIS VA CELERY (async vazifalar)
# ===========================================================
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ===========================================================
# CHANNELS (WebSocket)
# ===========================================================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# ===========================================================
# REST FRAMEWORK
# ===========================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ===========================================================
# CRISPY FORMS
# ===========================================================
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ===========================================================
# PAROL TEKSHIRUVI
# ===========================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===========================================================
# TIL VA VAQT MINTAQASI
# ===========================================================
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===========================================================
# LOYIHA SOZLAMALARI
# ===========================================================
# 6 xonali tasdiqlash kodi muddati (daqiqalarda)
VERIFICATION_CODE_EXPIRE_MINUTES = 10

# Sodiqlik tizimi
LOYALTY_TOKENS_PER_ORDER = 10  # Har bir muvaffaqiyatli buyurtma uchun
LOYALTY_FULL_PERCENTAGE = 10   # 100% uchun kerakli buyurtmalar soni

# Google email va oddiy email bir xil bo'lsa avtomatik ulanadi.
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

