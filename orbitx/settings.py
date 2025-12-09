import os  
from datetime import timedelta 
from pathlib import Path
from decouple import config 

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "55105437938a2263e5f3ad940d123fbe6e756763@#orbitx"

DEBUG = False 

ALLOWED_HOSTS = ['api.orbitx.uk', 'www.api.orbitx.uk', 'localhost', '127.0.0.1']


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_extensions",
    "auditlog",
    "rest_framework",  
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",        
    "corsheaders",
    "ckeditor", 
    "ckeditor_uploader", 
    "backend", 
]



REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ), 
     'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10000/day',
        'user': '10000/day'
    },
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
  
}


GOOGLE_CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "credentials.json")

GOOGLE_SCOPES = [
        "https://www.googleapis.com/auth/userinfo.profile",  
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ]


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    'SLIDING_TOKEN_LIFETIME': timedelta(days=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME_LATE_USER': timedelta(days=1),
    'SLIDING_TOKEN_LIFETIME_LATE_USER': timedelta(days=30),
    'BLACKLIST_AFTER_ROTATION': True,
    'ROTATE_REFRESH_TOKENS': True,
}

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://orbitx.uk', 
    "https://www.orbitx.uk",
    'http://orbitx.uk', 
    "http://www.orbitx.uk",
    "https://www.orbitx.uk",
    "https://orbitx.design"

]

CORS_ALLOW_CREDENTIALS = True  

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://orbitx.uk', 
    "https://www.orbitx.uk",
    'http://orbitx.uk', 
    "http://www.orbitx.uk",
    "https://www.orbitx.uk",
    "https://orbitx.design"
]

ROOT_URLCONF = "orbitx.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "orbitx.wsgi.application"


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'orbitx_db',
        'USER': 'root',
        'PASSWORD': 'admin',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}



AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'


STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]

FIXTURE_DIRS = [
    os.path.join(BASE_DIR, 'fixtures')
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

CKEDITOR_UPLOAD_PATH = 'uploads/'


CKEDITOR_IMAGE_BACKEND = "pillow"

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': '100%',
        'extraAllowedContent': 'img[!src,alt,width,height];',
    }
}


# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = config('GMAIL_CLIENT_ID')
# EMAIL_HOST_PASSWORD = config('GMAIL_PASSWORD')
# DEFAULT_FROM_EMAIL = config('GMAIL_CLIENT_ID')

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "mail.privateemail.com"
EMAIL_PORT = 465                   
EMAIL_USE_SSL = True                
EMAIL_USE_TLS = False           
EMAIL_HOST_USER = 'hello@orbitx.design'
EMAIL_HOST_PASSWORD = 'orbitx!23'
DEFAULT_FROM_EMAIL = 'hello@orbitx.design'