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

from datetime import datetime

from jsonalchemy.utils import load_schema_from_url
from jsonalchemy.wrappers import JSONDict, JSONList

from jsonschema import SchemaError, ValidationError
from jsonschema.exceptions import UnknownType

from helpers import abs_path


def test_constructor():
    """."""
    assert JSONDict() == {}
    assert JSONDict({}) == {}
    assert JSONDict(None, {}) == {}


def test_malformed_schema():
    """Malformed schemas raise a ValueError on creation."""
    with pytest.raises(ValueError):
        schema = load_schema_from_url(abs_path('schemas/missing_bracket.json'))


def test_invalid_type():
    """Schemas with invalid types raise UnknownType on use."""
    schema = load_schema_from_url(abs_path('schemas/invalid_type.json'))
    invalid_data = {'my_field': 'test'}

    data = JSONDict(invalid_data, schema)

    with pytest.raises(UnknownType):
        data.validate()


def test_data_load():
    """Wrappers can load data."""
    schema = load_schema_from_url(abs_path('schemas/simple.json'))
    valid_data = {'my_field': 'test'}
    invalid_type_data = {'my_field': 1}
    wrong_field_data = {'wrong_field': 'test'}

    data = JSONDict(valid_data, schema)

    assert 'my_field' in data
    assert set(data.keys()) == set(['my_field'])
    assert data['my_field'] == valid_data['my_field']

    with pytest.raises(ValidationError):
        JSONDict(invalid_type_data, schema=schema).validate()

    with pytest.raises(ValidationError):
        JSONDict(wrong_field_data, schema=schema).validate()


def test_data_set():
    """Wrappers can set data."""
    schema = load_schema_from_url(abs_path('schemas/simple.json'))

    empty_data = JSONDict(schema=schema)
    empty_data['my_field'] = 'valid value'
    assert empty_data['my_field'] == 'valid value'

    with pytest.raises(ValidationError):
        with empty_data.validation as d:
            d['my_field'] = 666
    assert empty_data['my_field'] != 666


def test_data_delete():
    """Wrappers can delete data."""
    schema = load_schema_from_url(abs_path('schemas/required_field.json'))

    data = JSONDict({
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

    data = JSONDict({
        'identifier': 1,
    }, schema=schema)

    with pytest.raises(ValidationError):
        with data.validation as d:
            d['my_field'] = 666
    assert 'my_field' not in data


def test_list_wrapper():
    """List wrapper works as if it were a list."""
    schema = load_schema_from_url(abs_path('schemas/list.json'))

    data = JSONList(['foo', 'bar'], schema=schema)

    assert data[0] == 'foo'
    assert len(data) == 2
    assert data == ['foo', 'bar']

    list_data = list(data)
    assert len(list_data) == 2


def test_complex_type_wrapping():
    """Wrappers can be recursively composed."""
    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    data = JSONDict({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    assert data['authors'][0]['family_name'] == 'Ellis'
    assert isinstance(data['authors'], JSONList)


def test_wrapper_subclass():
    """Subclassing a wrapper preserves its behavior."""
    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    class Record(JSONDict):
        pass

    data = Record({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    assert data['authors'][0]['family_name'] == 'Ellis'
    assert isinstance(data['authors'], JSONList)


def test_with_statement_no_validation():

    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    data = JSONDict({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    with data.validation as d:
        d['authors'][0]['family_name'] = 7
        d['authors'][0]['family_name'] = 'Cranmer'

    assert len(data['authors']) == 1
    assert data['authors'][0]['family_name'] == 'Cranmer'
    assert isinstance(data, JSONDict)
    assert isinstance(data.dict['authors'], JSONList)
    assert isinstance(data.dict['authors'].list[0], JSONDict)


def test_with_statement_assignment():

    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    data = JSONDict({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    with data.validation as d:
        d['authors'] = [{'family_name': 'Cranmer'}]

    assert len(data['authors']) == 1
    assert data['authors'][0]['family_name'] == 'Cranmer'
    assert isinstance(data, JSONDict)
    assert isinstance(data.dict['authors'], JSONList)
    assert isinstance(data.dict['authors'].list[0], JSONDict)


def test_with_statement_raises():

    schema = load_schema_from_url(abs_path('schemas/complex.json'))

    data = JSONDict({
        'authors': [{'family_name': 'Ellis'}]
    }, schema=schema)

    with pytest.raises(ValidationError) as excinfo:
        with data.validation as d:
            d['authors'] = 100

    assert 'is not of type' in str(excinfo.value)
    assert data.dict['authors'].list[0].dict['family_name'] == 'Ellis'
    assert isinstance(data, JSONDict)
    assert isinstance(data.dict['authors'], JSONList)
    assert isinstance(data.dict['authors'].list[0], JSONDict)


@pytest.mark.xfail
def test_with_statement_list():

    schema = load_schema_from_url(abs_path('schemas/list.json'))

    data = JSONList(['list0'], schema=schema)

    with data.validation as d:
        d[0] = 7
        d[0] = 'list1'

    assert len(data) == 1
    assert data[0] == 'list1'
