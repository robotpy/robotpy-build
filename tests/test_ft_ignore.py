from rpytest import ft


def test_ignore_fn():
    assert not hasattr(ft._rpytest_ft, "fnIgnore")
    assert ft.fnIgnoredParam() == 3


def test_ignore_cls():
    assert not hasattr(ft._rpytest_ft, "IgnoredClass")

    c = ft.ClassWithIgnored()

    assert not hasattr(c, "fnIgnore")
    assert c.fnIgnoredParam(y=4) == 42 + 4

    assert not hasattr(c, "ignoredProp")


def test_ignore_cls_enum():
    assert not hasattr(ft.ClassWithIgnored, "IgnoredInnerEnum")
    assert not hasattr(ft.ClassWithIgnored.InnerEnumWithIgnored, "Param1")
    assert ft.ClassWithIgnored.InnerEnumWithIgnored.Param2 == 2


def test_ignored_enums():
    assert not hasattr(ft._rpytest_ft, "IgnoredEnum")

    assert not hasattr(ft.EnumWithIgnored, "Ignored")
    assert ft.EnumWithIgnored.NotIgnored == 1
