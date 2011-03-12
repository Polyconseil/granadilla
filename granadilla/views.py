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

import time
import vobject

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseNotModified
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.http import http_date
from django.views.generic import create_update, list_detail
from django.views.generic.simple import redirect_to
from django.views.static import was_modified_since
from templatetags.granadilla_tags import granadilla_media

from granadilla.forms import LdapContactForm, LdapUserForm
from granadilla.models import LdapContact, LdapGroup, LdapUser, CONTACTS_DN

def can_write(user, entry):
    """
    Check whether a user can write an LDAP entry.
    """
    can_edit = user.username == entry.username or user.is_superuser
    for group in user.groups.all():
        if group.name in settings.GRANADILLA_ADMIN_GROUPS:
            can_edit = True
            break
    return can_edit

def get_contacts(user):
    base_dn = "ou=%s,%s" % (user.username, CONTACTS_DN)
    return LdapContact.scoped(base_dn)

def vcard(user):
    """Return the vCard for a contact."""
    card = vobject.vCard()
    card.add('n')
    card.n.value = vobject.vcard.Name(given=user.first_name, family=user.last_name)
    card.add('fn')
    card.fn.value = user.full_name
    card.add('email')
    card.email.value = user.email
    card.email.type_param = 'INTERNET'
    if hasattr(user, 'organization') and user.organization:
        org = card.add('org')
        org.value = [user.organization]
    if user.phone:
        tel = card.add('tel')
        tel.value = user.phone
        tel.type_param = "VOICE"
    if user.mobile_phone:
        tel = card.add('tel')
        tel.value = user.mobile_phone
        tel.type_param = "CELL"
    if False and user.photo:
        photo = card.add('photo')
        photo.value = user.photo
        photo.encoding_param = "b"
        photo.type_param = "JPEG"

    # send response
    response = HttpResponse(card.serialize(), "text/x-vcard; charset=utf-8")
    response['Content-Disposition'] = "attachment; filename=%s.vcf" % user.pk.replace(' ', '')
    return response
    
@login_required
def index(request, template_name='granadilla/facebook.html'):
    return group(request, settings.GRANADILLA_LDAP_USERS_GROUP)

@login_required
def contact(request, contact_id):
    contact = get_contacts(request.user).objects.get(pk=contact_id)
    if request.method == 'POST':
        form = LdapContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            return redirect_to(request, reverse(contact_list))
    else:
        form = LdapContactForm(instance=contact)
    return render_to_response('granadilla/contact.html', RequestContext(request, {
        'object': contact,
        'form': form,
    }))

@login_required
def contact_card(request, contact_id):
    contact = get_contacts(request.user).objects.get(pk=contact_id)
    return vcard(contact)

@login_required
def contact_create(request):
    base_dn = "ou=%s,%s" % (request.user.username, CONTACTS_DN)
    if request.method == 'POST':
        form = LdapContactForm(request.POST, base_dn=base_dn)
        if form.is_valid():
            form.save()
            return redirect_to(request, reverse(contact_list))
    else:
        form = LdapContactForm(base_dn=base_dn)
    return render_to_response('granadilla/contact.html', RequestContext(request, {
        'form': form,
    }))

@login_required
def contact_delete(request, contact_id):
    contact = get_contacts(request.user).objects.get(pk=contact_id)
    if request.method == 'POST':
        contact.delete()
        return redirect_to(request, reverse(contact_list))
    else:
        return render_to_response('granadilla/contact_delete.html', RequestContext(request, {'object': contact}))

@login_required
def contact_list(request):
    return list_detail.object_list(request,
        queryset=get_contacts(request.user).objects.all(),
        template_name="granadilla/contact_list.html")

@login_required
def group(request, gid, printable=False):
    """
    Display the list of users belonging to a group.
    """
    group = get_object_or_404(LdapGroup, pk=gid)
    return list_detail.object_list(request,
        queryset=LdapUser.objects.filter(username__in=group.usernames),
        template_name="granadilla/group.html",
        extra_context={
            'home': group.name == settings.GRANADILLA_LDAP_USERS_GROUP,
            'group': group,
            'printable': printable,
        })

@login_required
def group_print(request, gid):
    """
    Display a printable list of users belonging to a group.
    """
    return group(request, gid, printable=True)

@login_required
def groups(request):
    """
    Display the list of groups.
    """
    return list_detail.object_list(request,
        queryset=LdapGroup.objects.all(),
        template_name="granadilla/group_list.html")

@login_required
def photo(request, uid):
    now = time.time()
    max_age = 1800
    if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'), now - max_age):
        return HttpResponseNotModified()

    user = get_object_or_404(LdapUser, pk=uid)
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
    user = get_object_or_404(LdapUser, pk=uid)
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
    user = get_object_or_404(LdapUser, pk=uid)

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
    user = get_object_or_404(LdapUser, pk=uid)
    return vcard(user)
 
