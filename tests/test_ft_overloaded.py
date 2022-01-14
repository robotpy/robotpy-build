from rpytest import ft


def test_overloaded():
    class PyOB(ft.OB):
        def init(self, init):
            return f"PyOB => {init.doInit()}"

    class PyOC(ft.OC):
        def init(self, init):
            return f"PyOC => {init.doInit()}"

    class PyOG(ft.OG):
        def init(self, init):
            return f"PyOG => {init.doInit()}"

    obinit = ft.OBInitializer()
    ocinit = ft.OCInitializer()

    ob = PyOB()
    assert ob.init(obinit) == "PyOB => OBInitializer"
    assert ft.OBinitOB(ob, obinit) == "PyOB => OBInitializer"
    assert ft.OBinitOB(ob, ocinit) == "PyOB => OCInitializer"

    oc = PyOC()
    assert oc.init(obinit) == "PyOC => OBInitializer"
    assert oc.init(ocinit) == "PyOC => OCInitializer"
    assert ft.OCinitOB(oc, obinit) == "PyOC => OBInitializer"
    assert ft.OCinitOC(oc, obinit) == "PyOC => OBInitializer"
    assert ft.OCinitOC(oc, ocinit) == "PyOC => OCInitializer"

    og = PyOG()
    assert og.init(obinit) == "PyOG => OBInitializer"
    assert og.init(ocinit) == "PyOG => OCInitializer"
    assert ft.OCinitOB(og, obinit) == "PyOG => OBInitializer"
    assert ft.OCinitOC(og, obinit) == "PyOG => OBInitializer"
    assert ft.OCinitOC(og, ocinit) == "PyOG => OCInitializer"
    # assert ft.OGinitOB(og, obinit) == "PyOG => OBInitializer"
    assert ft.OGinitOC(og, ocinit) == "PyOG => OCInitializer"

    og = ft.OG()
    # assert og.init(obinit) == "" # scope resolution would fail in C++, won't work here either
    assert og.init(ocinit) == "OG::Init(OCInitializer &init) => OCInitializer"
