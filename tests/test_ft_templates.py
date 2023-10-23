from rpytest import ft


def test_basic_template():
    """template/basic.h"""
    s = ft.TBasicString()

    s.setT("string")
    assert s.t == "string"
    assert s.getT() == "string"


def test_dependent_using():
    du = ft.TDependentUsingInt()
    assert du.getThird([1, 2, 3]) == 3


def test_dependent_using2():
    du = ft.TDependentUsing2Int()
    assert du.getThird([1, 2, 3]) == 3


def test_classwithfn():
    assert ft.TClassWithFn.getT(1) == 1
    assert ft.TClassWithFn.getT(False) is False


def test_nested_template():
    """template/nested.h"""
    i = ft.TOuter.Inner()
    assert type(i.t) == int


def test_numeric():
    """template/numeric.h"""
    b4 = ft.TBaseGetN4()
    assert b4.getIt() == 4

    b6 = ft.TBaseGetN6()
    assert b6.getIt() == 6

    c4 = ft.TChildGetN4()
    assert c4.getIt() == 4

    c6 = ft.TChildGetN6()
    assert c6.getIt() == 6


#
# CRTP handling tests
#


def test_crtp_base():
    b = ft.TBase()
    assert b.baseFn() == 42
    assert b.get() == "TBase"


def test_crtp_concrete():
    c = ft.TConcrete()
    assert c.concrete() == 32
    assert c.baseFn() == 42
    assert c.get() == "TCrtp"


#
# Template base weirdness
#


def test_tvbase2():
    p = ft.TVParam2()
    assert p.get() == 2

    b = ft.TVBase2()
    assert b.get(p) == "TVBase 2"

    c = ft.TVChild2()
    assert c.get(p) == "TVChild 2"
