"""Django settings for config project."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

_env_path = BASE_DIR / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

SECRET_KEY = os.getenv(
    'SECRET_KEY',
    os.getenv(
        'DJANGO_SECRET_KEY',
        'django-insecure-d2)t)!5o6$^ovl%z7oa#m&ff3#a6%l-$bxh1#v5bwb#o^(iz%6',
    ),
)

# Platform detection (Render sets RENDER and RENDER_EXTERNAL_HOSTNAME automatically)
_on_render = bool(os.getenv('RENDER') or os.getenv('RENDER_EXTERNAL_HOSTNAME'))
_render_host = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
_on_railway = bool(os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID'))
_on_hf = bool(os.getenv('SPACE_ID') or os.getenv('SPACE_HOST'))
_hf_host = os.getenv('SPACE_HOST', '').strip()

_debug_raw = os.getenv('DEBUG', os.getenv('DJANGO_DEBUG', '')).strip().lower()
if _debug_raw in ('true', '1', 'yes'):
    DEBUG = True
elif _debug_raw in ('false', '0', 'no'):
    DEBUG = False
else:
    # Production (Render / Railway / Hugging Face) -> False, local development -> True
    DEBUG = not (_on_render or _on_railway or _on_hf)

_allowed_hosts_env = os.getenv('ALLOWED_HOSTS', os.getenv('DJANGO_ALLOWED_HOSTS', '')).strip()
if _allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']

for _domain in ['.onrender.com', '.railway.app', '.up.railway.app', '.hf.space']:
    if _domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_domain)

if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

_railway_public_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN', '').strip()
if _railway_public_domain and _railway_public_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_public_domain)

if _hf_host and _hf_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_hf_host)

# Behind the Render / Hugging Face / Railway proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'rag',
]

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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'


MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

_cors_env = os.getenv('CORS_ALLOWED_ORIGINS', '').strip()
if _cors_env:
    CORS_ALLOWED_ORIGINS = list(dict.fromkeys(
        _default_origins + [o.strip().rstrip('/') for o in _cors_env.split(',') if o.strip()]
    ))
else:
    CORS_ALLOWED_ORIGINS = _default_origins

_csrf_env = os.getenv('CSRF_TRUSTED_ORIGINS', '').strip()
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(
        _default_origins + [o.strip().rstrip('/') for o in _csrf_env.split(',') if o.strip()]
    ))
elif _cors_env:
    CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
else:
    CSRF_TRUSTED_ORIGINS = list(_default_origins)

if _hf_host:
    _hf_origin = f"https://{_hf_host}"
    if _hf_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_hf_origin)

if _render_host:
    _render_origin = f"https://{_render_host}"
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}