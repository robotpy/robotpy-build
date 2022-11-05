import rpytest.ft._rpytest_ft as ft


def test_refquals_ref():
    r = ft.RefQuals()
    assert ft.refquals_fn1(r) == 1


def test_refquals_move1():
    r = ft.RefQuals()
    assert ft.refquals_fn2(r) == 2


def test_refquals_move_custom():
    class MyRefQuals(ft.RefQuals):
        pass

    r = MyRefQuals()
    assert ft.refquals_fn2(r) == 42


def test_refquals_move2():
    r = ft.RefQuals()

    # This calls our cpp_code override
    assert r.fn3() == 43

    # This still calls the C++ version since we can't override it
    # merely with cpp_code
    assert ft.refquals_fn3(r) == 3
