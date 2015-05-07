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
# JSONAlchemy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with JSONAlchemy; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#
# In applying this licence, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import unicode_literals
from numbers import Number

from six import iteritems
from jsonschema import Draft4Validator


def wrap(value):

    def choose_wrapper(value):

        if isinstance(value, dict):
            return JSONObject(value)
        elif isinstance(value, list):
            return JSONArray(value)
        elif isinstance(value, str):
            return JSONString(value)
        elif isinstance(value, int):
            return JSONInteger(value)
        elif isinstance(value, float):
            return JSONNumber(value)
        raise TypeError('Type not defined in JSON Schema.')

    if isinstance(value, JSONBase) or isinstance(value, bool) or \
            value is None:
        # There is no representation of None and booleans as JSONBase objects.
        return value

    return choose_wrapper(value)


class JSONBase(object):

    def __init__(self, schema=None):
        self.schema = schema or {}

    @property
    def validation(parent):

        class JSONValidation(object):
            def __init__(self, json):
                self._json = json
                self._copy = json.__class__(json, json.schema)

            def __enter__(self):
                return self._copy

            def __exit__(self, type, value, traceback):
                if not type:
                    # There was no exception
                    self._copy.validate()
                    self._json._update(self._copy)

        return JSONValidation(parent)

    def validate(self):
        types = {
            'object': (dict, JSONObject,),
            'array': (list, JSONArray,),
            'string': (str, JSONString,),
            'number': (int, float, JSONNumber, JSONInteger),
            'integer': (int, JSONInteger),
        }
        return Draft4Validator(schema=self.schema, types=types).validate(self)


class JSONObject(dict, JSONBase):

    def __new__(self, mapping=None, schema=None):
        mapping = mapping or {}
        schema = schema or {}
        obj = dict.__new__(JSONObject)
        JSONBase.__init__(obj, schema)
        for name, value in iteritems(mapping):
            obj[name] = value
        return obj

    def __init__(self, mapping=None, schema=None):
        pass

    def __setitem__(self, name, value):
        dict.__setitem__(self, name, wrap(value))

    def _update(self, other_dict):
        dict.__init__(self, other_dict)


class JSONArray(list, JSONBase):

    def __new__(self, iterable=None, schema=None):
        iterable = iterable or []
        schema = schema or {}
        obj = list.__new__(JSONArray)
        JSONBase.__init__(obj, schema)
        for value in iterable:
            obj.append(wrap(value))
        return obj

    def __init__(self, iterable=None, schema=None):
        pass

    def __setitem__(self, index, value):
        list.__setitem__(self, index, wrap(value))

    def __setslice__(self, i, j, obj):
        list.__setslice__(self, i, j, [wrap(x) for x in obj])

    def append(self, obj):
        list.append(self, wrap(obj))

    def extend(self, obj):
        list.extend(self, [wrap(x) for x in obj])

    def insert(self, index, obj):
        list.insert(self, index, wrap(obj))

    def _update(self, copy):
        self[:] = copy


class JSONString(str, JSONBase):

    def __new__(cls, iterable=None, schema=None):
        iterable = iterable or ''
        obj = str.__new__(cls, iterable)
        JSONBase.__init__(obj, schema)
        return obj

    def __init__(self, iterable=None, schema=None):
        pass

    def _update(self, other_string):
        raise RuntimeError('JSONString is immutable.')


class JSONNumber(float, JSONBase):

    def __new__(cls, number=None, schema=None):
        number = number or 0
        representation = float.__new__(cls, number)
        JSONBase.__init__(representation, schema)
        return representation

    def __init__(self, number=None, schema=None):
        pass

    def _update(self, other_number):
        raise RuntimeError('JSONNumber is immutable.')


class JSONInteger(int, JSONBase):

    def __new__(cls, number=None, schema=None):
        number = number or 0
        representation = int.__new__(cls, number)
        JSONBase.__init__(representation, schema)
        return representation

    def __init__(self, number=None, schema=None):
        pass

    def _update(self, other_integer):
        raise RuntimeError('JSONInteger is immutable.')
