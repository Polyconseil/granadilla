"""
Django settings for granadilla-admin project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

from __future__ import unicode_literals

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import getconf
import os
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
env = config.get('env', 'dev')
assert env in ('dev', 'prod'), "Invalid environment %s" % env

# SECURITY WARNING: keep the secret key used in production secret!
if env == 'dev':
    _default_secret_key = 'Dev only!!'
else:
    _default_secret_key = ''

SECRET_KEY = config.get('django.secret_key', _default_secret_key)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config.getbool('dev.debug', env == 'dev')

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = config.getlist('django.allowed_hosts')


# Application definition

INSTALLED_APPS = (
    'granadilla',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = None

WSGI_APPLICATION = None


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': config.get('db.engine', 'django.db.backends.sqlite3'),
        'NAME': config.get('db.name', os.path.join(BASE_DIR, 'db.sqlite3')),
        'HOST': config.get('db.host'),
        'PORT': config.get('db.port'),
        'USER': config.get('db.user'),
        'PASSWORD': config.get('db.password'),
    }
}

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
LDAPDB_BIND_DN = config.get('ldap.cli_bind_dn', 'uid=test,dc=example,dc=org')
LDAPDB_BIND_PASSWORD = config.get('ldap.cli_bind_pw')
LDAPDB_SERVER_URI = config.get('ldap.server', 'ldaps://ldaps.example.org')

# Base DN for LDAP database.
GRANADILLA_BASE_DN = config.get('granadilla.base_dn', 'dc=example,dc=org')

# The organizationalUnit for groups
GRANADILLA_GROUPS_OU = config.get('granadilla.groups_ou', 'ou=groups')
GRANADILLA_GROUPS_DN = '%s,%s' % (GRANADILLA_GROUPS_OU, GRANADILLA_BASE_DN)
# The organizationalUnit for users
GRANADILLA_USERS_OU = config.get('granadilla.users_ou', 'ou=users')
GRANADILLA_USERS_DN = '%s,%s' % (GRANADILLA_USERS_OU, GRANADILLA_BASE_DN)
# The organizationalUnit for external users
GRANADILLA_EXTERNAL_USERS_OU = config.get('granadilla.external_users_ou', 'ou=external_users')
GRANADILLA_EXTERNAL_USERS_DN = '%s,%s' % (GRANADILLA_EXTERNAL_USERS_OU, GRANADILLA_BASE_DN)
# The organizationalUnit for devices
GRANADILLA_DEVICES_OU = config.get('granadilla.devices', 'ou=devices')
GRANADILLA_DEVICES_DN = '%s,%s' % (GRANADILLA_DEVICES_OU, GRANADILLA_BASE_DN)
GRANADILLA_DEVICEGROUPS_DN = GRANADILLA_DEVICES_DN

# The organizationalUnit for services
GRANADILLA_SERVICES_OU = config.get('granadilla.services_ou', 'ou=services')
GRANADILLA_SERVICES_DN = '%s,%s' % (GRANADILLA_SERVICES_OU, GRANADILLA_BASE_DN)
# The organizationalUnit for acls
GRANADILLA_ACLS_OU = config.get('granadilla.acls_ou', 'ou=acls')
GRANADILLA_ACLS_DN = '%s,%s' % (GRANADILLA_ACLS_OU, GRANADILLA_BASE_DN)
GRANADILLA_USE_ACLS = config.getbool('granadilla.use_acls', False)

# Domain to automatically generate e-mail addresses for new users.
GRANADILLA_MAIL_DOMAIN = config.get('granadilla.mail_domain', 'example.org')
# The home folder for user accounts
GRANADILLA_USERS_HOME = config.get('granadilla.users_home', '/home')
# The "base" group which is displayed in the index view.
GRANADILLA_USERS_GROUP = config.get('granadilla.users_group', 'test')
# The 'admin' groups
GRANADILLA_ADMIN_GROUPS = config.getlist('granadilla.admin_groups')

# Whether to use samba
GRANADILLA_USE_SAMBA = config.getbool('granadilla.use_samba', False)
# Samba SID prefix
GRANADILLA_SAMBA_PREFIX = config.get('granadilla.samba_prefix', 'S-1-0-0')

# URL from which Granadilla's static media are served.
GRANADILLA_MEDIA_PREFIX = STATIC_URL
