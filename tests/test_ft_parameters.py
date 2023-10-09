from rpytest import ft
import pytest


def test_array_out():
    assert ft.fnParamArrayOut() == (4, [5, 6, 7])


def test_array_out_w_default():
    assert ft.fnParamArrayOutWithDefault() == (4, [0, 6, 2])


def test_fund_ptr():
    assert ft.fnParamFundPtr(4) == (3, 5)


def test_fund_ref():
    assert ft.fnParamFundRef(6) == (7, 5)


def test_fund_const_ref():
    assert ft.fnParamFundConstRef(1, 2) == 3


def test_fn_disable_none():
    with pytest.raises(TypeError):
        ft.fnParamDisableNone(None)

    assert ft.fnParamDisableNone(ft.Param())


def test_fn_disable_all_none():
    with pytest.raises(TypeError):
        ft.fnParamDisableAllNone(None, None)

    with pytest.raises(TypeError):
        ft.fnParamDisableAllNone(None, ft.Param())

    with pytest.raises(TypeError):
        ft.fnParamDisableAllNone(ft.Param(), None)

    assert ft.fnParamDisableAllNone(ft.Param(), ft.Param())


def _callable():
    pass


def test_fn_auto_disable_none():
    with pytest.raises(TypeError):
        ft.fnParamAutoDisableNone(None)

    assert ft.fnParamAutoDisableNone(_callable)


def test_fn_allow_none():
    assert ft.fnParamAllowNone(_callable)
    assert ft.fnParamAllowNone(None) == False


def test_fn_disable_default():
    assert ft.fnParamDisableDefault(1) == 2
    with pytest.raises(TypeError):
        ft.fnParamDisableDefault()
