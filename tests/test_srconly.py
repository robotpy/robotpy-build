# just ensures the source-only module built correctly, nothing fancy
import rpytest.srconly


def test_srconly_fn():
    assert rpytest.srconly.srconly_fn(3) == 3 - 0x42
