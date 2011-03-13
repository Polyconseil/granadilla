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

import base64
try:
    import hashlib
    md5_constructor = hashlib.md5
except ImportError:
    import md5
    md5_constructor = md5.new
import os
import time
import unicodedata

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from ldapdb.models import Model
from ldapdb.models.fields import CharField, ImageField, IntegerField, ListField

BASE_DN = getattr(settings, "GRANADILLA_LDAP_BASE_DN")
MAIL_DOMAIN = getattr(settings, "GRANADILLA_LDAP_MAIL_DOMAIN")
CONTACTS_DN = getattr(settings, "GRANADILLA_LDAP_CONTACTS_DN", "ou=contacts," + BASE_DN)
GROUPS_DN = getattr(settings, "GRANADILLA_LDAP_GROUPS_DN", "ou=groups," + BASE_DN)
ACLS_DN = getattr(settings, "GRANADILLA_LDAP_ACLS_DN", "ou=groupacls," + BASE_DN)
USERS_DN = getattr(settings, "GRANADILLA_LDAP_USERS_DN", "ou=people," + BASE_DN)
USERS_GROUP = getattr(settings, "GRANADILLA_LDAP_USERS_GROUP")
USERS_HOME = getattr(settings, "GRANADILLA_LDAP_USERS_HOME", "/home")
USERS_SHELL = getattr(settings, "GRANADILLA_LDAP_USERS_SHELL", "/bin/bash")

# optional
GROUPS_MAILMAP = getattr(settings, "GRANADILLA_LDAP_GROUPS_MAILMAP", None)
USERS_MAILMAP = getattr(settings, "GRANADILLA_LDAP_USERS_MAILMAP", None)
USERS_SAMBA = getattr(settings, "GRANADILLA_LDAP_USERS_SAMBA", None)

def normalise(str):
    nkfd_form = unicodedata.normalize('NFKD', unicode(str))
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

class LdapAcl(Model):
    """
    Class for representing an LDAP ACL entry.
    """
    # LDAP meta-data
    base_dn = ACLS_DN
    object_classes = ['groupOfNames']

    # groupOfNames
    name = CharField(_('name'), db_column='cn', primary_key=True)
    members = ListField(_('members'), db_column='member')

    def save(self):
        if not self.members:
            self.delete()
        else:
            super(LdapAcl, self).save()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = _('access control list')
        verbose_name_plural = _('access control lists')

class LdapGroup(Model):
    """
    Class for representing an LDAP group entry.
    """
    # LDAP meta-data
    base_dn = GROUPS_DN
    object_classes = ['posixGroup']

    # posixGroup
    gid = IntegerField(_('identifier'), db_column='gidNumber', unique=True)
    name = CharField(_('name'), db_column='cn', primary_key=True)
    usernames = ListField(_('usernames'), db_column='memberUid')

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = _('group')
        verbose_name_plural = _('groups')

class LdapContact(Model):
    """
    Class for representing an LDAP contact entry.
    """
    # LDAP meta-data
    object_classes = ['inetOrgPerson']

    # inetOrgPerson
    first_name = CharField(_('first name'), db_column='givenName')
    last_name = CharField(_('last name'), db_column='sn')
    full_name = CharField(_('full name'), db_column='cn', primary_key=True)
    organization = CharField(_('organization'), db_column='o', blank=True)
    email = CharField(_('e-mail address'), db_column='mail', blank=True)
    phone = CharField(_('phone'), db_column='telephoneNumber', blank=True)
    mobile_phone = CharField(_('mobile phone'), db_column='mobile', blank=True)
    photo = ImageField(_('photo'), db_column='jpegPhoto')
    postal_address = CharField(_('postal address'), db_column='postalAddress', blank=True)

    def __unicode__(self):
        return self.full_name

    def last_name_initial(self):
        if len(self.last_name) > 0:
            return self.last_name[0].upper()
        else:
            return ''

    def save(self):
        self.full_name = "%s %s" % (self.first_name, self.last_name)
        super(LdapContact, self).save()

    class Meta:
        abstract = True
        ordering = ('last_name', 'first_name')
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')

class LdapUser(Model):
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
    base_dn = USERS_DN
    object_classes = ['posixAccount', 'shadowAccount', 'inetOrgPerson']
    if USERS_SAMBA:
        object_classes.append('sambaSamAccount')

    # inetOrgPerson
    first_name = CharField(_('first name'), db_column='givenName')
    last_name = CharField(_('last name'), db_column='sn')
    full_name = CharField(_('full name'), db_column='cn')
    email = CharField(_('e-mail address'), db_column='mail', blank=True)
    phone = CharField(_('phone'), db_column='telephoneNumber', blank=True)
    mobile_phone = CharField(_('mobile phone'), db_column='mobile', blank=True)
    photo = ImageField(_('photo'), db_column='jpegPhoto')

    # FIXME: this is a hack
    internal_phone = CharField(_('internal phone'), db_column='roomNumber', blank=True)

    # posixAccount
    uid = IntegerField(_('user id'), db_column='uidNumber', unique=True)
    group = IntegerField(_('group id'), db_column='gidNumber')
    gecos =  CharField(db_column='gecos')
    home_directory = CharField(_('home directory'), db_column='homeDirectory')
    login_shell = CharField(_('login shell'), db_column='loginShell', default=USERS_SHELL)
    username = CharField(_('username'), db_column='uid', primary_key=True)
    password = CharField(_('password'), db_column='userPassword')

    # samba
    if USERS_SAMBA:
        samba_sid = CharField(db_column='sambaSID')
        samba_lmpassword = CharField(db_column='sambaLMPassword')
        samba_ntpassword = CharField(db_column='sambaNTPassword')
        samba_pwdlastset = IntegerField(db_column='sambaPwdLastSet')

    def defaults(self, key):
        if key == "email":
            email = "-".join(normalise(self.first_name).split(" "))
            email += "."
            email += "-".join(normalise(self.last_name).split(" "))
            email += "@"
            email += MAIL_DOMAIN
            return email.lower()
        elif key == "full_name":
            return " ".join([self.first_name, self.last_name])
        elif key == "gecos":
            return normalise(self.full_name)
        elif key == "group":
            group = LdapGroup.objects.get(name=USERS_GROUP)
            return group.gid
        elif key == "home_directory":
            return os.path.join(USERS_HOME, self.username)
        elif key == "login_shell":
            return USERS_SHELL
        raise Exception("No defaults for %s" % key)

    def __str__(self):
        return self.username

    def __unicode__(self):
        return self.full_name

    def set_password(self, password):
        m = md5_constructor()
        m.update(password)
        hashed = "{MD5}" + base64.b64encode(m.digest())
        self.password = hashed
        if USERS_SAMBA:
            import smbpasswd
            self.samba_ntpassword = smbpasswd.nthash(password)
            self.samba_lmpassword = smbpasswd.lmhash(password)
            self.samba_pwdlastset = int(time.time())

    def save(self):
        if USERS_SAMBA and not self.samba_sid:
            self.samba_sid = "%s-%i" % (USERS_SAMBA, self.uid * 2 + 1000)
        super(LdapUser, self).save()
        
    class Meta:
        ordering = ('last_name', 'first_name')
        verbose_name = _('user')
        verbose_name_plural = _('users')

class LdapOrganizationalUnit(Model):
    """
    Class for representing an LDAP organization unit entry.
    """
    # LDAP meta-data
    base_dn = BASE_DN
    object_classes = ['organizationalUnit']

    # organizationalUnit
    name = CharField(_('name'), db_column='ou', primary_key=True)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
