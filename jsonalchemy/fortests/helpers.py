# -*- coding: utf-8 -*-
#
# This file is part of JSONAlchemy.
# Copyright (C) 2015 CERN.
#
# JSONAlchemy is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# JSONAlchemy is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with JSONAlchemy; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Test helpers. Functions for calculated tests."""

from jsonschema import ValidationError
from string import uppercase


def author(field):
    return "Smith, J."


def isCorrectName(field):
    """An author field is correct if it starts with an uppercase."""
    if field[0] not in uppercase:
        raise ValidationError("The author name doesn't" +
                              " start with an uppercase.")


def schema_title(field):
    return field.root.schema['title']


def raise_error(field, name, value):
    raise NotImplementedError("We can't process %s" % name)
