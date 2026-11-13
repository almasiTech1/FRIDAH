"""
FRIDAH - Kenya PropTech Super App
Django settings (production-ready, env-driven)
"""
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)

# Refuse to start in production with a guessable key (it signs every login token).
from config.security import validate_secret_key  # noqa: E402
validate_secret_key(SECRET_KEY, DEBUG)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,api.fridah.co.ke', cast=Csv())

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_celery_beat',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.users',
    'apps.properties',
    'apps.rentals',
    'apps.bookings',
    'apps.services',
    'apps.payments',
    'apps.notifications',
    'apps.analytics',
    'apps.ussd',
    'apps.ai',
    'apps.visitors',
    'apps.fraud',
    'apps.agencies',
    'apps.audit',
    'apps.tax',
    'apps.search',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'common.middleware.AdminIPAllowlistMiddleware',
    'apps.users.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = 'config.urls'

# The Django admin site. /admin/ is the first address attackers try, so in production set ADMIN_URL to something
# unguessable (for example "ops-7f3k2x9q/") and, if you have a fixed office or VPN address, ADMIN_ALLOWED_IPS.
ADMIN_URL = config('ADMIN_URL', default='admin/').strip('/') + '/'
ADMIN_ALLOWED_IPS = config('ADMIN_ALLOWED_IPS', default='', cast=Csv())

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

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
if config('USE_SQLITE', default=False, cast=bool):
    # Local dev / CI convenience only — production always uses Postgres above.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='fridah'),
            'USER': config('DB_USER', default='fridah'),
            'PASSWORD': config('DB_PASSWORD', default='fridah'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
        }
    }

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalization (Kenya)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'

# Reminders (SMS/push) are held back during these local hours unless the user sets their own window.
# Set to None to disable the platform default.
NOTIFICATION_DEFAULT_QUIET_HOURS = ('21:00', '07:00')
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# How long a signed link to a private file (ID scan, agreement, receipt...) stays valid, in seconds.
PRIVATE_FILE_URL_TTL = config('PRIVATE_FILE_URL_TTL', default=300, cast=int)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
# Reverse proxies in front of Django: 1 = nginx only, 2 = Cloudflare in front of nginx, 0 = none.
# ONE setting drives both the API rate limits and the M-Pesa callback IP check.
TRUSTED_PROXY_COUNT = config('TRUSTED_PROXY_COUNT', default=1, cast=int)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.users.authentication.FridahJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': (
        # Baseline blanket protection for every endpoint (most views never declare
        # a throttle_scope, and ScopedRateThrottle silently does nothing without
        # one — these two catch everything else). Using the "Safe" wrappers so a
        # cache/Redis outage degrades rate limiting instead of 500ing the entire API.
        'apps.users.throttling.SafeAnonRateThrottle',
        'apps.users.throttling.SafeUserRateThrottle',
        'apps.users.throttling.SafeScopedRateThrottle',
    ),
    # Same value the M-Pesa callback check uses (TRUSTED_PROXY_COUNT), so rate limits and payment checks can never disagree
    # about who the real client is. Without it DRF would trust the caller's own X-Forwarded-For header.
    'NUM_PROXIES': TRUSTED_PROXY_COUNT,
    'DEFAULT_THROTTLE_RATES': {
        # Overridable per environment (e.g. raise them on a staging server before a load test).
        # A single page view makes several API calls and many mobile users share one carrier address, so 100/hour
        # locked out real visitors. Brute-force protection comes from the strict login/otp limits below, not from this.
        'anon': config('THROTTLE_ANON', default='600/hour'),
        'user': config('THROTTLE_USER', default='1000/hour'),
        'otp': config('THROTTLE_OTP', default='5/min'),
        'login': config('THROTTLE_LOGIN', default='10/min'),
        'mpesa': config('THROTTLE_MPESA', default='20/min'),
    },
    'EXCEPTION_HANDLER': 'apps.users.exceptions.custom_exception_handler',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'FRIDAH API',
    'DESCRIPTION': 'Kenya PropTech Super App — Tenant, Landlord, Admin, Service Provider, Hotel/BnB portals',
    'VERSION': 'v1',
    'SERVE_PUBLIC': False,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,https://fridah.co.ke,https://www.fridah.co.ke',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://api.fridah.co.ke,https://fridah.co.ke',
    cast=Csv()
)

