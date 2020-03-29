from rpytest import ft
import pytest

#
# abstract.h
#


class MyBadAbstract(ft.Abstract):
    pass


def test_bad_abstract():
    m = MyBadAbstract()

    with pytest.raises(RuntimeError):
        m.mustOverrideMe()


class MyGoodAbstract(ft.Abstract):
    def mustOverrideMe(self):
        return 0x3


def test_good_abstract():
    m = MyGoodAbstract()
    assert m.mustOverrideMe() == 0x3


#
# static_only.h
#


def test_static_only():

    # shouldn't be able to construct
    with pytest.raises(TypeError):
        ft.StaticOnly()

    # should be able to call static
    assert ft.StaticOnly.callme() == 0x56
