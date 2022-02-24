# just ensures the module built correctly, nothing fancy
import rpytest.dl


def test_downloaded_fn():
    assert rpytest.dl.downloaded_fn(3) == 0x42 + 3


def test_extra_content():
    assert rpytest.dl.extra_content() == True
