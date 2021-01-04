from rpytest import ft


def test_enums():

    # normal enums convert to integers
    assert ft.GEnum.GE1 == 1
    assert ft.NSGEnum.NSGE2 == 2
    assert ft.EnumContainer.InnerEnum.IE1 == 1
    assert ft.NSEnumContainer.InnerEnum.NSIE1 == 1

    # Unnamed enums are hoisted as integers to their scope
    # - not supported yet for globals
    # assert ft._rpytest_ft.UGEX == 7
    # assert ft._rpytest_ft.NSUGEX == 5
    assert ft.EnumContainer.UEX == 4

    # enum class are specific types
    assert "GCE1" in ft.GCEnum.GCE1.__members__
    assert "NSGE2" in ft.NSGCEnum.NSGE2.__members__
    assert "IEC1" in ft.EnumContainer.InnerCEnum.__members__
    assert "NSIEC1" in ft.NSEnumContainer.InnerCEnum.__members__


def test_enum_strip_prefix():
    # 1 isn't a valid identifier, so it's not stripped
    assert ft.StripPrefixEnum.STRIP_1 == 1
    # STRIP_B is converted to B
    assert ft.StripPrefixEnum.B == 2
