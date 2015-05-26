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

import weakref

from jinja import Environment
from six import iteritems
from six import itervalues
from jsonpath_rw import parse
from jsonschema import Draft4Validator
from werkzeug.utils import import_string


def wrap(value, value_schema, root, parent):

    if isinstance(value, JSONBase) or isinstance(value, bool) or \
            value is None:
        # There is no representation of None and booleans as JSONBase objects.
        return value

    if isinstance(value, dict):
        return JSONObject(value, value_schema, root(), parent())
    elif isinstance(value, list):
        return JSONArray(value, value_schema, root(), parent())
    elif isinstance(value, str):
        return JSONString(value, value_schema, root(), parent())
    elif isinstance(value, int):
        return JSONInteger(value, value_schema, root(), parent())
    elif isinstance(value, float):
        return JSONNumber(value, value_schema, root(), parent())
    raise TypeError('Type not defined in JSON Schema.')


class JSONBase(object):

    def __init__(self, schema=None, root=None, parent=None):
        self.schema = schema or {}
        self.__doc__ = self.schema.get('description', '')
        if root:
            self.root = weakref.ref(root)
        else:
            try:
                self.root = weakref.ref(self)
            except TypeError:
                # Basic type, imitiate weakref
                self.root = lambda: self

        if parent is not None:
            self.parent = weakref.ref(parent)
        else:
            try:
                self.parent = weakref.ref(self)
            except TypeError:
                # Basic type, imitiate weakref
                self.parent = lambda: self

    def search(self, query):
        jsonpath_expr = parse(query)
        result = [match.value for match in jsonpath_expr.find(self)]

        return JSONArray(result, schema={'type': 'array',
                                         'items': [el.schema for
                                                   el in result]})

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
        self._validate_external()
        types = {
            'object': (dict, JSONObject,),
            'array': (list, JSONArray,),
            'string': (str, JSONString,),
            'number': (int, float, JSONNumber, JSONInteger),
            'integer': (int, JSONInteger),
        }
        return Draft4Validator(schema=self.schema, types=types).validate(self)

    def _set_schema(self, schema):
        self.schema = schema

    def _validate_external(self):
        try:
            validation_path = self.schema['validation']
            validation = import_string(validation_path)
            validation(self)
        except KeyError:
            pass


class JSONObject(dict, JSONBase):

    def __new__(cls, mapping=None, schema=None, root=None, parent=None):
        mapping = mapping or {}
        schema = schema or {}
        obj = dict.__new__(JSONObject)
        JSONBase.__init__(obj, schema, root, parent)
        for name, value in iteritems(mapping):
            obj[name] = value
        return obj

    def __init__(self, mapping=None, schema=None, root=None, parent=None):
        pass

    def __getitem__(self, name):
        try:
            item_getter = self.schema['properties'][name]['getter']
        except KeyError:
            try:
                item_template = self.schema['properties'][name]['template']
                item_watch = self.schema['properties'][name]['watch']
            except KeyError:
                return dict.__getitem__(self, name)

            template = Environment().from_string(item_template)

            return template.render({k: self.root()._get_from_path(v) for (k, v)
                                    in iteritems(item_watch)})

        getter = import_string(item_getter)
        return getter(self)

    def __setitem__(self, name, value):
        try:
            item_setter = self.schema['properties'][name]['setter']
        except KeyError:
            item_schema = self.schema.get('properties', {}).get(name, None)
            return dict.__setitem__(self, name, wrap(value, item_schema,
                                                     self.root, lambda: self))

        setter = import_string(item_setter)
        setter(self, name, value)

    def _set_schema(self, schema):
        self.schema = schema
        for name, value in iteritems(self):
            value._set_schema(schema.get('properties', {}).get(name, None))

    def _update(self, other_dict):
        dict.__init__(self, other_dict)

    def _validate_external(self):
        JSONBase._validate_external(self)
        for value in itervalues(self):
            value._validate_external()

    def get(self, value, default=None):
        try:
            return self[value]
        except KeyError:
            return default

    def _get_from_path(self, path):
        split_path = path.split('.')
        current = self
        for key in split_path:
            current = current[key]
        return current


class JSONArray(list, JSONBase):

    def __new__(cls, iterable=None, schema=None, root=None, parent=None):
        iterable = iterable or []
        schema = schema or {}
        obj = list.__new__(JSONArray)
        JSONBase.__init__(obj, schema, root, parent)
        for value in iterable:
            obj.append(value)
        return obj

    def __init__(self, iterable=None, schema=None, root=None, parent=None):
        pass

    def __setitem__(self, index, value):
        list.__setitem__(self, index, wrap(value, self._get_schema(index),
                         self.root, lambda: self))

    def __setslice__(self, i, j, obj):
        # O(n)!
        list.__setslice__(self, i, j, [wrap(x, self._get_schema(i + index),
                          self.root, lambda: self) for
                          index, x in enumerate(obj)])
        self._recompute_schemas(i + len(obj))

    def append(self, obj):
        list.append(self, wrap(obj, self._get_schema(max(len(self), 0)),
                    self.root, lambda: self))

    def extend(self, obj):
        list.extend(self, [wrap(x, self._get_schema(index), self.root,
                           lambda: self) for index, x in enumerate(obj)])

    def insert(self, index, obj):
        # O(n)!
        index = max(min(len(self), index), -len(self))
        if index < 0:
            index = len(self) + index
        list.insert(self, index, wrap(obj, self._get_schema(index), self.root,
                                      lambda: self))
        self._recompute_schemas(index)

    def _get_schema(self, index):
        subschema = self.schema.get('items', None)
        if isinstance(subschema, dict):
            return subschema
        elif isinstance(subschema, list):
            index = len(subschema) + index if index < 0 else index
            if len(subschema) > index:
                return subschema[index]
            else:
                return None

    def _recompute_schemas(self, index):
        # Recompute the schema starting from the element next to the one
        # indicated by index.
        length = len(self)
        index = length + index if index < 0 else index
        while index < length:
            self[index]._set_schema(self._get_schema(index))
            index = index + 1

    def _set_schema(self, schema):
        self.schema = schema
        for index, value in enumerate(self):
            value._set_schema(self._get_schema(index))

    def _update(self, copy):
        self[:] = copy

    def _validate_external(self):
        JSONBase._validate_external(self)
        for item in self:
            item._validate_external()


class JSONString(str, JSONBase):

    def __new__(cls, iterable=None, schema=None, root=None, parent=None):
        iterable = iterable or ''
        obj = str.__new__(cls, iterable)
        JSONBase.__init__(obj, schema, root, parent)
        return obj

    def __init__(self, iterable=None, schema=None, root=None, parent=None):
        pass

    def _update(self, other_string):
        raise RuntimeError('JSONString is immutable.')


class JSONNumber(float, JSONBase):

    def __new__(cls, number=None, schema=None, root=None, parent=None):
        number = number or 0
        representation = float.__new__(cls, number)
        JSONBase.__init__(representation, schema, root, parent)
        return representation

    def __init__(self, number=None, schema=None, root=None, parent=None):
        pass

    def _update(self, other_number):
        raise RuntimeError('JSONNumber is immutable.')


class JSONInteger(int, JSONBase):

    def __new__(cls, number=None, schema=None, root=None, parent=None):
        number = number or 0
        representation = int.__new__(cls, number)
        JSONBase.__init__(representation, schema, root, parent)
        return representation

    def __init__(self, number=None, schema=None, root=None, parent=None):
        pass

    def _update(self, other_integer):
        raise RuntimeError('JSONInteger is immutable.')
