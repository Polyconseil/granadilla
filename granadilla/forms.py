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

from . import models
from django import forms
from django.utils.translation import gettext_lazy as _

from zxcvbn_password.fields import PasswordField, PasswordConfirmationField


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


class LdapUserPassForm(forms.Form):
    current_pass = forms.CharField(label='Current password', max_length=150, widget=forms.PasswordInput())
    new_pass_1 = PasswordField()
    new_pass_2 = PasswordConfirmationField(confirm_with='new_pass_1')

    def clean(self):
        cleaned_data = super(LdapUserPassForm, self).clean()
        new_pass_1 = cleaned_data.get("new_pass_1")
        if new_pass_1 is not None:
            if not self.user.check_password(self.cleaned_data['current_pass']):
                raise forms.ValidationError("Invalid Password!")
        check = models.check_password_strength(
            new_pass_1,
            [self.user.username, self.user.first_name, self.user.last_name],
        )
        if not check.good:
            raise forms.ValidationError(str(check.message))
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data['new_pass_2'])
        self.user.save()
        return self.user

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
