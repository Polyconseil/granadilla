from __future__ import unicode_literals

import contextlib
import io
import os.path
import sys

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.urls import reverse
from django import test as django_test

import volatildap

from granadilla import cli
from granadilla import models


# Helpers
# =======


@contextlib.contextmanager
def replace_stdin(contents):
    original_stdin = sys.stdin
    fake_stdin = io.StringIO(contents)
    sys.stdin = fake_stdin
    yield fake_stdin
    sys.stdin = original_stdin


class LdapBasedTestCase(django_test.TestCase):

    databases = ['default', 'ldap']

    @classmethod
    def setUpClass(cls):
        super(LdapBasedTestCase, cls).setUpClass()
        SAMBA_SCHEMA = os.path.join(settings.CHECKOUT_DIR, 'dev', 'samba.schema')
        cls.ldap_server = volatildap.LdapServer(
            schemas=['core.schema', 'cosine.schema', 'nis.schema', 'inetorgperson.schema', SAMBA_SCHEMA],
        )

    @classmethod
    def tearDownClass(cls):
        cls.ldap_server.stop()
        super(LdapBasedTestCase, cls).tearDownClass()

    def setUp(self):
        super(LdapBasedTestCase, self).setUp()
        self.ldap_server.start()
        settings.DATABASES['ldap']['USER'] = self.ldap_server.rootdn
        settings.DATABASES['ldap']['PASSWORD'] = self.ldap_server.rootpw
        settings.DATABASES['ldap']['NAME'] = self.ldap_server.uri
        settings.AUTH_LDAP_SERVER_URI = self.ldap_server.uri
        settings.AUTH_LDAP_BIND_DN = self.ldap_server.rootdn
        settings.AUTH_LDAP_BIND_PASSWORD = self.ldap_server.rootpw
        cli.CLI().init()


# Tests
# =====


