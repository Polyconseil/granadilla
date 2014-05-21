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
from granadilla.forms import LdapContactForm, LdapUserForm
from . import models

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
    base_dn = "ou=%s,%s,%s" % (user.username, settings.GRANADILLA_LDAP_CONTACTS_OU, settings.GRANADILLA_LDAP_BASE_DN)
    return models.LdapContact.scoped(base_dn)

def vcard(user):
    """Return the vCard for a contact."""
    import vobject
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
    return group(request, pk=settings.GRANADILLA_LDAP_USERS_GROUP)


@login_required
def contact_card(request, contact_id):
    contact = get_contacts(request.user).objects.get(pk=contact_id)
    return vcard(contact)


class ContactCreate(generic_views.CreateView):
    model = models.LdapContact
    template_name = 'granadilla/contact.html'

    form_class = LdapContactForm

    def get_form_kwargs(self):
        base_dn = 'ou=%s,%s,%s' % (self.request.user.username, settings.GRANADILLA_LDAP_CONTACTS_OU, settings.GRANADILLA_LDAP_BASE_DN)
        kwargs = super(ContactCreate, self).get_form_kwargs()
        kwargs['base_dn'] = base_dn
        return kwargs

    def get_success_url(self):
        return reverse(contact_list)

contact_create = login_required(ContactCreate.as_view())


class ContactUpdate(generic_views.UpdateView):
    model = models.LdapContact
    template_name = 'granadilla/contact.html'
    form_class = LdapContactForm

    def get_queryset(self):
        return get_contacts(self.request.user).objects.all()

contact = login_required(ContactUpdate.as_view())


class ContactDelete(generic_views.DeleteView):
    model = models.LdapContact
    template_name = 'granadilla/contact_delete.html'

    def get_queryset(self):
        return get_contacts(self.request.user).objects.all()

    def get_success_url(self):
        return reverse(contact_list)


contact_delete = login_required(ContactDelete.as_view())


class ContactListView(generic_views.ListView):
    model = models.LdapContact
    template_name = 'granadilla/contact_list.html'

    def get_queryset(self):
        return get_contacts(self.request.user).objects.all()


contact_list = login_required(ContactListView.as_view())


class GroupView(generic_views.DetailView):
    model = models.LdapGroup
    template_name = 'granadilla/group.html'
    printable = False
    slug_field = 'name'

    def get_context_data(self, **kwargs):
        ctxt = super(GroupView, self).get_context_data(**kwargs)
        ctxt.update({
            'printable': self.printable,
            'home': self.object.name == settings.GRANADILLA_LDAP_USERS_GROUP,
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
    return vcard(user)
 
