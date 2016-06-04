from __future__ import unicode_literals

from django.conf import settings
from django.core.urlresolvers import reverse
from django import test as django_test

import volatildap

from . import cli
from . import models


class LdapBasedTestCase(django_test.TestCase):
    @classmethod
    def setUpClass(cls):
        super(LdapBasedTestCase, cls).setUpClass()
        cls.ldap_server = volatildap.LdapServer(
            schemas=['core.schema', 'cosine.schema', 'nis.schema', 'inetorgperson.schema'],
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
        settings.PAPAYA_LDAP_SERVER_URI = self.ldap_server.uri
        cli.CLI().init()


class DeviceTests(LdapBasedTestCase):
    def test_add_user_group_device(self):
        user = models.LdapUser(
            uid=123,
            first_name="John",
            last_name="Doe",
            full_name="John Doe",
            home_directory='/home/jdoe',
            email='john.doe@example.org',
            group=1234,
            username='jdoe',
        )
        user.save()
        group = models.LdapGroup(
            gid=1234,
            name="test-group",
            usernames=[user.username],
        )
        group.save()

        device = models.LdapDevice(
            owner_dn=user.dn,
            name="My shiny laptop",
            owner_username='laptop',
            login='jdoe_laptop',
        )
        device.set_password('sesame')
        device.save()
        device_group = models.LdapDeviceGroup(
            name=group.name,
            group_dn=group.dn,
            members=[device.dn],
        )
        device_group.save()

        device2 = models.LdapDevice(
            owner_dn=user.dn,
            name="My awesome smartphone",
            owner_username='smartphone',
            login='jdoe_smartphone',
        )
        device2.set_password('sesame!!')
        device2.save()

        dg = models.LdapDeviceGroup.objects.get()
        self.assertEqual([device.dn, device2.dn], dg.members)

    def test_web_add_device(self):
        # Add the user
        user = models.LdapUser(
            uid=123,
            first_name="John",
            last_name="Doe",
            full_name="John Doe",
            home_directory='/home/jdoe',
            email='john.doe@example.org',
            group=1234,
            username='jdoe',
        )
        user.set_password('yay')
        user.save()

        # And its group
        group = models.LdapGroup(
            gid=1234,
            name="test-group",
            usernames=[user.username],
        )
        group.save()

        # Add a device
        self.client.login(username='jdoe', password='yay')
        response = self.client.post(
            reverse('device_create'),
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
            reverse('device_password', args=(device.login,)),
        )
        self.assertEqual(200, response.status_code)
        pwd = response.context['object'].tmppwd
        self.assertIsNotNone(pwd)

        # Create group
        dg = models.LdapDeviceGroup(
            name=group.name,
            group_dn=group.dn,
        )
        dg.init()
        dg = models.LdapDeviceGroup.objects.get()
        self.assertEqual([device.dn], dg.members)

        # Add another device
        response = self.client.post(
            reverse('device_create'),
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