# ---------------------------------------------------------------------------
# Celery / Redis
# ---------------------------------------------------------------------------
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

CELERY_BEAT_SCHEDULE = {
    'generate-monthly-rent-invoices': {
        'task': 'apps.payments.tasks.generate_monthly_rent_invoices',
        'schedule': config('CRON_MONTHLY_INVOICES', default=86400, cast=int),  # checked daily; task is idempotent per period
    },
    'apply-late-payment-penalties': {
        'task': 'apps.payments.tasks.apply_late_payment_penalties',
        'schedule': 86400,  # once daily
    },
    'send-payment-reminders': {
        'task': 'apps.payments.tasks.send_payment_reminders',
        'schedule': 3600,  # hourly: reminders held during quiet hours go out as soon as the window ends; de-duplicated
    },
    'daily-payment-reconciliation': {
        'task': 'apps.payments.tasks.run_daily_reconciliation',
        'schedule': 86400,
    },
    'retry-failed-notification-deliveries': {
        'task': 'apps.notifications.tasks.retry_failed_deliveries',
        'schedule': 1800,
    },
    'check-lease-renewals': {
        'task': 'apps.rentals.tasks.check_lease_renewals',
        'schedule': 86400,  # once daily
    },
    'expire-stale-lease-renewals': {
        'task': 'apps.rentals.tasks.expire_stale_lease_renewals',
        'schedule': 86400,  # once daily
    },
    'recalculate-tenant-risk-scores': {
        'task': 'apps.analytics.tasks.recalculate_tenant_risk_scores_task',
        'schedule': 86400,  # once daily, overnight batch job
    },
    'generate-flat-fee-utility-invoices': {
        'task': 'apps.rentals.tasks.generate_flat_fee_utility_invoices_task',
        'schedule': 86400,  # once daily (task itself is idempotent per calendar month)
    },
    'generate-scheduled-owner-statements': {
        'task': 'apps.agencies.tasks.generate_scheduled_owner_statements',
        'schedule': 86400,  # daily; idempotent per period (monthly always, annual during January)
    },
    'generate-amenity-invoices': {
        'task': 'apps.rentals.tasks.generate_amenity_invoices_task',
        'schedule': 86400,  # daily; idempotent per charge/lease/month
    },
    'run-fraud-detection': {
        'task': 'apps.fraud.tasks.run_fraud_detection_task',
        'schedule': 86400,  # nightly sweep
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# ---------------------------------------------------------------------------
# M-Pesa Daraja 2.0
# ---------------------------------------------------------------------------
# Number of reverse proxies in front of the app (nginx, load balancer, CDN...). Used to find the real
# caller IP in X-Forwarded-For for the M-Pesa callback allowlist. Set 0 if the app is exposed directly.
# Refund policy (see apps/payments/refunds.py). Amounts in KES.
REFUND_ADMIN_APPROVAL_ABOVE = config('REFUND_ADMIN_APPROVAL_ABOVE', default=5000, cast=float)
REFUND_WINDOW_DAYS = config('REFUND_WINDOW_DAYS', default=180, cast=int)
# Send approved refunds to customers automatically via M-Pesa B2C (spends the business float; leave off until finance agrees).
MPESA_B2C_REFUNDS_ENABLED = config('MPESA_B2C_REFUNDS_ENABLED', default=False, cast=bool)
REFUND_ALLOW_SELF_APPROVAL = config('REFUND_ALLOW_SELF_APPROVAL', default=False, cast=bool)
MPESA_ENV = config('MPESA_ENV', default='sandbox')  # sandbox | production
MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='')
MPESA_SHORTCODE = config('MPESA_SHORTCODE', default='174379')
MPESA_PASSKEY = config('MPESA_PASSKEY', default='')
MPESA_INITIATOR_NAME = config('MPESA_INITIATOR_NAME', default='')
MPESA_INITIATOR_PASSWORD = config('MPESA_INITIATOR_PASSWORD', default='')
MPESA_CALLBACK_BASE_URL = config('MPESA_CALLBACK_BASE_URL', default='https://api.fridah.co.ke')
MPESA_BASE_URL = (
    'https://sandbox.safaricom.co.ke' if MPESA_ENV == 'sandbox'
    else 'https://api.safaricom.co.ke'
)
MPESA_ALLOWED_IPS = config(
    'MPESA_ALLOWED_IPS',
    default='196.201.214.200,196.201.214.206,196.201.213.114,196.201.214.207,196.201.214.208,196.201.213.44,196.201.212.127,196.201.212.138,196.201.212.129,196.201.212.136,196.201.212.74,196.201.212.69',
    cast=Csv()
)

# ---------------------------------------------------------------------------
# Africa's Talking SMS
# ---------------------------------------------------------------------------
AT_USERNAME = config('AT_USERNAME', default='sandbox')
AT_API_KEY = config('AT_API_KEY', default='')
AT_SENDER_ID = config('AT_SENDER_ID', default='FRIDAH')

# --- WhatsApp Cloud API (Meta) ---
WHATSAPP_ACCESS_TOKEN = config('WHATSAPP_ACCESS_TOKEN', default='')
WHATSAPP_PHONE_NUMBER_ID = config('WHATSAPP_PHONE_NUMBER_ID', default='')
WHATSAPP_VERIFY_TOKEN = config('WHATSAPP_VERIFY_TOKEN', default='fridah-verify-token')
WHATSAPP_APP_SECRET = config('WHATSAPP_APP_SECRET', default='')  # used to verify X-Hub-Signature-256
USSD_SHARED_SECRET = config('USSD_SHARED_SECRET', default='')  # append ?secret=... to the AT callback URL

# --- Africa's Talking USSD ---
USSD_SERVICE_CODE = config('USSD_SERVICE_CODE', default='*483*XXX#')

# --- Anthropic (AI features: property assistant, rent estimator, listing generator, maintenance triage) ---
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
AI_MODEL_FAST = config('AI_MODEL_FAST', default='claude-haiku-4-5-20251001')     # query parsing, triage classification
AI_MODEL_QUALITY = config('AI_MODEL_QUALITY', default='claude-sonnet-5')        # listing copywriting, match explanations

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.sendgrid.net')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='apikey')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@fridah.co.ke')

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'fridah.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
        'apps.payments': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
        'celery': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
}

