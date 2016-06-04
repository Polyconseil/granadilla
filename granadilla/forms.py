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


class LdapDeviceForm(forms.Form):

    name = forms.CharField(label=_("Name (e.g 'laptop')"), max_length=42)

    def __init__(self, target_user, instance=None, *args, **kwargs):
        self.target_user = target_user
        assert instance is None
        super(LdapDeviceForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name']
        login = '%s_%s' % (self.target_user.username, name)

        if models.LdapDevice.objects.filter(login=login).exists():
            raise forms.ValidationError(_("A device with name %s already exists") % name)

        return name

    def save(self, commit=True):
        # target_user might be a Django User object
        user = models.LdapUser.objects.get(username=self.target_user.username)
        name = self.data['name']
        login = '%s_%s' % (user.username, name)

        device = models.LdapDevice(
            owner_username=user.username,
            owner_dn=user.dn,
            login=login,
            name=name,
        )
        device.set_password()
        device.save()

        return device


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
