from swtest_base._module import add_to_inty
from sw_caster_consumer._module import add_more_to_inty


def test_add_to_inty():
    assert add_to_inty(1, 2) == 3


def test_add_more_to_inty():
    assert add_more_to_inty(1, 2) == 3
