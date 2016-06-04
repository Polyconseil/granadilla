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
import colorama
import datetime
import django
import inspect
import logging
import os
import os.path
import termios
import time
import re
import sys

import zxcvbn

if django.VERSION[:2] >= (1, 7):
    django.setup()

from .conf import settings
from . import models

PY2 = sys.version_info[0] == 2

if PY2:
    def force_text(txt):
        return txt.decode('utf-8')
else:
    def force_text(txt):
        return txt

# configure logging
logger = logging.getLogger(__name__.split('.')[0])
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def command(fun):
    """Decorator that marks a method as "publicly callable".

    Usage:

        >>> @command
        ... def foo(self):
        ...     pass
    """
    fun.is_command = True
    return fun


class CLI(object):

    PASSWORD_MIN_SCORE = 3

    def _write(self, txt, args, color=colorama.Fore.RESET, target=sys.stdout):
        txt = txt % args
        txt = '%s%s%s\n' % (color, txt, colorama.Fore.RESET)
        if PY2:
            target.write(txt.encode('utf-8'))
        else:
            target.write(txt)

    def display(self, txt, *args):
        self._write(txt, args)

    def success(self, txt, *args):
        self._write(txt, args, color=colorama.Fore.GREEN)

    def warn(self, txt, *args):
        self._write(txt, args, color=colorama.Fore.YELLOW)

    def error(self, txt, *args):
        self._write(txt, args, color=colorama.Fore.RED, target=sys.stderr)

    def change_password(self, user):
        password = None

        blacklist = [
            user.username,
            user.first_name,
            user.last_name,
        ]

        while password is None:
            password = self._get_good_password(blacklist)

        user.set_password(password)

    def change_device_password(self, device):
        password = None

        blacklist = [
            device.owner_dn,
            device.name,
        ]

        while password is None:
            password = self._get_good_password(blacklist)

        device.set_password(password)

    def _get_good_password(self, blacklist):
        password1 = self.grab("Password: ", True)
        password2 = self.grab("Password (again): ", True)
        if password2 != password1:
            self.error("Passwords do not match, try again.")
            return None

        check = zxcvbn.password_strength(password1, blacklist)
        if check['score'] < self.PASSWORD_MIN_SCORE:
            self.error("Password is too weak (bruteforce: %s)", check['crack_time_display'])
            return None

        self.success("Password is strong enough (bruteforce: %s)", check['crack_time_display'])
        return password1

    def grab(self, prompt, password=False):

        if password:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            new = termios.tcgetattr(fd)
            new[3] = new[3] & ~termios.ECHO
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, new)
                passwd = force_text(raw_input(prompt))
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            sys.stdout.write("\n")
            return passwd

        else:
            sys.stdout.write(prompt)
            return force_text(sys.stdin.readline()).strip()

    def fill_object(self, obj, fields):
        for key in fields:
            field = obj._meta.get_field(key)
            name = key.replace("_", " ").title()
            default = getattr(obj, key)
            new_value = ''

            if default:
                new_value = self.grab("%s [%s]: " % (name, default))
            else:
                while not len(new_value):
                    new_value = self.grab("%s: " % (name))

            if new_value:
                setattr(obj, key, new_value)

    @command
    def addgroup(self, groupname):
        """
        Create a new group.
        """
        # get gid
        gids = models.LdapGroup.objects.values_list('gid', flat=True)
        if gids:
            gid = max(gids) + 1
        else:
            gid = 10000

        # create group
        group = models.LdapGroup()
        group.name = groupname
        group.gid = gid
        group.save()

    @command
    def adduser(self, username):
        """
        Create a new user.
        """
        # create user
        users = models.LdapUser.objects.all()
        if users:
            id = max([ x.uid for x in users ]) + 1
        else:
            id = 10000

        # prompt for information
        user = models.LdapUser()
        user.username = username
        user.uid = id
        self.fill_object(user, ['first_name', 'last_name'])
        for key in ['full_name', 'gecos', 'group', 'email', 'home_directory', 'login_shell']:
            setattr(user, key, user.defaults(key))
        self.fill_object(user, ['email'])
        self.change_password(user)

        # save user
        user.save()

    @command
    def addusergroup(self, username, groupname):
        """Add user <username> to group <groupname>."""
        user = models.LdapUser.objects.get(username=username)
        group = models.LdapGroup.objects.get(name=groupname)
        if not user.username in group.usernames:
            group.usernames.append(user.username)
            group.save()

        if settings.GRANADILLA_USE_ACLS:
            try:
                acl = models.LdapAcl.objects.get(name=groupname)
                if not user.dn in acl.members:
                    acl.members.append(user.dn)
                    acl.save()
            except models.LdapAcl.DoesNotExist:
                acl = models.LdapAcl()
                acl.name = groupname
                acl.members = [ user.dn ]
                acl.save()

    @command
    def catgroup(self, groupname):
        """
        Display a group's details.
        """
        group = models.LdapGroup.objects.get(name=groupname)
        self.display("dn: %s", group.dn)
        for field in group._meta.fields:
            if field.db_column:
                val = getattr(group, field.name, None)
                if val:
                    self.display("%s: %s", field.db_column, val)

    @command
    def catuser(self, username):
        """
        Display a user's details.
        """
        user = models.LdapUser.objects.get(username=username)
        self.display("dn: %s", user.dn)
        for field in user._meta.fields:
            if field.db_column and field.db_column != "jpegPhoto":
                val = getattr(user, field.name, None)
                if val:
                    self.display("%s: %s", field.db_column, val)

    @command
    def delgroup(self, groupname):
        """
        Delete the given group.
        """
        group = models.LdapGroup.objects.get(name=groupname)
        self.warn("Deleting group %s", group.dn)
        group.delete()
        if settings.GRANADILLA_USE_ACLS:
            try:
                models.LdapAcl.objects.get(name=groupname).delete()
            except models.LdapAcl.DoesNotExist:
                pass
        self.sync_device_acls()

    @command
    def delusergroup(self, username, groupname):
        """Remove a user from a group."""
        user = models.LdapUser.objects.get(username=username)
        group = models.LdapGroup.objects.get(name=groupname)

        self._delusergroup(user, group)

    def _delusergroup(self, user, group):
        if user.username in group.usernames:
            self.warn("Removing %s from group %s", user.username, group.name)
            group.usernames = [ x for x in group.usernames if x != user.username ]
            group.save()

        if settings.GRANADILLA_USE_ACLS:
            try:
                acl = models.LdapAcl.objects.get(name=group.name)
                if user.dn in acl.members:
                    acl.members = [ x for x in acl.members if x != user.dn ]
                    acl.save()
            except models.LdapAcl.DoesNotExist:
                pass


    @command
    def deluser(self, username):
        """
        Delete the given user.
        """
        user = models.LdapUser.objects.get(username=username)

        # delete user
        for group in models.LdapGroup.objects.all():
            self._delusergroup(user, group)

        self.warn("Removing user %s", user.dn)
        user.delete()

    @command
    def init(self):
        """
        Initialise the LDAP directory.
        """
        # create organizational units
        dns = [
            settings.GRANADILLA_USERS_DN,
            settings.GRANADILLA_EXTERNAL_USERS_DN,
            settings.GRANADILLA_DEVICES_DN,
            settings.GRANADILLA_GROUPS_DN,
            settings.GRANADILLA_SERVICES_DN,
        ]
        if settings.GRANADILLA_USE_ACLS:
            dns += [settings.GRANADILLA_ACLS_DN]

        for dn in dns:
            # FIXME: this may not be accurate depending on the DN
            name = dn.split(",")[0].split("=")[1]
            try:
                ou = models.LdapOrganizationalUnit.objects.get(name=name)
            except models.LdapOrganizationalUnit.DoesNotExist:
                ou = models.LdapOrganizationalUnit()
                ou.name = name
                ou.save()

        # create default group
        try:
            models.LdapGroup.objects.get(name=settings.GRANADILLA_USERS_GROUP)
        except:
            self.addgroup(settings.GRANADILLA_USERS_GROUP)

    @command
    def lsgroups(self):
        """Print the list of groups"""
        for group in models.LdapGroup.objects.all():
            self.display(group.name)

    @command
    def lsgroup(self, groupname):
        """
        Print the members of one group
        """
        members = models.LdapGroup.objects.get(name=groupname).usernames
        others = [ x.username for x in models.LdapUser.objects.all() if not x.username in members ]
        self.display("members:")
        for member in sorted(members):
            self.display("  %s", member)
        self.display("")
        self.display("non-members:")
        for other in sorted(others):
            self.display("  %s", other)

    @command
    def lsuser(self):
        """
        Print the list of users.
        """
        self.display("%20s%50s%20s", "username", "Email", "Password last set")
        for user in models.LdapUser.objects.order_by('username'):
            if user.samba_pwdlastset > time.time() - 3 * 365 * 24 * 60 * 60:
                pwd_last_set = datetime.date.fromtimestamp(user.samba_pwdlastset).strftime('%d %b %Y')
            else:
                pwd_last_set = "long ago"
            self.display("%20s%50s%20s", user.username, user.email, pwd_last_set)

    @command
    def lspasswd(self):
        """
        Print the list of passwords.
        """
        for user in models.LdapUser.objects.order_by('username'):
            self.display(user.password)

    @command
    def lsjohnpasswd(self):
        """
        Print the list of password formated for john
        """
        password_re = re.compile(r'^{\w+}([A-Za-z0-9/+=]+)$')  # {MD5}uihGYUGE==
        for user in models.LdapUser.objects.order_by('username'):
            match = password_re.match(user.password)
            if not match:
                self.warn("Password of user %s doesn't match {<ALGO>}<hash> format.", user.username)
                continue
            password = match.groups()[0]
            john_password = base64.b16encode(base64.b64decode(password)).lower()
            self.display("%s:%s", user.username, john_password)

    @command
    def lsusergroups(self, username):
        """Print the groups a user belongs to."""
        user = models.LdapUser.objects.get(username=username)
        self.display("Groups for %s (%s):\n", user.username, user.email)

        for group in models.LdapGroup.objects.order_by('name'):
            if user.username in group.usernames:
                self.display(group.name)

    @command
    def moduser(self, username, attr, value):
        """
        Modify an attribute for a user.
        """
        user = models.LdapUser.objects.get(username=username)
        for field in user._meta.fields:
            if field.db_column == attr:
                setattr(user, field.name, value)
                user.save()
                return
        raise Exception("Unnown field %s" % attr)

    @command
    def passwd(self, username):
        """
        Change the given user's password.
        """
        user = models.LdapUser.objects.get(username=username)
        self.change_password(user)
        user.save()

    @command
    def service_list(self):
        """
        Print the list of service accounts.
        """
        for account in models.LdapServiceAccount.objects.order_by('username'):
            self.display("%-20s %s", account.username, account.description.replace('\n', '  '))

    @command
    def service_add(self, username):
        """
        Add a new service account.
        """
        account = models.LdapServiceAccount()
        account.username = username
        self.fill_object(account, ['description'])
        self.change_password(account)

        account.save()

    @command
    def service_mod(self, username, attr, value):
        """
        Modify an attribute for a service.
        """
        account = models.LdapServiceAccount.objects.get(username=username)
        for field in account._meta.fields:
            if field.db_column == attr:
                setattr(account, field.name, value)
                account.save()
                return
        raise Exception("Unknown field %s" % attr)

    @command
    def service_del(self, username):
        """
        Delete a service account.
        """
        account = models.LdapServiceAccount.objects.get(username=username)
        self.warn("Deleting service %s", account.dn)
        account.delete()

    @command
    def service_passwd(self, username):
        """
        Change the password of a service.
        """
        account = models.LdapServiceAccount.objects.get(username=username)
        self.change_password(account)
        account.save()

    @command
    def extuser_list(self):
        """
        Print the list of extuser accounts.
        """
        for account in models.LdapExternalUser.objects.order_by('email'):
            self.display("%-20s %s", account.email, account.full_name)

    @command
    def extuser_add(self, email):
        """
        Add a new extuser account.
        """
        account = models.LdapExternalUser()
        account.email = email
        self.fill_object(account, [
            'first_name',
            'last_name',
        ])

        account.save()

    @command
    def extuser_addingroup(self, email, groupname):
        """
        Add an extuser in a group.
        """
        account = models.LdapExternalUser.objects.get(email=email)
        group = models.LdapGroup.objects.get(name=groupname)

        if settings.GRANADILLA_USE_ACLS:
            try:
                acl = models.LdapAcl.objects.get(name=groupname)
            except models.LdapAcl.DoesNotExist:
                acl = models.LdapAcl()
                acl.name = groupname
                acl.members = []

            if account.dn not in acl.members:
                acl.members.append(account.dn)
            acl.save()

    @command
    def extuser_lsgroups(self, email):
        """
        List the groups of an extuser.
        """
        account = models.LdapExternalUser.objects.get(email=email)

        for acl in models.LdapAcl.objects.order_by('name'):
            if account.dn in acl.members:
                self.display(acl.name)

    @command
    def extuser_delfromgroup(self, email, groupname):
        """
        Remove an extuser from a group.
        """
        account = models.LdapExternalUser.objects.get(email=email)
        group = models.LdapGroup.objects.get(name=groupname)

        self.warn("Removing %s from group %s", account.email, group.name)

        if settings.GRANADILLA_USE_ACLS:
            try:
                acl = models.LdapAcl.objects.get(name=groupname)
            except models.LdapAcl.DoesNotExist:
                return

            if account.dn in acl.members:
                acl.members = [ dn for dn in acl.members if dn != account.dn ]
                acl.save()

    @command
    def extuser_mod(self, email, attr, value):
        """
        Modify an attribute for a extuser.
        """
        account = models.LdapExternalUser.objects.get(email=email)
        for field in account._meta.fields:
            if field.db_column == attr:
                setattr(account, field.name, value)
                account.save()
                return
        raise Exception("Unknown field %s" % attr)

    @command
    def extuser_del(self, email):
        """
        Delete a extuser account.
        """
        account = models.LdapExternalUser.objects.get(email=email)
        self.warn("Deleting extuser %s", account.dn)
        account.delete()

    @command
    def device_list(self):
        """
        Print the list of devices and their owner.
        """
        for device in models.LdapDevice.objects.order_by('login'):
            self.display("%s", device.login)

    @command
    def device_add(self, username, device_name):
        """
        Add a new device.
        """
        device = models.LdapDevice()
        user = models.LdapUser.objects.get(username=username)
        device.owner_username = username
        device.owner_dn = user.dn
        device.name = device_name
        device.login = username + "_" + device_name
        self.change_device_password(device)
        device.save()
        self.sync_device_acls()

    @command
    def device_password(self, username, name):
        """
        Change the password of the device.
        """
        device = models.LdapDevice.objects.get(
                    login=username + "_" + name)
        self.change_device_password(device)
        device.save()

    @command
    def device_del(self, username, device_name):
        """
        Delete a device.
        """
        device = models.LdapDevice.objects.get(
                        login=username + "_" + device_name)
        self.warn("Deleting device %s", device.login)
        device.delete()

    @command
    def device_group_add(self, group_name):
        """
        Add a device group; must relate to an existing group.
        """
        group = models.LdapGroup.objects.get(name=group_name)
        device_group = models.LdapDeviceGroup(
            name=group_name,
            group_dn=group.dn,
        )
        device_group.init()
        self.display("Created DeviceGroup %s with members %s", device_group, device_group.members)

    @command
    def sync_device_acls(self):
        """
        Synchronize device ACLs.
        """
        for device_group in models.LdapDeviceGroup.objects.all():
            device_group.resync()

    @command
    def help(self):
        """
        Display a help message.
        """
        cmdhelp = []
        for cmd in dir(self):
            func = getattr(self, cmd)
            if not getattr(func, 'is_command', False):
                continue

            bits = [cmd]
            bits.extend(["<%s>" % arg for arg in inspect.getargspec(func)[0][1:] ])
            cmdhelp.append("%s%s" % (" ".join(bits).ljust(50), func.__doc__.strip()))

        self.display("""Usage: %s <command> [arguments..]

Commands:
%s
""", os.path.basename(sys.argv[0]), "\n".join(cmdhelp))


    def main(self, argv):
        if len(argv) < 2:  # No command
            self.help()
            return 1

        cmd = argv[1]
        args = argv[2:]
        meth = getattr(self, cmd, None)
        if meth is None or not getattr(meth, 'is_command', False):
            self.error("Unknown command %s", cmd)
            self.help()
            return 1

        args = [force_text(arg) for arg in args]

        try:
            meth(*args)
        except models.LdapUser.DoesNotExist:
            self.error("The requested user does not exist.")
            return 2
        except (models.LdapAcl.DoesNotExist, models.LdapGroup.DoesNotExist):
            self.error("The requested group does not exist.")
            return 2
        except models.LdapServiceAccount.DoesNotExist:
            self.error("The requested service account does not exist.")
            return 2
        except models.LdapExternalUser.DoesNotExist:
            self.error("The requested external user does not exist.")
            return 2


def launch_cli():
    """Main 'cli' entry point."""
    cli = CLI()
    retcode = cli.main(sys.argv)
    sys.exit(retcode)


if __name__ == "__main__":
    launch_cli()
