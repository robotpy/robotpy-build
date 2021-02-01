from rpytest.ft import ClassWithTrampoline


def test_class_with_trampoline():
    c = ClassWithTrampoline()
    assert c.get42() == 42
