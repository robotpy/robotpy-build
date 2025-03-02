from ..setup import Setup


def get_setup() -> Setup:
    s = Setup()
    s.prepare()
    return s
