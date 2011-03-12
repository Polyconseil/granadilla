# -*- coding: utf-8 -*-
# 
# django-granadilla
# Copyright (C) 2009-2011 Bolloré telecom
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

from django.contrib import admin
from granadilla.models import LdapAcl, LdapGroup, LdapUser, ACLS_DN, USERS_SAMBA

class LdapAclAdmin(admin.ModelAdmin):
    exclude = ['dn', 'members']

class LdapGroupAdmin(admin.ModelAdmin):
    exclude = ['dn', 'usernames']
    list_display = ['name', 'gid']
    search_fields = ['name']

class LdapUserAdmin(admin.ModelAdmin):
    exclude = ['dn', 'password', 'photo']
    if USERS_SAMBA:
        exclude += ['samba_ntpassword', 'samba_lmpassword', 'samba_pwdlastset']
    list_display = ['username', 'first_name', 'last_name', 'email', 'uid']
    search_fields = ['first_name', 'last_name', 'full_name', 'username']

if ACLS_DN:
    admin.site.register(LdapAcl, LdapAclAdmin)
admin.site.register(LdapGroup, LdapGroupAdmin)
admin.site.register(LdapUser, LdapUserAdmin)
