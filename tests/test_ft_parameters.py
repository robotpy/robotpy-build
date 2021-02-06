from rpytest import ft


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
