from rpytest import ft
import pytest


# C++ check functions
getBaseOnly = ft.IBase.getBaseOnly
getBaseAndChild = ft.IBase.getBaseAndChild
getBaseAndPyChild = ft.IBase.getBaseAndPyChild
getBaseAndChildFinal = ft.IBase.getBaseAndChildFinal
getBaseAndGrandchild = ft.IBase.getBaseAndGrandchild


class PyIBase(ft.IBase):
    def baseOnly(self):
        return "pyibase::baseOnly"


def test_inheritance_base():

    # create a base, check its virtual methods
    b = ft.IBase()
    assert b.baseOnly() == "base::baseOnly"
    assert b.baseAndChild() == "base::baseAndChild"
    assert b.baseAndPyChild() == "base::baseAndPyChild"
    assert b.baseAndChildFinal() == "base::baseAndChildFinal"
    assert b.baseAndGrandchild() == "base::baseAndGrandchild"

    # C++ function should see the same thing
    assert getBaseOnly(b) == "base::baseOnly"
    assert getBaseAndChild(b) == "base::baseAndChild"
    assert getBaseAndPyChild(b) == "base::baseAndPyChild"
    assert getBaseAndChildFinal(b) == "base::baseAndChildFinal"
    assert getBaseAndGrandchild(b) == "base::baseAndGrandchild"


def test_inheritance_pybase():

    # Overridden version should be the same
    pyb = PyIBase()
    assert pyb.baseOnly() == "pyibase::baseOnly"
    assert pyb.baseAndChild() == "base::baseAndChild"
    assert pyb.baseAndPyChild() == "base::baseAndPyChild"
    assert pyb.baseAndChildFinal() == "base::baseAndChildFinal"
    assert pyb.baseAndGrandchild() == "base::baseAndGrandchild"

    # C++ function should see the same thing
    assert getBaseOnly(pyb) == "pyibase::baseOnly"
    assert getBaseAndChild(pyb) == "base::baseAndChild"
    assert getBaseAndPyChild(pyb) == "base::baseAndPyChild"
    assert getBaseAndChildFinal(pyb) == "base::baseAndChildFinal"
    assert getBaseAndGrandchild(pyb) == "base::baseAndGrandchild"


def test_inheritance_child():

    # child
    c = ft.IChild()
    assert c.baseOnly() == "base::baseOnly"
    assert c.baseAndChild() == "child::baseAndChild"
    assert c.baseAndPyChild() == "base::baseAndPyChild"
    assert c.baseAndChildFinal() == "child::baseAndChildFinal"
    assert c.baseAndGrandchild() == "base::baseAndGrandchild"

    assert c.getI() == 42

    # C++ function should see the same thing
    assert getBaseOnly(c) == "base::baseOnly"
    assert getBaseAndChild(c) == "child::baseAndChild"
    assert getBaseAndPyChild(c) == "base::baseAndPyChild"
    assert getBaseAndChildFinal(c) == "child::baseAndChildFinal"
    assert getBaseAndGrandchild(c) == "base::baseAndGrandchild"


class PyIChild(ft.IChild):
    def baseAndChild(self):
        return "pyichild::baseAndChild"

    def baseAndPyChild(self):
        return "pyichild::baseAndPyChild"

    # baseAndChildFinal is final, so even though it's overridden here, it won't
    # work in C++ land
    # .. would be nice if the pybind11 metaclass detected that, but probably
    #    will never happen
    def baseAndChildFinal(self):
        return "pyichild::baseAndChildFinal"


def test_inheritance_pychild():
    # child
    pyc = PyIChild()
    assert pyc.baseOnly() == "base::baseOnly"
    assert pyc.baseAndChild() == "pyichild::baseAndChild"
    assert pyc.baseAndPyChild() == "pyichild::baseAndPyChild"
    assert pyc.baseAndChildFinal() == "pyichild::baseAndChildFinal"
    assert pyc.baseAndGrandchild() == "base::baseAndGrandchild"

    assert pyc.getI() == 42

    # C++ function should see the same thing, except the final function is broken
    assert getBaseOnly(pyc) == "base::baseOnly"
    assert getBaseAndChild(pyc) == "pyichild::baseAndChild"
    assert getBaseAndPyChild(pyc) == "pyichild::baseAndPyChild"
    assert getBaseAndChildFinal(pyc) == "child::baseAndChildFinal"
    assert getBaseAndGrandchild(pyc) == "base::baseAndGrandchild"


def test_inheritance_grandchild():
    # grandchild
    g = ft.IGrandChild()
    assert g.baseOnly() == "base::baseOnly"
    assert g.baseAndChild() == "child::baseAndChild"
    assert g.baseAndPyChild() == "base::baseAndPyChild"
    assert g.baseAndChildFinal() == "child::baseAndChildFinal"
    assert g.baseAndGrandchild() == "grandchild::baseAndGrandchild"

    # C++ function should see the same thing
    assert getBaseOnly(g) == "base::baseOnly"
    assert getBaseAndChild(g) == "child::baseAndChild"
    assert getBaseAndPyChild(g) == "base::baseAndPyChild"
    assert getBaseAndChildFinal(g) == "child::baseAndChildFinal"
    assert getBaseAndGrandchild(g) == "grandchild::baseAndGrandchild"


def test_inheritance_pygrandchild():

    # grandchild is final, so we cannot inherit from it
    with pytest.raises(TypeError):

        class PyGrandChild(ft.IGrandChild):
            pass


def test_inheritance_mchild():

    # child
    c = ft.IMChild()
    assert c.baseOnly() == "base::baseOnly"
    assert c.baseAndChild() == "mchild::baseAndChild"
    assert c.baseAndChildFinal() == "mchild::baseAndChildFinal"
    assert c.baseAndGrandchild() == "base::baseAndGrandchild"

    # assert c.getI() == 42

    # C++ function should see the same thing
    assert getBaseOnly(c) == "base::baseOnly"
    assert getBaseAndChild(c) == "mchild::baseAndChild"
    assert getBaseAndChildFinal(c) == "mchild::baseAndChildFinal"
    assert getBaseAndGrandchild(c) == "base::baseAndGrandchild"


class PyIMChild(ft.IMChild):
    def baseAndChild(self):
        return "pymchild::baseAndChild"

    def baseAndPyChild(self):
        return "pymchild::baseAndPyChild"

    # baseAndChildFinal is final, so even though it's overridden here, it won't
    # work in C++ land
    # .. would be nice if the pybind11 metaclass detected that, but probably
    #    will never happen
    def baseAndChildFinal(self):
        return "pymchild::baseAndChildFinal"


def test_inheritance_pymchild():
    # child
    pyc = PyIMChild()
    assert pyc.baseOnly() == "base::baseOnly"
    assert pyc.baseAndChild() == "pymchild::baseAndChild"
    assert pyc.baseAndPyChild() == "pymchild::baseAndPyChild"
    assert pyc.baseAndChildFinal() == "pymchild::baseAndChildFinal"
    assert pyc.baseAndGrandchild() == "base::baseAndGrandchild"

    # C++ function should see the same thing, except the final function can't be overridden by python
    assert getBaseOnly(pyc) == "base::baseOnly"
    assert getBaseAndChild(pyc) == "pymchild::baseAndChild"
    assert getBaseAndPyChild(pyc) == "pymchild::baseAndPyChild"
    assert getBaseAndChildFinal(pyc) == "mchild::baseAndChildFinal"
    assert getBaseAndGrandchild(pyc) == "base::baseAndGrandchild"
