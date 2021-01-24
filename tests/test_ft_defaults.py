from rpytest import ft


def test_defaults():
    assert ft.fnSimpleDefaultParam(1) == 4
    assert ft.fnSimpleDefaultParam(2, 3) == 5

    assert ft.fnEmptyDefaultParam() == []
    assert ft.fnEmptyDefaultParam([1, 2]) == [1, 2]
