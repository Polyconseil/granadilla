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

import inspect
import logging
import os
import os.path
import sys

from django.db.models.signals import post_save, post_delete

from granadilla.models import LdapAcl, LdapGroup, LdapUser, LdapOrganizationalUnit, ACLS_DN, MAIL_DOMAIN, USERS_DN, USERS_GROUP, USERS_MAILMAP, USERS_SAMBA, GROUPS_DN, GROUPS_MAILMAP

POSTMAP = "/usr/sbin/postmap"

# configure logging
logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def change_password(user):
    password1 = grab("Password: ", True)
    password2 = grab("Password (again): ", True)
    if password2 != password1:
        raise Exception("Passwords do not match")
    user.set_password(password1)

def grab(prompt, password=False):
    import sys
    import termios

    if password:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~termios.ECHO
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, new)
            passwd = raw_input(prompt)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\n")
        return passwd
    else:
        sys.stdout.write(prompt)
        return unicode(sys.stdin.readline(), 'utf-8').strip()

def prompt(object, *fields):
    for key in fields:
        field = object._meta.get_field(key)
        name = key.replace("_", " ").title()
        default = getattr(object, key)
        new_value = ''

        if default:
            new_value = grab("%s [%s]: " % (name, default))
        else:
            while not len(new_value):
                new_value = grab("%s: " % (name))

        if new_value:
            setattr(object, key, new_value)

