from rpytest import ft
import pytest
import re

#
# main module
#


def test_raise_from():
    with pytest.raises(ValueError) as excinfo:
        ft.raise_from()
    assert str(excinfo.value) == "outer"
    assert str(excinfo.value.__cause__) == "inner"


def test_raise_from_already_set():
    with pytest.raises(ValueError) as excinfo:
        ft.raise_from_already_set()
    assert str(excinfo.value) == "outer"
    assert str(excinfo.value.__cause__) == "inner"


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


class MyBadPrivateAbstract(ft.PrivateAbstract):
    pass


def test_private_abstract():
    # it's private, you can't call it
    assert not hasattr(ft.PrivateAbstract, "_mustOverrideMe")


def test_bad_private_abstract():
    m = MyBadPrivateAbstract()

    with pytest.raises(
        RuntimeError,
        match=r".*"
        + re.escape(
            'does not override required function "PrivateAbstract::_mustOverrideMe"'
        ),
    ):
        ft.PrivateAbstract.getPrivateOverride(m)


class MyGoodPrivateAbstract(ft.PrivateAbstract):
    def _mustOverrideMe(self):
        return 0x3


def test_good_private_abstract():
    m = MyGoodPrivateAbstract()
    assert m._mustOverrideMe() == 0x3
    assert ft.PrivateAbstract.getPrivateOverride(m) == 0x3


#
# buffers.h
#


def test_buffers():
    o = ft.Buffers()
    o.set_buffer(b"12345")

    b = bytearray(4)
    l = o.get_buffer1(b)
    assert b == b"1234"
    assert l == 4

    b = bytearray(4)
    l = o.get_buffer2(b)
    assert b == b"1234"
    assert l == 4

    bi = b"2345"
    bo = bytearray(4)
    l = o.inout_buffer(bi, bo)
    assert bo == b"3456"


def test_buffers_v():
    o = ft.Buffers()
    o.v_set_buffer(b"12345")

    b = bytearray(4)
    l = o.v_get_buffer1(b)
    assert b == b"1234"
    assert l == 4

    b = bytearray(4)
    l = o.v_get_buffer2(b)
    assert b == b"1234"
    assert l == 4


#
# factory.h
#


def test_factory():
    o = ft.HasFactory(4)
    assert o.m_x == 5


#
# gilsafe_container.h
#


def test_gilsafe_container():
    ft.GilsafeContainer.check()


#
# inline_code.h
#


def test_inline_code():
    o = ft.InlineCode()
    assert o.get2() == 2
    assert o.get4() == 4


def test_cpp_code_with_constant():
    o = ft.InlineCode()
    assert o.cpp_code_with_constant() == 4


#
# ns_class.h
#


def test_ns_class():
    assert ft._rpytest_ft.NSClass().getN() == 4


#
# operators.h
#


def test_operators_eq():
    o1 = ft.HasOperator(1)
    o1a = ft.HasOperator(1)
    o2 = ft.HasOperator(2)

    assert o1 == o1a
    assert not (o1 == o2)
    assert o1 != o2


def test_operators_eq2():
    o1 = ft.HasOperatorNoDefault(1)
    o1a = ft.HasOperatorNoDefault(1)
    o2 = ft.HasOperatorNoDefault(2)

    assert o1 == o1a
    assert not (o1 == o2)
    assert o1 != o2


#
# static_only.h
#


def test_static_only():
    # shouldn't be able to construct
    with pytest.raises(TypeError):
        ft.StaticOnly()

    # should be able to call static
    assert ft.StaticOnly.callme() == 0x56


#
# using.h / using2.h
#


def test_using_fwddecl():
    f = ft.FwdDecl()
    f.x = 42
    u = ft.Using4()
    assert u.getX(f) == 43


#
# virtual_xform.h
#
# Check to see that python and C++ see different things for each type
# - py: () -> str
# - C++ (stringstream&) -> void
#


def test_virtual_xform():
    base = ft.VBase()

    with pytest.raises(RuntimeError):
        assert base.pure_io() == "ohai"

    with pytest.raises(RuntimeError):
        assert ft.check_pure_io(base)

    assert base.impure_io() == "py vbase impure + c++ vbase impure"
    assert ft.check_impure_io(base) == "c++ vbase impure"

    assert base.different_cpp_and_py(1) == 3
    assert ft.check_different_cpp_and_py(base, 1) == 2

    class PyChild(ft.VBase):
        def pure_io(self) -> str:
            return "pychild pure"

        def impure_io(self) -> str:
            return "pychild impure"

    pychild = PyChild()
    assert pychild.pure_io() == "pychild pure"
    assert ft.check_pure_io(pychild) == "vbase-xform-pure pychild pure"

    assert pychild.impure_io() == "pychild impure"
    assert ft.check_impure_io(pychild) == "vbase-xform-impure pychild impure"

    child = ft.VChild()

    assert child.pure_io() == "py vchild pure + c++ vchild pure"
    assert ft.check_pure_io(child) == "c++ vchild pure"

    assert child.impure_io() == "py vchild impure + c++ vchild impure"
    assert ft.check_impure_io(child) == "c++ vchild impure"

    class PyGrandChild(ft.VChild):
        def pure_io(self) -> str:
            return "pygrandchild pure"

        def impure_io(self) -> str:
            return "pygrandchild impure"

    pygrandchild = PyGrandChild()

    assert pygrandchild.pure_io() == "pygrandchild pure"
    assert ft.check_pure_io(pygrandchild) == "vchild-xform-pure pygrandchild pure"

    assert pygrandchild.impure_io() == "pygrandchild impure"
    assert ft.check_impure_io(pygrandchild) == "vchild-xform-impure pygrandchild impure"


#
# Misc
#


# ensure that not calling __init__ from a inherited class raises TypeError
def test_init_raises():
    called = [False]

    class PyGoodAbstract(ft.Abstract):
        def __init__(self):
            called[0] = True

    with pytest.raises(TypeError):
        PyGoodAbstract()
    assert called == [True]


def test_subpkg():
    from rpytest.ft.subpkg import SPClass
