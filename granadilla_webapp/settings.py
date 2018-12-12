"""
Django settings for granadilla_webapp project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

from __future__ import unicode_literals

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import getconf
import ldap
import django_auth_ldap.config as dal_config

BASE_DIR = os.path.dirname(__file__)
CHECKOUT_DIR = os.path.dirname(BASE_DIR)

config = getconf.ConfigGetter('granadilla',
    [
        '/etc/granadilla/settings.ini',
        os.path.join(CHECKOUT_DIR, 'local_settings.ini'),
    ],
)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/
env = config.getstr('env', 'dev')
assert env in ('dev', 'prod'), "Invalid environment %s" % env

# SECURITY WARNING: keep the secret key used in production secret!
if env == 'dev':
    _default_secret_key = 'Dev only!!'
else:
    _default_secret_key = ''

SECRET_KEY = config.getstr('django.secret_key', _default_secret_key)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config.getbool('dev.debug', env == 'dev')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        },
    },
]


ALLOWED_HOSTS = config.getlist('django.allowed_hosts')


# Application definition

INSTALLED_APPS = (
    'granadilla',
    'granadilla_webapp.web',
    'zxcvbn_password',
    'django_password_strength',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)

ROOT_URLCONF = 'granadilla_webapp.urls'

WSGI_APPLICATION = 'granadilla_webapp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': config.getstr('db.engine', 'django.db.backends.sqlite3'),
        'NAME': config.getstr('db.name', os.path.join(BASE_DIR, 'db.sqlite3')),
        'HOST': config.getstr('db.host'),
        'PORT': config.getstr('db.port'),
        'USER': config.getstr('db.user'),
        'PASSWORD': config.getstr('db.password'),
    },
    'ldap': {
        'ENGINE': 'ldapdb.backends.ldap',
        'NAME': config.getstr('ldap.server', 'ldaps://ldaps.example.org'),
        'USER': config.getstr('ldap.webapp_bind_dn', 'uid=test,dc=example,dc=org'),
        'PASSWORD': config.getstr('ldap.webapp_bind_pw'),
    },
}

AUTH_PASSWORD_VALIDATORS = [{
    'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
}, {
    'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
}, {
    'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
}, {
    'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
}, {
    'NAME': 'zxcvbn_password.ZXCVBNValidator',
    'OPTIONS': {
        'min_score': 3,
        'user_attributes': ('username', 'email', 'first_name', 'last_name')
    }
}]

DATABASE_ROUTERS = ['ldapdb.router.Router']

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


# LDAP

# Base DN for LDAP database.
GRANADILLA_BASE_DN = config.getstr('granadilla.base_dn', 'dc=example,dc=org')

# The organizationalUnit for groups
GRANADILLA_GROUPS_OU = config.getstr('granadilla.groups_ou', 'ou=groups')
GRANADILLA_GROUPS_DN = '%s,%s' % (GRANADILLA_GROUPS_OU, GRANADILLA_BASE_DN)
# The organizationalUnit for users
GRANADILLA_USERS_OU = config.getstr('granadilla.users_ou', 'ou=users')
GRANADILLA_USERS_DN = '%s,%s' % (GRANADILLA_USERS_OU, GRANADILLA_BASE_DN)
# The organizationalUnit for external users
GRANADILLA_EXTERNAL_USERS_OU = config.getstr('granadilla.external_users_ou', 'ou=external_users')
GRANADILLA_EXTERNAL_USERS_DN = '%s,%s' % (GRANADILLA_EXTERNAL_USERS_OU, GRANADILLA_BASE_DN)
# The organizationalUnit for devices
GRANADILLA_DEVICES_OU = config.getstr('granadilla.devices_ou', 'ou=external_users')
GRANADILLA_DEVICES_DN = '%s,%s' % (GRANADILLA_DEVICES_OU, GRANADILLA_BASE_DN)
GRANADILLA_DEVICEGROUPS_DN = GRANADILLA_DEVICES_DN

# The organizationalUnit for services
GRANADILLA_SERVICES_OU = config.getstr('granadilla.services_ou', 'ou=services')
GRANADILLA_SERVICES_DN = '%s,%s' % (GRANADILLA_SERVICES_OU, GRANADILLA_BASE_DN)
# The organizationalUnit for acls
GRANADILLA_ACLS_OU = config.getstr('granadilla.acls_ou', 'ou=acls')
GRANADILLA_ACLS_DN = '%s,%s' % (GRANADILLA_ACLS_OU, GRANADILLA_BASE_DN)
GRANADILLA_USE_ACLS = config.getbool('granadilla.use_acls', False)

# Domain to automatically generate e-mail addresses for new users.
GRANADILLA_MAIL_DOMAIN = config.getstr('granadilla.mail_domain', 'example.org')
# The home folder for user accounts
GRANADILLA_USERS_HOME = config.getstr('granadilla.users_home', '/home')
# The "base" group which is displayed in the index view.
GRANADILLA_USERS_GROUP = config.getstr('granadilla.users_group', 'test')
# The 'admin' groups
GRANADILLA_ADMIN_GROUPS = config.getlist('granadilla.admin_groups')

# Whether to use samba
GRANADILLA_USE_SAMBA = config.getbool('granadilla.use_samba', False)
# Samba SID prefix
GRANADILLA_SAMBA_PREFIX = config.getstr('granadilla.samba_prefix', 'S-1-0-0')

# URL from which Granadilla's static media are served.
GRANADILLA_MEDIA_PREFIX = os.path.join(STATIC_URL, 'granadilla')


AUTH_LDAP_SERVER_URI = DATABASES['ldap']['NAME']
AUTH_LDAP_BIND_DN = DATABASES['ldap']['USER']
AUTH_LDAP_BIND_PASSWORD = DATABASES['ldap']['PASSWORD']
AUTH_LDAP_USER_DN_TEMPLATE = 'uid=%(user)s,' + GRANADILLA_USERS_DN
# Populate Django from the LDAP
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail',
}
AUTH_LDAP_GROUP_SEARCH = dal_config.LDAPSearch(
    GRANADILLA_GROUPS_DN,
    ldap.SCOPE_SUBTREE,
    '(objectClass=posixGroup)',
)
AUTH_LDAP_GROUP_TYPE = dal_config.PosixGroupType()
AUTH_LDAP_MIRROR_GROUPS = True
