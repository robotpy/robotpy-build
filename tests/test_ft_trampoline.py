from swtest_base._module import abaseclass
from swtest.ft._ft import ClassWithTrampoline, ConstexprTrampoline, RemoteTrampoline


def test_class_with_trampoline():
    c = ClassWithTrampoline()
    assert c.get42() == 42

    assert c.fnWithMoveOnlyParam(4) == 4
    assert ClassWithTrampoline.check_moveonly(c) == 7


def test_trampoline_with_mv():
    class PyClassWithTrampoline(ClassWithTrampoline):
        pass

    c = PyClassWithTrampoline()
    assert ClassWithTrampoline.check_moveonly(c) == 7


def test_trampoline_without_mv():
    class PyClassWithTrampoline(ClassWithTrampoline):
        def fnWithMoveOnlyParam(self, i):
            assert i == 7
            return 8

    c = PyClassWithTrampoline()
    assert ClassWithTrampoline.check_moveonly(c) == 8


def test_constexpr_trampoline():
    ConstexprTrampoline()


def test_remote_trampoline():
    a = abaseclass()
    assert a.fn() == "abaseclass"

    r = RemoteTrampoline()
    assert r.fn() == "RemoteTrampoline"

    assert isinstance(r, abaseclass)
