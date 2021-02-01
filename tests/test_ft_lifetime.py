from rpytest.ft import LTTester, LTWithVirtual
import gc


class PyLTWithVirtual(LTWithVirtual):
    def get_bool(self) -> bool:
        return True


def test_lifetime():
    tester = LTTester()

    # At this point python releases the reference to the created object
    # need to ensure that it stays around as long as the std::shared_ptr
    tester.set_val(PyLTWithVirtual())
    gc.collect()
    assert tester.get_bool() == True