class Tool(object):
    def __init__(self):
        """
        Setup callbacks for user/groups modifications.
        """
        post_delete.connect(self.postfix_groups, sender=LdapGroup)
        post_save.connect(self.postfix_groups, sender=LdapGroup)
        post_delete.connect(self.postfix_users, sender=LdapUser)
        post_save.connect(self.postfix_users, sender=LdapUser)

    def addgroup(self, groupname):
        """
        Create a new group.
        """
        # get gid
        groups = LdapGroup.objects.all()
        if groups:
            id = max([ x.gid for x in groups ]) + 1
        else:
            id = 10000
        
        # create group
        group = LdapGroup()
        group.name = groupname
        group.gid = id
        group.save()

    def adduser(self, username, groupname=None):
        """
        Create a new user or add a user to a group.
        """
        # add a user to a group
        if groupname:
            user = LdapUser.objects.get(username=username)
            group = LdapGroup.objects.get(name=groupname)
            if not user.username in group.usernames:
                group.usernames.append(user.username)
                group.save()

            if ACLS_DN:
                try:
                    acl = LdapAcl.objects.get(name=groupname)
                    if not user.dn in acl.members:
                        acl.members.append(user.dn)
                        acl.save()
                except LdapAcl.DoesNotExist:
                    acl = LdapAcl()
                    acl.name = groupname
                    acl.members = [ user.dn ]
                    acl.save()
            return
 
        # create user
        users = LdapUser.objects.all()
        if users:
            id = max([ x.uid for x in users ]) + 1
        else:
            id = 10000

        # prompt for information
        user = LdapUser()
        user.username = username
        user.uid = id
        prompt(user, 'first_name', 'last_name')
        for key in ['full_name', 'gecos', 'group', 'email', 'home_directory', 'login_shell']:
            setattr(user, key, user.defaults(key))
        prompt(user, 'email')
        change_password(user)

        # save user
        user.save()

    def catgroup(self, groupname):
        """
        Display a group's details.
        """
        user = LdapGroup.objects.get(name=groupname)
        print "dn: %s" % user.dn
        for field in user._meta.fields:
            if field.db_column:
                val = getattr(user, field.name, None)
                if val:
                    print "%s: %s" % (field.db_column, getattr(user, field.name))

    def catuser(self, username):
        """
        Display a user's details.
        """
        user = LdapUser.objects.get(username=username)
        print "dn: %s" % user.dn
        for field in user._meta.fields:
            if field.db_column and field.db_column != "jpegPhoto":
                val = getattr(user, field.name, None)
                if val:
                    print "%s: %s" % (field.db_column, getattr(user, field.name))

    def delgroup(self, groupname):
        """
        Delete the given group.
        """
        LdapGroup.objects.get(name=groupname).delete()
        if ACLS_DN:
            try:
                LdapAcl.objects.get(name=groupname).delete()
            except LdapAcl.DoesNotExist:
                pass

    def deluser(self, username, groupname=None):
        """
        Delete the given user or remove it from a group.
        """
	def remove_from_group(user, group):
            if user.username in group.usernames:
                group.usernames = [ x for x in group.usernames if x != user.username ]
                group.save()

            if ACLS_DN:
                try:
                    acl = LdapAcl.objects.get(name=group.name)
                    if user.dn in acl.members:
                        acl.members = [ x for x in acl.members if x != user.dn ]
                        acl.save()
                except LdapAcl.DoesNotExist:
                    pass

        user = LdapUser.objects.get(username=username)

        # remove user from a group
        if groupname:
            remove_from_group(user, LdapGroup.objects.get(name=groupname))
            return

        # delete user
        for group in LdapGroup.objects.all():
            remove_from_group(user, group)
        user.delete()

    def init(self):
        """
        Initialise the LDAP directory.
        """
        # create organizational units
        for dn in [ USERS_DN, GROUPS_DN, ACLS_DN ]:
            if not dn:
                continue

            # FIXME: this may not be accurate depending on the DN
            name = dn.split(",")[0].split("=")[1]
            try:
                ou = LdapOrganizationalUnit.objects.get(name=name)
            except LdapOrganizationalUnit.DoesNotExist:
                ou = LdapOrganizationalUnit()
                ou.name = name
                ou.save()

        # create default group
        try:
            LdapGroup.objects.get(name=USERS_GROUP)
        except:
            self.addgroup(USERS_GROUP)

    def lsgroup(self, groupname=None):
        """
        Print the list of groups.
        """
        if groupname:
            members = LdapGroup.objects.get(name=groupname).usernames
            others = [ x.username for x in LdapUser.objects.all() if not x.username in members ]
            print "members:\n " +  "\n ".join(sorted(members))
            print
            print "non-members:\n " +  "\n ".join(sorted(others))
        else:
            for group in LdapGroup.objects.all():
                print group.name

    def lsuser(self):
        """
        Print the list of users.
        """
        for user in LdapUser.objects.order_by('username'):
            print user.username

    def moduser(self, username, attr, value):
        """
        Modify an attribute for a user.
        """
        user = LdapUser.objects.get(username=username)
        for field in user._meta.fields:
            if field.db_column == attr:
                setattr(user, field.name, value)
                user.save()
                return
        raise Exception("Unnown field %s" % attr)

    def help(self):
        """
        Display a help message.
        """
        cmdhelp = []
        for cmd in dir(self):
            if not cmd.startswith("_"):
                func = getattr(tool, cmd)
                bits = [cmd]
                bits.extend(["<%s>" % arg for arg in inspect.getargspec(func)[0][1:] ])
                cmdhelp.append("%s%s" % (" ".join(bits).ljust(30), func.__doc__.strip()))

        print """Usage: %s <command> [arguments..]

Commands:
%s
""" % (os.path.basename(sys.argv[0]), "\n".join(cmdhelp))

    def passwd(self, username):
        """
        Change the given user's password.
        """
        user = LdapUser.objects.get(username=username)
        change_password(user)
        user.save()

    def postfix_groups(self, **kwargs):
        """
        Print the postfix virtual domain map for the LDAP groups.
        """
        if not GROUPS_MAILMAP:
            return

        logging.info("Writing postfix groups map to %s" % GROUPS_MAILMAP)
        fp = open(GROUPS_MAILMAP, "w")
        for group in LdapGroup.objects.filter():
            if len(group.usernames):
                dest = " ".join(group.usernames)
            else:
                dest = "/dev/null"
            fp.write("%s@%s\t%s\n" % (group.name, MAIL_DOMAIN, dest))
        fp.close()
        os.system("%s %s" % (POSTMAP, GROUPS_MAILMAP))
 
    def postfix_users(self, **kwargs):
        """
        Print the postfix virtual domain map for the LDAP users.
        """
        if not USERS_MAILMAP:
            return

        logging.info("Writing postfix users map to %s" % USERS_MAILMAP)
        fp = open(USERS_MAILMAP, "w")
        for user in LdapUser.objects.all():
            if user.email:
                fp.write("%s\t%s\n" % (user.email, user.username))
        fp.close()
        os.system("%s %s" % (POSTMAP, USERS_MAILMAP))

if __name__ == "__main__":
    import sys
    tool = Tool()

    if len(sys.argv) < 2:
        tool.help()
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    try:
        func = getattr(tool, cmd)
    except AttributeError:
        tool.help()
        sys.exit(1)

    try:
        func(*args)
    except LdapUser.DoesNotExist:
        sys.stderr.write("The requested user does not exist.\n")
        sys.exit(1)
    except LdapGroup.DoesNotExist:
        sys.stderr.write("The requested group does not exist.\n")
        sys.exit(1)

