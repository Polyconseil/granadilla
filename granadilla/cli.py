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

import colorama
import inspect
import logging
import os
import os.path
import termios
import sys

import zxcvbn

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
logger = logging.getLogger()
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

        while password is None:
            password = self._get_good_password(user)

        user.set_password(password)

    def _get_good_password(self, user):
        password1 = self.grab("Password: ", True)
        password2 = self.grab("Password (again): ", True)
        if password2 != password1:
            self.error("Passwords do not match, try again.")
            return None

        blacklist = [
            user.username,
            user.first_name,
            user.last_name,
        ]
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

    def fill_object(self, obj, *fields):
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
        self.fill_object(user, 'first_name', 'last_name')
        for key in ['full_name', 'gecos', 'group', 'email', 'home_directory', 'login_shell']:
            setattr(user, key, user.defaults(key))
        self.fill_object(user, 'email')
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
            settings.GRANADILLA_GROUPS_DN,
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
        for user in models.LdapUser.objects.order_by('username'):
            self.display(user.username)

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
        self.fill_object(account, 'description')
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

        try:
            meth(*args)
        except models.LdapUser.DoesNotExist:
            self.error("The requested user does not exist.")
            return 2
        except models.LdapGroup.DoesNotExist:
            self.error("The requested group does not exist.")
            return 2


def launch_cli():
    """Main 'cli' entry point."""
    cli = CLI()
    retcode = cli.main(sys.argv)
    sys.exit(retcode)


if __name__ == "__main__":
    launch_cli()