class DeviceTests(LdapBasedTestCase):
    def setUp(self):
        super(DeviceTests, self).setUp()

        self.user = models.LdapUser(
            uid=123,
            first_name="John",
            last_name="Doe",
            full_name="John Doe",
            home_directory='/home/jdoe',
            email='john.doe@example.org',
            group=1234,
            username='jdoe',
        )
        self.user.set_password('yay')
        self.user.save()
        self.group = models.LdapGroup(
            gid=1234,
            name="test-group",
            usernames=[self.user.username],
        )
        self.group.save()

    def test_add_user_group_device(self):

        device = models.LdapDevice(
            owner_dn=self.user.dn,
            name="My shiny laptop",
            owner_username='laptop',
            login='jdoe_laptop',
        )
        device.set_password()
        device.save()
        device_group = models.LdapDeviceGroup(
            name=self.group.name,
            group_dn=self.group.dn,
            members=[device.dn],
        )
        device_group.save()

        device2 = models.LdapDevice(
            owner_dn=self.user.dn,
            name="smartphone",
            owner_username='jdoe',
            login='jdoe_smartphone',
        )
        device2.set_password()
        device2.save()

        dg = models.LdapDeviceGroup.objects.get()
        self.assertEqual([device.dn, device2.dn], dg.members)

    def test_web_view_device(self):
        device = models.LdapDevice(
            owner_dn=self.user.dn,
            name="laptop",
            owner_username='jdoe',
            login='jdoe_laptop',
        )
        device.set_password()
        device.save()

        self.client.login(username='jdoe', password='yay')

        response = self.client.get(
            reverse('granadilla:device_details', args=(device.login,)),
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'granadilla/device_attr.html')
        self.assertContains(response, 'jdoe_laptop')

    def test_web_change_password(self):
        device = models.LdapDevice(
            owner_dn=self.user.dn,
            name="laptop",
            owner_username='jdoe',
            login='jdoe_laptop',
        )
        device.set_password()
        device.save()

        self.client.login(username='jdoe', password='yay')
        response = self.client.post(
            reverse('granadilla:device_password', args=(device.login,)),
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'granadilla/device_password.html')
        pwd = response.context['password']
        self.assertContains(response, pwd)

        device = models.LdapDevice.objects.get(dn=device.dn)
        self.assertTrue(device.check_password(pwd))

    def test_list_devices(self):
        device1 = models.LdapDevice(
            owner_dn=self.user.dn,
            name="laptop",
            owner_username='jdoe',
            login='jdoe_laptop',
        )
        device1.set_password()
        device1.save()

        device2 = models.LdapDevice(
            owner_dn=self.user.dn,
            name="desktop",
            owner_username='jdoe',
            login='jdoe_desktop',
        )
        device2.set_password()
        device2.save()

        self.client.login(username='jdoe', password='yay')
        response = self.client.get(reverse('granadilla:device_list'))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'granadilla/device_list.html')
        self.assertContains(response, 'jdoe_laptop')
        self.assertContains(response, 'jdoe_desktop')

    def test_list_devices_superuser(self):
        admin = auth_models.User.objects.create(username='admin', is_superuser=True)
        admin.set_password('MAGIC!')
        admin.save()

        device1 = models.LdapDevice(
            owner_dn=self.user.dn,
            name="laptop",
            owner_username='jdoe',
            login='jdoe_laptop',
        )
        device1.set_password()
        device1.save()

        device2 = models.LdapDevice(
            owner_dn=self.user.dn,
            name="desktop",
            owner_username='jdoe',
            login='jdoe_desktop',
        )
        device2.set_password()
        device2.save()

        self.client.login(username='admin', password='MAGIC!')
        response = self.client.get(reverse('granadilla:device_list'))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'granadilla/device_list.html')
        self.assertContains(response, 'jdoe_laptop')
        self.assertContains(response, 'jdoe_desktop')

    def test_list_devices_filtering(self):
        spy = auth_models.User.objects.create(username='spy')
        spy.set_password('Bond.')
        spy.save()

        device = models.LdapDevice(
            owner_dn=self.user.dn,
            name="laptop",
            owner_username='jdoe',
            login='jdoe_laptop',
        )
        device.set_password()
        device.save()

        self.client.login(username='spy', password='Bond.')
        response = self.client.get(reverse('granadilla:device_list'))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'granadilla/device_list.html')
        self.assertNotContains(response, 'jdoe_laptop')

        # No access to objects in any way.
        response = self.client.get(reverse('granadilla:device_details', args=('jdoe_laptop',)))
        self.assertEqual(404, response.status_code)
        response = self.client.get(reverse('granadilla:device_password', args=('jdoe_laptop',)))
        self.assertEqual(404, response.status_code)

    def test_web_add_device(self):
        # Add a device
        self.client.login(username='jdoe', password='yay')
        response = self.client.post(
            reverse('granadilla:device_create'),
            {
                'name': 'laptop',
            },
        )
        self.assertEqual(302, response.status_code)
        response = self.client.get(response.url)
        self.assertEqual(200, response.status_code)
        device = models.LdapDevice.objects.get()
        self.assertEqual('jdoe_laptop', device.login)

        # Create device password
        response = self.client.get(
            reverse('granadilla:device_password', args=(device.login,)),
        )
        self.assertEqual(200, response.status_code)
        response = self.client.post(
            reverse('granadilla:device_password', args=(device.login,)),
        )
        self.assertEqual(200, response.status_code)
        device = response.context['device']
        pwd = response.context['password']
        # The password is displayed to the user
        self.assertContains(response, pwd)

        # The password is now in use by the device
        device = models.LdapDevice.objects.get(dn=device.dn)
        self.assertTrue(device.check_password(pwd))

        # Create group
        dg = models.LdapDeviceGroup(
            name=self.group.name,
            group_dn=self.group.dn,
        )
        dg.init()
        dg = models.LdapDeviceGroup.objects.get()
        self.assertEqual([device.dn], dg.members)

        # Add another device
        response = self.client.post(
            reverse('granadilla:device_create'),
            {
                'name': 'phone',
            },
            follow=True,
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, models.LdapDevice.objects.count())
        device2 = models.LdapDevice.objects.all()[1]
        self.assertEqual('jdoe_phone', device2.login)

        # Group should contain both devices.
        dg = models.LdapDeviceGroup.objects.all()[0]
        self.assertEqual([device.dn, device2.dn], dg.members)


class UserTests(LdapBasedTestCase):
    def test_cli_adduser(self):
        lines = [
            'John',
            'Doe',
            '',
            'this password is amazing!',
            'this password is amazing!',
        ]

        interface = cli.CLI()
        with replace_stdin('\n'.join(lines)):
            interface.adduser('jdoe')

        user = models.LdapUser.objects.get(username='jdoe')
        self.assertEqual("John", user.first_name)
        self.assertEqual("Doe", user.last_name)
        self.assertIsNotNone(user.samba_ntpassword)
        self.assertEqual('', user.samba_lmpassword)
