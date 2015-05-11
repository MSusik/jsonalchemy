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

"""Test wrappers."""

from __future__ import absolute_import

import json
import pytest

from jsonalchemy.utils import load_schema_from_url
from jsonalchemy.wrappers import JSONArray
from jsonalchemy.wrappers import JSONInteger
from jsonalchemy.wrappers import JSONNumber
from jsonalchemy.wrappers import JSONObject
from jsonalchemy.wrappers import JSONString

from jsonschema import SchemaError
from jsonschema import ValidationError
from jsonschema.exceptions import UnknownType

from helpers import abs_path


def test_constructor():
    """Empty or falsy arguments create empty wrappers."""
    assert JSONObject() == {}
    assert JSONObject({}) == {}
    assert JSONObject(None, {}) == {}


def test_malformed_schema():
    """Malformed schemas raise a ValueError on creation."""
    with pytest.raises(ValueError):
        schema = load_schema_from_url(abs_path('schemas/missing_bracket.json'))


def test_unknown_type():
    """Instances of types that aren't mapped to JSONBase raise on wrapping."""
    with pytest.raises(TypeError) as excinfo:
        data = JSONObject({'1': lambda x: x})

    assert 'Type not defined' in str(excinfo.value)


def test_invalid_type():
    """Schemas with invalid types raise UnknownType on use."""
    schema = load_schema_from_url(abs_path('schemas/invalid_type.json'))
    invalid_data = {'my_field': 'test'}

    data = JSONObject(invalid_data, schema)

    with pytest.raises(UnknownType):
        data.validate()


def test_data_load():
    """Wrappers can load data."""
    schema = load_schema_from_url(abs_path('schemas/simple.json'))
    valid_data = {'my_field': 'test'}
    invalid_type_data = {'my_field': 1}
    wrong_field_data = {'wrong_field': 'test'}

    data = JSONObject(valid_data, schema)

    assert 'my_field' in data
    assert set(data.keys()) == set(['my_field'])
    assert data['my_field'] == valid_data['my_field']

    with pytest.raises(ValidationError):
        JSONObject(invalid_type_data, schema=schema).validate()

    with pytest.raises(ValidationError):
        JSONObject(wrong_field_data, schema=schema).validate()


def test_data_set():
    """Wrappers can set data."""
    schema = load_schema_from_url(abs_path('schemas/simple.json'))

    empty_data = JSONObject(schema=schema)
    empty_data['my_field'] = 'valid value'
    assert empty_data['my_field'] == 'valid value'

    with pytest.raises(ValidationError):
        with empty_data.validation as d:
            d['my_field'] = 666
    assert empty_data['my_field'] != 666


def test_data_delete():
    """Wrappers can delete data."""
    schema = load_schema_from_url(abs_path('schemas/required_field.json'))

    data = JSONObject({
        'identifier': 1,
        'my_field': 'test'
    }, schema=schema)
    del data['identifier']

    with pytest.raises(ValidationError):
        data.validate()

    del data['my_field']
    assert 'my_field' not in data


def test_data_rollback():
    """Wrappers rollback invalid edits."""
    schema = load_schema_from_url(abs_path('schemas/required_field.json'))

    data = JSONObject({
        'identifier': 1,
    }, schema=schema)

    with pytest.raises(ValidationError):
        with data.validation as d:
            d['my_field'] = 666
    assert 'my_field' not in data


def test_array_wrapper():
    """List wrapper works as if it were a list."""
    schema = load_schema_from_url(abs_path('schemas/list.json'))

    data = JSONArray(['foo', 'bar'], schema=schema)

    assert data[0] == 'foo'
    assert len(data) == 2
    assert data == ['foo', 'bar']

    list_data = list(data)
    assert len(list_data) == 2


