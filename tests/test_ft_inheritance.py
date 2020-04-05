from rpytest import ft
import pytest


# C++ check functions
getBaseOnly = ft.IBase.getBaseOnly
getBaseAndChild = ft.IBase.getBaseAndChild
getBaseAndGrandchild = ft.IBase.getBaseAndGrandchild


class PyIBase(ft.IBase):
    def baseOnly(self):
        return "pyibase::baseOnly"


def test_inheritance_base():

    # create a base, check its virtual methods
    b = ft.IBase()
    assert b.baseOnly() == "base::baseOnly"
    assert b.baseAndChild() == "base::baseAndChild"
    assert b.baseAndGrandchild() == "base::baseAndGrandchild"

    # C++ function should see the same thing
    assert getBaseOnly(b) == "base::baseOnly"
    assert getBaseAndChild(b) == "base::baseAndChild"
    assert getBaseAndGrandchild(b) == "base::baseAndGrandchild"


def test_inheritance_pybase():

    # Overridden version should be the same
    pyb = PyIBase()
    assert pyb.baseOnly() == "pyibase::baseOnly"
    assert pyb.baseAndChild() == "base::baseAndChild"
    assert pyb.baseAndGrandchild() == "base::baseAndGrandchild"

    # C++ function should see the same thing
    assert getBaseOnly(pyb) == "pyibase::baseOnly"
    assert getBaseAndChild(pyb) == "base::baseAndChild"
    assert getBaseAndGrandchild(pyb) == "base::baseAndGrandchild"


def test_inheritance_child():

    # child
    c = ft.IChild()
    assert c.baseOnly() == "base::baseOnly"
    assert c.baseAndChild() == "child::baseAndChild"
    assert c.baseAndGrandchild() == "base::baseAndGrandchild"

    assert c.getI() == 42

    # C++ function should see the same thing
    assert getBaseOnly(c) == "base::baseOnly"
    assert getBaseAndChild(c) == "child::baseAndChild"
    assert getBaseAndGrandchild(c) == "base::baseAndGrandchild"


class PyIChild(ft.IChild):
    # baseAndChild is final, so even though it's overridden here, it won't
    # work in C++ land
    # .. would be nice if the pybind11 metaclass detected that, but probably
    #    will never happen
    def baseAndChild(self):
        return "pyichild::baseAndChild"


def test_inheritance_pychild():
    # child
    pyc = PyIChild()
    assert pyc.baseOnly() == "base::baseOnly"
    assert pyc.baseAndChild() == "pyichild::baseAndChild"
    assert pyc.baseAndGrandchild() == "base::baseAndGrandchild"

    assert pyc.getI() == 42

    # C++ function should see the same thing, except the final function is broken
    assert getBaseOnly(pyc) == "base::baseOnly"
    assert getBaseAndChild(pyc) == "child::baseAndChild"
    assert getBaseAndGrandchild(pyc) == "base::baseAndGrandchild"


def test_inheritance_grandchild():
    # grandchild
    g = ft.IGrandChild()
    assert g.baseOnly() == "base::baseOnly"
    assert g.baseAndChild() == "child::baseAndChild"
    assert g.baseAndGrandchild() == "grandchild::baseAndGrandchild"

    # C++ function should see the same thing
    assert getBaseOnly(g) == "base::baseOnly"
    assert getBaseAndChild(g) == "child::baseAndChild"
    assert getBaseAndGrandchild(g) == "grandchild::baseAndGrandchild"


def test_inheritance_pygrandchild():

    # grandchild is final, so we cannot inherit from it
    with pytest.raises(TypeError):

        class PyGrandChild(ft.IGrandChild):
            pass
