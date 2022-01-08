from rpytest import ft


def test_fn_overloads():
    assert ft.fnOverload(1) == 1
    assert ft.fnOverload(1, 2) == 2


def test_cls_overloads():
    oo = ft.OverloadedObject()
    assert oo.overloaded(1) == 0x1
    assert oo.overloaded("bob") == 0x2

    assert oo.overloaded_constexpr(1, 2) == 3
    assert oo.overloaded_constexpr(1, 2, 3) == 6

    assert ft.OverloadedObject.overloaded_static(1) == 0x3
    assert ft.OverloadedObject.overloaded_static("yup") == 0x4