def test_complex_type_wrapping():
    """Wrappers can be recursively composed."""
    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    data = JSONObject({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    assert data['authors'][0]['family_name'] == 'Ellis'
    assert isinstance(data['authors'], JSONArray)


def test_wrapper_subclass():
    """Subclassing a wrapper preserves its behavior."""
    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    class Record(JSONObject):
        pass

    data = Record({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    assert data['authors'][0]['family_name'] == 'Ellis'
    assert isinstance(data['authors'], JSONArray)


def test_multiple_types_field():
    """Multiple types can be used to define one field."""
    schema = load_schema_from_url(abs_path('schemas/multiple_types.json'))

    data = JSONObject({'idontknowthetype': [[]]}, schema)

    with pytest.raises(ValidationError) as excinfo:
        data.validate()

    assert 'is too short' in str(excinfo.value)

    data['idontknowthetype'][0] = ['str']
    data.validate()

    assert data['idontknowthetype'][0][0].__class__ == JSONString

    data['idontknowthetype'].append({})

    assert data['idontknowthetype'].__class__ == JSONArray
    assert data['idontknowthetype'][-1].__class__ == JSONObject

    with pytest.raises(ValidationError) as excinfo:
        data.validate()

    assert 'is a required property' in str(excinfo.value)

    with data.validation as d:
        d['idontknowthetype'][1]['foo'] = 1

    assert data['idontknowthetype'][1]['foo'].__class__ == JSONInteger


def test_with_statement_no_validation_inbetween():
    """With blocks validate only on __exit__."""
    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    data = JSONObject({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    with data.validation as d:
        d['authors'][0]['family_name'] = 7
        d['authors'][0]['family_name'] = 'Cranmer'

    assert len(data['authors']) == 1
    assert data['authors'][0]['family_name'] == 'Cranmer'
    assert isinstance(data, JSONObject)
    assert isinstance(data['authors'], JSONArray)
    assert isinstance(data['authors'][0], JSONObject)


def test_with_statement_assignment():
    """Assignment in with blocks works as expected."""
    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    data = JSONObject({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    with data.validation as d:
        d['authors'] = [{'family_name': 'Cranmer'}]

    assert len(data['authors']) == 1
    assert data['authors'][0]['family_name'] == 'Cranmer'
    assert isinstance(data, JSONObject)
    assert isinstance(data['authors'], JSONArray)
    assert isinstance(data['authors'][0], JSONObject)


def test_with_statement_raises():
    """When validation of a with block fails, a ValidationError is thrown."""
    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    data = JSONObject({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    with pytest.raises(ValidationError) as excinfo:
        with data.validation as d:
            d['authors'] = 100

    assert 'is not of type' in str(excinfo.value)
    assert data['authors'][0]['family_name'] == 'Ellis'
    assert isinstance(data, JSONObject)
    assert isinstance(data['authors'], JSONArray)
    assert isinstance(data['authors'][0], JSONObject)


def test_with_statement_array():
    """Array assignment in with blocks works as expected."""
    schema = load_schema_from_url(abs_path('schemas/list.json'))

    data = JSONArray(['list0'], schema=schema)

    with data.validation as d:
        d[0] = 7
        d[0] = 'list1'

    assert len(data) == 1
    assert data[0] == 'list1'


def test_array_append():
    """A JSONArray responds to the append method."""
    data = JSONArray([])

    data.append(13.5)
    data.append('13.5')

    assert data[0].__class__ == JSONNumber
    assert data[1].__class__ == JSONString
    assert data[1] == '13.5'


def test_array_extend():
    """A JSONArray responds to the extend method."""
    data = JSONArray([{}])
    data.extend([13.5, '13.5'])

    assert data[0].__class__ == JSONObject
    assert data[1].__class__ == JSONNumber
    assert data[2].__class__ == JSONString
    assert data == [{}, 13.5, '13.5']


def test_array_insert():
    """A JSONArray responds to the insert method."""
    data = JSONArray([1])

    data.insert(0, '2')
    data.insert(3, 2)

    assert data == ['2', 1, 2]
    assert data[0].__class__ == JSONString
    assert data[2].__class__ == JSONInteger


@pytest.mark.parametrize('JSONClass, value, schema',
                         [(JSONString, 'verylongstring',
                           {'type': 'string', 'maxLength': 5}),
                          (JSONNumber, 13.5,
                           {'type': 'number', 'multipleOf': 0.4}),
                          (JSONInteger, 13,
                           {'type': 'integer', 'maximum': 12})])
def test_immutable_validation(JSONClass, value, schema):
    """Immutable types reject invalid data."""
    data = JSONClass(value, schema)

    with pytest.raises(ValidationError) as excinfo:
        data.validate()

    assert isinstance(data, JSONClass)


@pytest.mark.parametrize('JSONClass, value, schema',
                         [(JSONString, 'verylongstring',
                           {'type': 'string', 'maxLength': 15}),
                          (JSONNumber, 13.5,
                           {'type': 'number', 'multipleOf': 0.5}),
                          (JSONInteger, 13,
                           {'type': 'integer', 'maximum': 15})])
def test_immutability(JSONClass, value, schema):
    """Immutable types reject mutations."""
    data = JSONClass(value, schema)

    with pytest.raises(RuntimeError) as excinfo:
        with data.validation as d:
            d = value

    assert 'is immutable' in str(excinfo.value)
