from rpytest import ft
import pytest


#
# type_caster.h
#


def test_get123():
    assert ft.get123() == [1, 2, 3]


#
# type_caster_nested.h
#


def test_nested_typecaster():
    nt = ft.NestedTypecaster()
    ll = None

    def fn(l):
        nonlocal ll
        ll = l

    nt.callWithList(fn)
    assert ll == [1, 2]
