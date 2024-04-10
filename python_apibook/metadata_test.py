from copy import deepcopy

import pytest

from .metadata import ClassDetail, Field, FieldKind

_EXPECTED_ATTRS = [
    Field(name="name", type="str", description="Fooobar"),
    Field(name="type", type="str", description="The foobar"),
]


@pytest.mark.parametrize(
    "kind_str, expected",
    [
        ("cvar", FieldKind.CLASS),
        ("ivar", FieldKind.INSTANCE),
        ("var", FieldKind.MODULE),
        ("foobar", FieldKind.UNKNOWN),
    ],
)
def test_fieldkind_from_str(kind_str, expected):
    assert FieldKind.from_str(kind_str) == expected


def test_attribute_nd():
    example = """
    Short docstring.

    Also a long docstring, maybe.

    Attributes
    ----------
    name : str
           Fooobar
    type: str
          The foobar
    """

    assert ClassDetail().with_docstring_source(example).fields == _EXPECTED_ATTRS


def test_attribute_epydoc():
    example = """
    Short docstring.

    Also a long docstring, maybe.

    @cvar name: Fooobar
    @type name: str
    @ivar type: The foobar
    @type type: str
    """
    expected = deepcopy(_EXPECTED_ATTRS)
    expected[0].kind = FieldKind.CLASS
    expected[1].kind = FieldKind.INSTANCE

    assert ClassDetail().with_docstring_source(example).fields == expected


def test_attribute_rst():
    example = """
    Short docstring.

    Also a long docstring, maybe.

    :cvar name str: Fooobar
    :ivar type str: The foobar
    """
    expected = deepcopy(_EXPECTED_ATTRS)
    expected[0].kind = FieldKind.CLASS
    expected[1].kind = FieldKind.INSTANCE

    assert ClassDetail().with_docstring_source(example).fields == expected


def test_attribute_google():
    example = """
    Short docstring.

    Also a long docstring, maybe.

    Attributes:
        name (str): Fooobar
        type (str): The foobar

    """

    assert ClassDetail().with_docstring_source(example).fields == _EXPECTED_ATTRS
