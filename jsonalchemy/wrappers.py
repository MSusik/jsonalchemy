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

import collections

from six import iteritems
from jsonschema import Draft4Validator
from jsonschema import SchemaError, ValidationError


def validate(data, schema, *args, **kwargs):
    types = {
        'object': (dict, JSONDict),
        'array': (list, JSONList),
        'string': (str, unicode),
    }
    return Draft4Validator(schema=schema, types=types).validate(data)


def wrap(value, value_schema):
    if value_schema:
        value_type = value_schema.get('type', '')
        if value_type == 'object':
            if not isinstance(value, JSONDict):
                return JSONDict(value, value_schema)
        elif value_type == 'array':
            if not isinstance(value, JSONList):
                return JSONList(value, value_schema)
    return value


class JSONBase(object):

    def __init__(self, schema=None):
        self.schema = schema or {}

    def _copy_element(self, element):
        try:
            return element.copy_()
        except AttributeError:
            return element

    @property
    def validation(parent):

        class JSONValidation(parent.__class__):
            def __init__(self, json):
                self._json = json
                super(JSONValidation,
                      self).__init__(parent._copy_element(json))

            def __enter__(self):
                return self

            def __exit__(self, type, value, traceback):
                if not type:
                    # There was no exception
                    validate(self,
                             self._json.schema)
                    self._json.update(self)

        return JSONValidation(parent)


class JSONDict(collections.Mapping, JSONBase):

    def __init__(self, mapping=None, schema=None):
        mapping = mapping or {}
        JSONBase.__init__(self, schema)
        properties = self.schema.get('properties', {})
        self.dict = {
            name: wrap(value, properties.get(name, None))
            for name, value in iteritems(mapping)
        }

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self.dict)

    def __contains__(self, value):
        return value in self.dict

    def __getitem__(self, name):
        return self.dict[name]

    def __setitem__(self, name, value):
        self.dict[name] = value

    def __delitem__(self, name):
        value = self.dict.pop(name)

    def copy_(self):
        return JSONDict({self._copy_element(k): self._copy_element(v) for k, v
                         in iteritems(self.dict)})

    # Implement proper update
    def update(self, other_dict):
        self.dict.update(wrap(other_dict.dict, self.schema))

    def validate(self):
        return validate(self, self.schema)


class JSONList(collections.Iterable, JSONBase):

    def __init__(self, iterable=None, schema=None):
        iterable = iterable or []
        JSONBase.__init__(self, schema)
        value_schema = self.schema.get('items', None)
        self.list = [wrap(value, value_schema) for value in iterable]

    def __getitem__(self, index):
        return self.list[index]

    def __iter__(self):
        return iter(self.list)

    def __len__(self):
        return len(self.list)

    def __eq__(self, value):
        return self.list == value

    def copy_(self):
        return JSONList(map(lambda x: self._copy_element(x), self.list))

    def update(self, copy):
        self.__init__(self, copy, self.schema)

    def validate(self):
        return validate(self, self.schema)
