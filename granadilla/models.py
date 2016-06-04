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

import base64
try:
    import hashlib
    md5_constructor = hashlib.md5
except ImportError:
    import md5
    md5_constructor = md5.new

import logging
import os
import time
import random
import unicodedata

from .conf import settings
from django.utils.translation import ugettext_lazy as _

from ldapdb import models as ldap_models
from ldapdb.models import fields as ldap_fields


logger = logging.getLogger(__name__.split('.')[0])


def normalise(str):
    nkfd_form = unicodedata.normalize('NFKD', unicode(str))
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])


def hash_password(password):
    m = md5_constructor()
    m.update(password.encode('utf-8'))
    return "{MD5}" + base64.b64encode(m.digest())


def random_password(length=32):
    allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join([random.choice(allowed_chars) for i in range(length)])


class LdapAcl(ldap_models.Model):
    """
    Class for representing an LDAP ACL entry.
    """
    # LDAP meta-data
    base_dn = settings.GRANADILLA_ACLS_DN
    object_classes = ['groupOfNames']

    # groupOfNames
    name = ldap_fields.CharField(_("name"), db_column='cn', primary_key=True)
    members = ldap_fields.ListField(_("members"), db_column='member')

    def save(self):
        if not self.members:
            self.delete()
        else:
            super(LdapAcl, self).save()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = _("access control list")
        verbose_name_plural = _("access control lists")


class LdapGroup(ldap_models.Model):
    """
    Class for representing an LDAP group entry.
    """
    # LDAP meta-data
    base_dn = settings.GRANADILLA_GROUPS_DN
    object_classes = ['posixGroup']

    # posixGroup
    gid = ldap_fields.IntegerField(_("identifier"), db_column='gidNumber', unique=True)
    name = ldap_fields.CharField(_("name"), db_column='cn', primary_key=True)
    usernames = ldap_fields.ListField(_("usernames"), db_column='memberUid')

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = _("group")
        verbose_name_plural = _("groups")

    def get_members(self):
        return LdapUser.objects.filter(username__in=self.usernames)

    def save(self, *args, **kwargs):
        res = super(LdapGroup, self).save(*args, **kwargs)

        try:
            device_group = LdapDeviceGroup.objects.get(group_dn=self.dn)
        except LdapDeviceGroup.DoesNotExist:
            pass
        else:
            device_group.resync()

        return res


class LdapServiceAccount(ldap_models.Model):
    """Class for a Service account."""
    # LDAP meta-data
    base_dn = settings.GRANADILLA_SERVICES_DN
    object_classes = ['person', 'uidObject']

    username = ldap_fields.CharField(_("username"), db_column='uid', primary_key=True)
    first_name = ldap_fields.CharField(_("name (copy)"), db_column='sn', editable=False)
    last_name = ldap_fields.CharField(_("name (copy)"), db_column='cn', editable=False)
    password = ldap_fields.CharField(_("password"), db_column='userPassword')
    description = ldap_fields.CharField(_("description"), db_column='description')

    class Meta:
        verbose_name = _("service account")
        verbose_name_plural = _("service accounts")

    def __str__(self):
        return self.username

    def __unicode__(self):
        return self.username

    def set_password(self, password):
        self.password = hash_password(password)

    def save(self, *args, **kwargs):
        self.first_name = self.last_name = self.username
        super(LdapServiceAccount, self).save(*args, **kwargs)


