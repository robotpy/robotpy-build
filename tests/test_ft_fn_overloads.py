from rpytest import ft


def test_overloads():
    assert ft.fnOverload(1) == 1
    assert ft.fnOverload(1, 2) == 2
