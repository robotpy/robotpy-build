from rpytest import ft
import pytest

#
# custom_type_caster.h
#


def test_custom_type_caster():
    assert ft.checkConvertRpyintToInt() == 6
    assert ft.convertRpyintToInt(5) == 5
    assert ft.convertRpyintToInt() == 6


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