class LdapUser(ldap_models.Model):
    """
    Class for representing an LDAP user entry.

    >>> q = LdapUser.objects.filter(username="foo")
    >>> q.query.where.as_sql()
    '(uid=foo)'

    >>> q = LdapUser.objects.filter(username__in=["foo", "bar"])
    >>> q.query.where.as_sql()
    '(|(uid=foo)(uid=bar))'
    """
    # LDAP meta-data
    base_dn = settings.GRANADILLA_USERS_DN
    object_classes = ['posixAccount', 'shadowAccount', 'inetOrgPerson']
    if settings.GRANADILLA_USE_SAMBA:
        object_classes.append('sambaSamAccount')

    # inetOrgPerson
    first_name = ldap_fields.CharField(_("first name"), db_column='givenName')
    last_name = ldap_fields.CharField(_("last name"), db_column='sn')
    full_name = ldap_fields.CharField(_("full name"), db_column='cn')
    email = ldap_fields.CharField(_("e-mail address"), db_column='mail', blank=True)
    phone = ldap_fields.CharField(_("phone"), db_column='telephoneNumber', blank=True)
    mobile_phone = ldap_fields.CharField(_("mobile phone"), db_column='mobile', blank=True)
    photo = ldap_fields.ImageField(_("photo"), db_column='jpegPhoto')

    # FIXME: this is a hack
    internal_phone = ldap_fields.CharField(_("internal phone"), db_column='roomNumber', blank=True)

    # posixAccount
    uid = ldap_fields.IntegerField(_("user id"), db_column='uidNumber', unique=True)
    group = ldap_fields.IntegerField(_("group id"), db_column='gidNumber')
    gecos =  ldap_fields.CharField(db_column='gecos')
    home_directory = ldap_fields.CharField(_("home directory"), db_column='homeDirectory')
    login_shell = ldap_fields.CharField(_("login shell"), db_column='loginShell', default=settings.GRANADILLA_USERS_SHELL)
    username = ldap_fields.CharField(_("username"), db_column='uid', primary_key=True)
    password = ldap_fields.CharField(_("password"), db_column='userPassword')

    # samba
    if settings.GRANADILLA_USE_SAMBA:
        samba_sid = ldap_fields.CharField(db_column='sambaSID')
        samba_lmpassword = ldap_fields.CharField(db_column='sambaLMPassword')
        samba_ntpassword = ldap_fields.CharField(db_column='sambaNTPassword')
        samba_pwdlastset = ldap_fields.IntegerField(db_column='sambaPwdLastSet')

    def defaults(self, key):
        if key == "email":
            email = "-".join(normalise(self.first_name).split(" "))
            email += "."
            email += "-".join(normalise(self.last_name).split(" "))
            email += "@"
            email += settings.GRANADILLA_MAIL_DOMAIN
            return email.lower()
        elif key == "full_name":
            return " ".join([self.first_name, self.last_name])
        elif key == "gecos":
            return normalise(self.full_name)
        elif key == "group":
            group = LdapGroup.objects.get(name=settings.GRANADILLA_USERS_GROUP)
            return group.gid
        elif key == "home_directory":
            return os.path.join(settings.GRANADILLA_USERS_HOME, self.username)
        elif key == "login_shell":
            return settings.GRANADILLA_USERS_SHELL
        raise Exception("No defaults for %s" % key)

    def __str__(self):
        return self.username

    def __unicode__(self):
        return self.full_name

    def set_password(self, password):
        self.password = hash_password(password)
        if settings.GRANADILLA_USE_SAMBA:
            import smbpasswd
            self.samba_ntpassword = smbpasswd.nthash(password)
            self.samba_lmpassword = smbpasswd.lmhash(password.encode('utf-8'))
            self.samba_pwdlastset = int(time.time())

    def resync_devices(self):
        for group in LdapGroup.objects.filter(usernames__contains=self.username):
            try:
                device_group = LdapDeviceGroup.objects.get(group_dn=group.dn)
            except LdapDeviceGroup.DoesNotExist:
                continue
            device_group.resync()

    def save(self, *args, **kwargs):
        if settings.GRANADILLA_USE_SAMBA and not self.samba_sid:
            self.samba_sid = "%s-%i" % (settings.GRANADILLA_SAMBA_PREFIX, self.uid * 2 + 1000)
        super(LdapUser, self).save(*args, **kwargs)

    class Meta:
        ordering = ('last_name', 'first_name')
        verbose_name = _("user")
        verbose_name_plural = _("users")


