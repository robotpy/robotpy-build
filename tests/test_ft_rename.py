from rpytest import ft


def test_rename_fn():
    assert not hasattr(ft._rpytest_ft, "fnOriginal")
    assert ft.fnRenamed() == 0x1
    assert ft.fnRenamedParam(y=4) == 4


def test_rename_cls():
    assert not hasattr(ft._rpytest_ft, "OriginalClass")

    c = ft.RenamedClass()

    assert not hasattr(c, "fnOriginal")
    assert c.fnRenamed() == 0x2
    assert c.fnRenamedParam(y=7) == 7

    assert not hasattr(c, "originalProp")
    assert c.renamedProp == 8
    assert c.getProp() == 8

    c.setProp(9)
    assert c.renamedProp == 9
    assert c.getProp() == 9
    c.renamedProp = 10
    assert c.getProp() == 10

    assert not hasattr(c, "ClassOriginalEnum")
    assert not hasattr(c.ClassRenamedEnum, "Param1")
    assert c.ClassRenamedEnum.P1 == 1


def test_rename_enums():
    assert not hasattr(ft._rpytest_ft, "OriginalEnum")

    assert not hasattr(ft.RenamedEnum, "Original1")
    assert ft.RenamedEnum.Renamed1 == 1
