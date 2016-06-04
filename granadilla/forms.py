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

from __future__ import unicode_literals
import re

from . import models
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import ugettext as _


class LdapDeviceForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        if 'base_dn' in kwargs:
            self._base_dn = kwargs.pop('base_dn')
        else:
            self._base_dn = None

        self._username = kwargs.pop('username')
        self.tmppwd = kwargs.pop('tmppwd')

        super(LdapDeviceForm, self).__init__(*args, **kwargs)

    def is_valid(self):
        if super(LdapDeviceForm, self).is_valid():    
            # Check if the device already exists
            login = self._username + '_' + self.data['name']
            try:
                if models.LdapDevice.objects.get(login=login):
                    self.errors['devicenameerror'] = "A device with \
                            this name already exists"
                    return False
            except models.LdapDevice.DoesNotExist:
                return True
        return False

    def save(self, commit=True):
        device = super(LdapDeviceForm, self).save(False)

        device.owner_username = self._username
        user = models.LdapUser.objects.get(username=device.owner_username)
        device.owner_dn = user.dn
        device.login = device.owner_username + '_' + self.data['name']

        # Initialize with random password because the field is necessary
        device.set_password(self.tmppwd)
        self.tmppwd = ""

        if self._base_dn:
            device.base_dn = self._base_dn
        if commit:
            device.save()
        return device

    class Meta:
        model = models.LdapDevice
        exclude = ("password", "dn", "owner_username", "owner_dn", "login")


class LdapUserForm(forms.ModelForm):
    new_photo = forms.ImageField(required=False, label=_("Photo"))

    def save(self, commit=True):
        contact = super(LdapUserForm, self).save(False)
        photo = self.cleaned_data['new_photo']
        if hasattr(photo, 'read'):
            contact.photo = photo.read()
        if commit:
            contact.save()
        return contact

    class Meta:
        model = models.LdapUser
        fields = ('phone', 'mobile_phone', 'internal_phone', 'new_photo')
