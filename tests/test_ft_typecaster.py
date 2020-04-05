from rpytest import ft
import pytest

#
# type_caster.h
#


def test_get123():
    assert ft.get123() == [1, 2, 3]
