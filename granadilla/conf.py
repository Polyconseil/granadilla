# -*- coding: utf-8 -*-
# 
# django-granadilla
# Copyright (C) 2009-2012 Bolloré telecom
# See AUTHORS file for a full list of contributors.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import appconf

from django.conf import settings


class GranadillaConf(appconf.AppConf):
    """Default settings for granadilla.

    Override in settings.py.
    """

    class Meta:
        prefix = 'granadilla_ldap'
        required = ['base_dn']

    # LDAP root
    BASE_DN = 'dc=example,dc=org'

    # Specific organizationalUnit for some components
    ACLS_OU = 'ou=groupacls'
    CONTACTS_OU = 'ou=contacts'
    GROUPS_OU = 'ou=groups'
    SERVERS_OU = 'ou=servers'
    USERS_OU = 'ou=users'

    # Homepage: "full company" group name
    USERS_GROUP = 'all'

    # Account settings
    USERS_HOME = '/home'
    USERS_SHELL = '/bin/bash'

    # Samba
    USE_SAMBA = False
    SAMBA_PREFIX = 'S-1-0-0'
