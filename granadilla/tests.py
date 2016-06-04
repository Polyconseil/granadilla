from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth import models as auth_models
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
        device.set_password('sesame')
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
        device2.set_password('sesame!!')
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
        device.set_password('sesame')
        device.save()

        self.client.login(username='jdoe', password='yay')

        response = self.client.get(
            reverse('device_details', args=(device.login,)),
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
        device.set_password('sesame')
        device.save()

        self.client.login(username='jdoe', password='yay')
        response = self.client.post(
            reverse('device_password', args=(device.login,)),
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
        response = self.client.get(reverse('device_list'))
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
        response = self.client.get(reverse('device_list'))
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
        response = self.client.get(reverse('device_list'))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'granadilla/device_list.html')
        self.assertNotContains(response, 'jdoe_laptop')

        # No access to objects in any way.
        response = self.client.get(reverse('device_details', args=('jdoe_laptop',)))
        self.assertEqual(404, response.status_code)
        response = self.client.get(reverse('device_password', args=('jdoe_laptop',)))
        self.assertEqual(404, response.status_code)

    def test_web_add_device(self):
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
        response = self.client.post(
            reverse('device_password', args=(device.login,)),
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