# ---------------------------------------------------------------------------
# Security (production)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# FRIDAH custom settings
# ---------------------------------------------------------------------------
OTP_EXPIRY_MINUTES = config('OTP_EXPIRY_MINUTES', default=10, cast=int)
KYC_DOCUMENT_MAX_SIZE_MB = 5
FRONTEND_URL = config('FRONTEND_URL', default='https://fridah.co.ke')
PLATFORM_COMMISSION_PERCENT = config('PLATFORM_COMMISSION_PERCENT', default=5.0, cast=float)
LATE_PAYMENT_GRACE_DAYS = config('LATE_PAYMENT_GRACE_DAYS', default=5, cast=int)
LATE_PAYMENT_PENALTY_PERCENT = config('LATE_PAYMENT_PENALTY_PERCENT', default=2.0, cast=float)

KENYA_COUNTIES = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita-Taveta",
    "Garissa", "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru",
    "Tharaka-Nithi", "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua",
    "Nyeri", "Kirinyaga", "Murang'a", "Kiambu", "Turkana", "West Pokot",
    "Samburu", "Trans Nzoia", "Uasin Gishu", "Elgeyo-Marakwet", "Nandi",
    "Baringo", "Laikipia", "Nakuru", "Narok", "Kajiado", "Kericho",
    "Bomet", "Kakamega", "Vihiga", "Bungoma", "Busia", "Siaya", "Kisumu",
    "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi"
]
