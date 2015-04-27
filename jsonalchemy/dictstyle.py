from __future__ import unicode_literals

import collections

from copy import deepcopy
from six import iteritems
from werkzeug import MultiDict
from jsonschema import Draft4Validator
from jsonschema import SchemaError, ValidationError


def validate(data, schema, *args, **kwargs):
    types = {
        'object': (dict, JSONDict),
        'array': (list, JSONList),
        'string': (str, unicode),
    }
    return Draft4Validator(schema=schema, types=types).validate(data)


def wrap(value, value_schema, callbacks=None):
    if value_schema:
        value_type = value_schema.get('type', '')
        if value_type == 'object':
            if not isinstance(value, JSONDict):
                return JSONDict(value, value_schema, callbacks)
        elif value_type == 'array':
            if not isinstance(value, JSONList):
                return JSONList(value, value_schema, callbacks)
    return value


class JSONBase(object):

    def __init__(self, schema, callbacks):
        self.schema = schema or {}
        print self.schema
        callbacks = callbacks or getattr(self.__class__, '__callbacks__', {})
        self.callbacks = {}
        self.callbacks.update(callbacks)

    def _copy_element(self, element):
        try:
            return element.copy()
        except AttributeError:
            return element

    @property
    def transaction_delayed(self):

        class JSONTransactionDelayed(object):
            def __init__(self, json):
                self._json = json
                self._copy = self._json.copy()

            def __enter__(self):
                return self._copy

            def __exit__(self, type, value, traceback):
                if not type:
                    # There was no exception
                    validate(self._copy,
                             self._json.schema)
                    self._json.update(self._copy)

        return JSONTransactionDelayed(self)


class JSONDict(collections.Mapping, JSONBase):

    def __init__(self, mapping=None, schema=None, callbacks=None):
        mapping = mapping or {}
        JSONBase.__init__(self, schema, callbacks)
        properties = self.schema.get('properties', {})
        self.dict = {
            name: wrap(value, properties.get(name, None),
                       self.callbacks.get(name, None))
            for name, value in iteritems(mapping)
        }

        validate(self, self.schema)

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self.dict)

    def __contains__(self, value):
        return value in self.dict

    def __getitem__(self, name):
        if name in self.callbacks and callable(self.callbacks[name]):
            return self.callbacks[name](self.dict[name])
        return self.dict[name]

    def __setitem__(self, name, value):
        has_key = name in self.dict
        old_value = self.dict.get(name, None)

        value_schema = self.schema.get('properties', {}).get(name, None)
        value = wrap(value, value_schema)

        self.dict[name] = value

        try:
            validate(self, self.schema)
        except ValidationError as e:
            # rollback the dict modification
            if has_key:
                self.dict[name] = old_value
            else:
                del self.dict[name]
            raise e

    def __delitem__(self, name):
        value = self.dict.pop(name)

        try:
            validate(self, self.schema)
        except ValidationError as e:
            # rollback the dict modification
            self.dict[name] = value
            raise e

    def copy(self):
        return {self._copy_element(k): self._copy_element(v) for k, v
                in self.dict.iteritems()}

    def update(self, other_dict):
        self.dict.update(other_dict)


class JSONList(collections.Iterable, JSONBase):

    def __init__(self, iterable=None, schema=None, callbacks=None):
        iterable = iterable or []
        JSONBase.__init__(self, schema, callbacks)
        value_schema = self.schema.get('items', None)
        # FIXME callbacks per item
        self.list = [wrap(value, value_schema, self.callbacks.get(None, None))
                     for value in iterable]

        validate(self, self.schema)

    def __getitem__(self, index):
        return self.list[index]

    def __iter__(self):
        return iter(self.list)

    def __len__(self):
        return len(self.list)

    def __eq__(self, value):
        return self.list == value

    def copy(self):
        return map(lambda x: self._copy_element(x), self.list)

    def update(self, copy):
        self.__init__(copy, self.schema, self.callbacks)
