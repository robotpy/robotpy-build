from rpytest import ft


def test_ignore_fn():
    assert not hasattr(ft._rpytest_ft, "fnIgnore")
    assert ft.fnIgnoredParam() == 3


def test_ignore_cls():
    assert not hasattr(ft._rpytest_ft, "IgnoredClass")
    assert not hasattr(ft._rpytest_ft, "IgnoredClassWithEnum")

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


#
# ignored_by_default
#


def test_ignored_by_default_fn():
    assert not hasattr(ft._rpytest_ft, "id_fnIgnore")
    assert ft._rpytest_ft.id_fnEnable() == 2


def test_ignored_by_default_enum():
    assert not hasattr(ft._rpytest_ft, "id_IgnoredEnum")
    assert ft._rpytest_ft.id_EnabledEnum.Param3 == 3


def test_ignored_by_default_class():
    assert not hasattr(ft._rpytest_ft, "id_IgnoreClass")
    o = ft._rpytest_ft.id_EnabledClass()
    assert o.fn() == 3
    assert o.fn_missing() == 4
    assert ft._rpytest_ft.id_EnabledClass.InnerEnum.Param6 == 6
    assert ft._rpytest_ft.id_EnabledClass.InnerEnumMissing.Param7 == 7
