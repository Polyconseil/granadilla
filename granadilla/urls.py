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

from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'granadilla.views.index'),
    url(r'^devices/$', 'granadilla.views.device_list', name="device_list"),
    url(r'^devices/create/$', 'granadilla.views.device_create', name="device_create"),
    url(r'^devices/(?P<device_login>[^/]+)/$', 'granadilla.views.device_attr', name="device_details"),
    url(r'^devices/(?P<device_login>[^/]+)/password/$', 'granadilla.views.device_password', name='device_password'),
    url(r'^devices/(?P<device_login>[^/]+)/delete/$', 'granadilla.views.device_delete'),
    url(r'^groups/$', 'granadilla.views.groups'),
    url(r'^group/(?P<slug>.*)/print/$', 'granadilla.views.group_print'),
    url(r'^group/(?P<slug>.*)/$', 'granadilla.views.group'),
    url(r'^user/(?P<uid>.*)/card/$', 'granadilla.views.user_card'),
    url(r'^user/(?P<uid>.*)/photo/$', 'granadilla.views.photo'),
    url(r'^user/(?P<uid>.*)/photo/delete/$', 'granadilla.views.photo_delete'),
    url(r'^user/(?P<uid>.*)/$', 'granadilla.views.user'),
)

