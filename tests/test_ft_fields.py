from rpytest.ft import ClassWithFields


def test_fields():

    c = ClassWithFields()

    assert "should_be_ignored" not in dir(c)
    assert "array_of_two" in dir(c)

    assert len(c.array_of_two) == 2
    assert c.array_of_two[0] == 0x10
    assert c.array_of_two[1] == 0x22

    c.array_of_two[1] = 0x42
    assert c.get_array_of_two(1) == 0x42

    assert c.const_field == 3

    assert ClassWithFields.static_int == 4
    ClassWithFields.static_int = 44
    assert ClassWithFields.static_int == 44

    assert ClassWithFields.static_const == 5
    assert ClassWithFields.static_constexpr == 6

    assert c.actual_int == 2
    assert c.ref_int == 2

    c.actual_int = 3
    assert c.ref_int == 3

    # TODO: this probably has subtle issues, should always
    #       be readonly?
    c.ref_int = 4
    assert c.actual_int == 4
