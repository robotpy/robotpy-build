from rpytest import ft
import pytest


class PyGChild(ft.PChild):
    pass


def test_ft_protection():
    # can create base
    b = ft.PBase()

    assert b.getChannel() == 9

    # protected things are available with leading underscore
    b._setChannel(7)
    assert b.getChannel() == 7

    # child with protected constructor is usable
    c = ft.PChild(1)
    assert c.getChannel() == 1

    # Inheritance of child works
    pyc = PyGChild(2)
    assert pyc.getChannel() == 2
    pyc._setChannel(5)
    assert pyc.getChannel() == 5

    # can create grandchild
    gc = ft.PGChild(3)
    assert gc.getChannel() == 3

    # isinstance works too
    assert isinstance(c, ft.PBase)
    assert isinstance(pyc, ft.PBase)
    assert isinstance(gc, ft.PBase)

    # private final should not fail to compile, and children
    # should still work
    # .. oddly enough the method doesn't get hidden, must be
    #    because of pybind11's inheritance. Probably should fix?

    assert b.privateFinalTestC() == 1
    assert b.privateFinalTestGC() == 10
    assert b.privateOverrideTestC() == 100

    assert c.privateFinalTestC() == 2
    assert c.privateFinalTestGC() == 20
    assert c.privateOverrideTestC() == 200

    # Well, this is an unexpected result, but it works too
    assert gc.privateFinalTestC() == 2
    assert gc.privateFinalTestGC() == 30
    assert gc.privateOverrideTestC() == 200
