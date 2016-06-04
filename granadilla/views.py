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

import time

from .conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseNotModified
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.http import http_date
from django.views.static import was_modified_since
from django.views import generic as generic_views

from granadilla.templatetags.granadilla_tags import granadilla_media
from granadilla.forms import LdapDeviceForm, LdapUserForm
from . import models
from . import vcard

def can_write(user, entry):
    """
    Check whether a user can write an LDAP entry.
    """
    can_edit = user.username == entry.username or user.is_superuser
    for group in user.groups.all():
        if group.name in settings.GRANADILLA_ADMIN_GROUPS:
            return True
    return can_edit

def get_contacts(user):
    base_dn = "ou=%s,%s" % (user.username, settings.GRANADILLA_CONTACTS_DN)
    return models.LdapContact.scoped(base_dn)


def user_vcard(user):
    """Return the vCard for a contact."""
    card = vcard.VCard()
    card['kind'] = 'individual'
    card['names'] = [
        [user.first_name],
        [user.last_name],
        [],  # Additional names
        [],  # Honorific prefixes
        [],  # Honorific suffixes
    ]
    card['full_name'] = user.full_name
    card['email'] = user.email
    card['org'] = getattr(user, 'organization', '')
    card['phone'] = user.phone
    card['cell'] = user.mobile_phone

    # send response
    response = HttpResponse(card.render_bytes(), "text/x-vcard; charset=utf-8")
    response['Content-Disposition'] = "attachment; filename=%s.vcf" % user.pk.replace(' ', '')
    return response
    
@login_required
def index(request, template_name='granadilla/facebook.html'):
    return group(request, pk=settings.GRANADILLA_USERS_GROUP)


@login_required
def contact_card(request, contact_id):
    contact = get_contacts(request.user).objects.get(pk=contact_id)
    return user_vcard(contact)


class DeviceACLMixin(object):
    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return models.LdapDevice.objects.order_by('owner_username')
        else:
            return models.LdapDevice.objects.filter(owner_username=user.username)


class DeviceCreate(generic_views.CreateView):
    """
    Creating a new device
    """
    model = models.LdapDevice
    template_name = 'granadilla/device.html'

    form_class = LdapDeviceForm

    def get_form_kwargs(self):
        kwargs = super(DeviceCreate, self).get_form_kwargs()
        kwargs['target_user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse(device_list)

device_create = login_required(DeviceCreate.as_view())


class DevicePassword(DeviceACLMixin, generic_views.DetailView):
    """
    Generating a new password
    """
    model = models.LdapDevice
    template_name = 'granadilla/device_password.html'

    slug_field = 'login'
    slug_url_kwarg = 'device_login'
    context_object_name = 'device'

    http_method_names = ['get', 'post']

    def post(self, request, *args, **kwargs):
        # Set self.object, expected by Django
        device = self.object = self.get_object()
        password = models.random_password()
        device.set_password(password)
        device.save()

        context = self.get_context_data(object=device)
        context['password'] = password
        return self.render_to_response(context)

device_password = login_required(DevicePassword.as_view())


class DeviceDelete(DeviceACLMixin, generic_views.DeleteView):
    """
    Deleting a device
    """
    model = models.LdapDevice
    template_name = 'granadilla/device_delete.html'

    slug_field = 'login'
    slug_url_kwarg = 'device_login'

    def get_success_url(self):
        return reverse(device_list)


device_delete = login_required(DeviceDelete.as_view())


class DeviceAttrView(DeviceACLMixin, generic_views.DetailView):
    """
    Displaying the device's attribute
    """
    model = models.LdapDevice
    template_name = 'granadilla/device_attr.html'

    slug_field = 'login'
    slug_url_kwarg = 'device_login'
    context_object_name = 'device'

device_attr = login_required(DeviceAttrView.as_view())


class DeviceListView(DeviceACLMixin, generic_views.ListView):
    """
    Displaying the list of devices
    """
    model = models.LdapDevice
    template_name = 'granadilla/device_list.html'
    context_object_name = 'devices'

device_list = login_required(DeviceListView.as_view())


class GroupView(generic_views.DetailView):
    model = models.LdapGroup
    template_name = 'granadilla/group.html'
    printable = False
    slug_field = 'name'

    def get_context_data(self, **kwargs):
        ctxt = super(GroupView, self).get_context_data(**kwargs)
        ctxt.update({
            'printable': self.printable,
            'home': self.object.name == settings.GRANADILLA_USERS_GROUP,
            'group': self.object,
            'members': models.LdapUser.objects.filter(username__in=self.object.usernames),
        })
        return ctxt


group = login_required(GroupView.as_view())



class PrintableGroupView(GroupView):
    printable = True


"""
Display a printable list of users belonging to a group.
"""
group_print = login_required(PrintableGroupView.as_view())


class GroupsView(generic_views.ListView):
    """
    Display the list of groups.
    """
    model = models.LdapGroup
    template_name = 'granadilla/group_list.html'


groups = login_required(GroupsView.as_view())


@login_required
def photo(request, uid):
    now = time.time()
    max_age = 1800
    if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'), now - max_age):
        return HttpResponseNotModified()

    user = get_object_or_404(models.LdapUser, pk=uid)
    if not user.photo:
        return HttpResponseRedirect(granadilla_media('img/unknown.png'))
    response = HttpResponse()
    response['Cache-Control'] = 'max-age=%i' % max_age
    response['Content-Length'] = len(user.photo)
    response['Content-Type'] = 'image/jpeg'
    response['Last-Modified'] = http_date(now)
    response.write(user.photo)
    return response

def photo_delete(request, uid):
    user = get_object_or_404(models.LdapUser, pk=uid)
    if not can_write(request.user, user):
        raise PermissionDenied

    if request.method == 'POST':
        user.photo = ''
        user.save()
        return redirect_to(request, reverse(index))
    else:
        return render_to_response('granadilla/photo_delete.html', RequestContext(request, {
            'object': user,
        }))

@login_required
def user(request, uid):
    user = get_object_or_404(models.LdapUser, pk=uid)

    # set permissions
    can_edit = can_write(request.user, user)

    # handle form
    if request.method == 'POST':
        if not can_edit:
            raise PermissionDenied
        form = LdapUserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect_to(request, reverse(index))
    else:
        form = LdapUserForm(instance=user)

    return render_to_response('granadilla/user.html', RequestContext(request, {
        'can_edit': can_edit,
        'object': user,
        'form': form,
    }))

@login_required
def user_card(request, uid):
    user = get_object_or_404(models.LdapUser, pk=uid)
    return user_vcard(user)
 
