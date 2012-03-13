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

import os.path

from django.conf import settings
from django.template import Library
from django.utils.translation import ugettext as _

import granadilla

register = Library()

def granadilla_title():
    try:
        return settings.GRANADILLA_TITLE
    except:
        return _("Phonebook")
register.simple_tag(granadilla_title)

def granadilla_version():
    return "<a href=\"%s\" title=\"Granadilla %s\">%s</a>" % (granadilla.__url__, granadilla.__version__, granadilla_title())
register.simple_tag(granadilla_version)

def granadilla_media(medium):
    """
    Returns the path to static media.
    """
    try:
        prefix = settings.GRANADILLA_MEDIA_PREFIX
    except:
        try:
            prefix = os.path.join(settings.STATIC_URL, 'granadilla')
        except:
            prefix = os.path.join(settings.MEDIA_URL, 'granadilla')
    return os.path.join(prefix, medium)
register.simple_tag(granadilla_media)

def field_value(field):
    if not field.form.is_bound:
        data = field.form.initial.get(field.name, field.field.initial)
        if callable(data):
            data = data()
    else:
        data =field.data
    return data
register.simple_tag(field_value)

