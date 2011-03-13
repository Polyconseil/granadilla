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

import re

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import ugettext as _

from granadilla.models import LdapContact, LdapUser

class LdapContactForm(forms.ModelForm):
    postal_address = forms.CharField(required=False, label=_("Postal address"), widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        if 'base_dn' in kwargs:
            self.__base_dn = kwargs.pop('base_dn')
        else:
            self.__base_dn = None
        super(LdapContactForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        contact = super(LdapContactForm, self).save(False)
        if self.__base_dn:
            contact.base_dn = self.__base_dn
        if commit:
            contact.save()
        return contact

    class Meta:
        model = LdapContact
        exclude = ("dn", "photo", "full_name")

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
        model = LdapUser
        fields = ('phone', 'mobile_phone', 'internal_phone', 'new_photo')