class LdapOrganizationalUnit(ldap_models.Model):
    """
    Class for representing an LDAP organization unit entry.
    """
    # LDAP meta-data
    base_dn = settings.GRANADILLA_BASE_DN
    object_classes = ['organizationalUnit']

    # organizationalUnit
    name = ldap_fields.CharField(_("name"), db_column='ou', primary_key=True)


class LdapExternalUser(ldap_models.Model):
    """
    An external user.
    """
    # LDAP meta-data
    base_dn = settings.GRANADILLA_EXTERNAL_USERS_DN
    object_classes = ['inetOrgPerson']

    # inetOrgPerson
    first_name = ldap_fields.CharField(_("first name"), db_column='givenName')
    last_name = ldap_fields.CharField(_("last name"), db_column='sn')
    full_name = ldap_fields.CharField(_("full name"), db_column='cn')
    email = ldap_fields.CharField(_("e-mail address"), db_column='mail', primary_key=True)

    def __str__(self):
        return self.username

    def __unicode__(self):
        return self.full_name

    class Meta:
        ordering = ('last_name', 'first_name')
        verbose_name = _("external user")
        verbose_name_plural = _("external users")

    def save(self, *args, **kwargs):
        self.full_name = u"%s %s" % (self.first_name, self.last_name)
        return super(LdapExternalUser, self).save(*args, **kwargs)


class LdapDevice(ldap_models.Model):
    """
    A device for the VPN.
    """
    # LDAP meta-data
    base_dn = settings.GRANADILLA_DEVICES_DN
    object_classes = ['device', 'simpleSecurityObject']

    # device
    login = ldap_fields.CharField(_("device-specific login"), db_column='cn', primary_key=True)
    name = ldap_fields.CharField(_("name"), db_column='description')
    owner_dn = ldap_fields.CharField(_("owner distinguished name"), db_column='owner')
    owner_username = ldap_fields.CharField(_("owner username"), db_column='o')

    # simpleSecurityObject
    password = ldap_fields.CharField(_("password"), db_column='userPassword')

    def __str__(self):
        return self.owner_username

    def __unicode__(self):
        return self.name

    def check_password(self, password):
        return self.password == hash_password(password)

    def set_password(self, password=''):
        if not password:
            password = random_password()
        self.password = hash_password(password)

    def save(self, *args, **kwargs):
        res = super(LdapDevice, self).save(*args, **kwargs)
        owner = LdapUser.objects.get(dn=self.owner_dn)
        owner.resync_devices()
        return res


class LdapDeviceGroup(ldap_models.Model):
    """
    A group of devices.
    """
    # LDAP meta-data
    base_dn = settings.GRANADILLA_DEVICEGROUPS_DN
    object_classes = ['groupOfNames']

    name = ldap_fields.CharField(_("name"), db_column='cn', primary_key=True)
    group_dn = ldap_fields.CharField(_("target group"), db_column='seeAlso', unique=True)
    members = ldap_fields.ListField(_("members"), db_column='member')

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = _("device group")
        verbose_name_plural = _("device groups")

    @property
    def group(self):
        for group in LdapGroup.objects.all():
            if group.dn == self.group_dn:
                return group
        raise LdapGroup.DoesNotExist("Related group %s not found!!" % self.group_dn)

    @group.setter
    def set_group(self, group):
        self.group_dn = group.dn

    def _get_expected_members(self):
        owners = self.group.get_members()
        owner_dns = [owner.dn for owner in owners]
        devices = LdapDevice.objects.filter(owner_dn__in=owner_dns)
        return [device.dn for device in devices]

    def init(self, save=True):
        self.members = self._get_expected_members()
        if save:
            self.save()

    def resync(self):
        members = self._get_expected_members()

        old_members = set(self.members)
        new_members = set(members)

        added = sorted(new_members - old_members)
        removed = sorted(old_members - new_members)
        if added:
            logger.info("Group %s: added devices %s", self.name, ', '.join(sorted(added)))
        if removed:
            logger.info("Group %s: removed devices %s", self.name, ', '.join(sorted(removed)))
        if added or removed:
            self.members = members
            self.save()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
