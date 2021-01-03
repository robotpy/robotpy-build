from rpytest import ft


def test_enums():

    # normal enums convert to integers
    assert ft.GEnum.GE1 == 1
    assert ft.NSGEnum.NSGE2 == 2
    assert ft.EnumContainer.InnerEnum.IE1 == 1
    assert ft.NSEnumContainer.InnerEnum.NSIE1 == 1

    # enum class are specific types
    assert "GCE1" in ft.GCEnum.GCE1.__members__
    assert "NSGE2" in ft.NSGCEnum.NSGE2.__members__
    assert "IEC1" in ft.EnumContainer.InnerCEnum.__members__
    assert "NSIEC1" in ft.NSEnumContainer.InnerCEnum.__members__
