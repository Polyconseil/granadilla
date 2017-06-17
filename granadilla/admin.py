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

from django.contrib import admin

from .conf import settings
from . import models


class LdapAclAdmin(admin.ModelAdmin):
    exclude = ['dn', 'members']


if settings.GRANADILLA_USE_ACLS:
    admin.site.register(models.LdapAcl, LdapAclAdmin)


class LdapGroupAdmin(admin.ModelAdmin):
    exclude = ['dn', 'usernames']
    list_display = ['name', 'gid']
    search_fields = ['name']


admin.site.register(models.LdapGroup, LdapGroupAdmin)


class LdapUserAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'full_name'),
        }),
        ('Posix account', {
            'fields': ('username', 'uid', 'group', 'gecos', 'home_directory', 'login_shell')
        }),
        ('Personal info', {
            'classes': ('collapse',),
            'fields': ('email', 'phone', 'mobile_phone', 'internal_phone'),
        }),
    )
    list_display = ['username', 'first_name', 'last_name', 'email', 'uid']
    search_fields = ['first_name', 'last_name', 'full_name', 'username']


admin.site.register(models.LdapUser, LdapUserAdmin)


class LdapServiceAccountAdmin(admin.ModelAdmin):
    exclude = ['dn']
    list_display = ['username', 'first_name', 'last_name', 'description']
    search_fields = list_display


admin.site.register(models.LdapServiceAccount, LdapServiceAccountAdmin)


class LdapDeviceAdmin(admin.ModelAdmin):
    exclude = ['dn']
    list_display = ['login', 'name', 'owner_dn']
    search_fields = list_display


admin.site.register(models.LdapDevice, LdapDeviceAdmin)
