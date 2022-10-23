from rpytest.ft import ClassWithTrampoline


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
