from rpytest import ft


def test_mvi_base():
    o = ft.MVIBase()
    assert o.i == 1
    assert o.base_getI() == 1


def test_mvi_child():
    o = ft.MVIChild()
    assert o.i == 1
    assert o.ci == 2
    assert o.base_getI() == 1
    assert o.child_getI() == 1
    assert o.child_getCI() == 2


def test_mvi_gchilda():
    o = ft.MVIGChildA()
    assert o.i == 1
    assert o.ci == 2
    assert o.cia == 3
    assert o.base_getI() == 1
    assert o.child_getI() == 1
    assert o.child_getCI() == 2
    assert o.gchildA_getI() == 1
    assert o.gchildA_getCI() == 2
    assert o.gchildA_getCIA() == 3


def test_mvi_gchildb():
    o = ft.MVIGChildB()
    assert o.i == 1
    assert o.ci == 2
    assert o.cib == 4
    assert o.base_getI() == 1
    assert o.child_getI() == 1
    assert o.child_getCI() == 2
    assert o.gchildB_getI() == 1
    assert o.gchildB_getCI() == 2
    assert o.gchildB_getCIB() == 4


def test_mvi_ggchild():
    o = ft.MVIGGChild()
    assert o.i == 1
    assert o.ci == 2
    assert o.cia == 3
    assert o.cib == 4
    assert o.gi == 5
    assert o.base_getI() == 1
    assert o.child_getI() == 1
    assert o.child_getCI() == 2
    assert o.gchildA_getI() == 1
    assert o.gchildA_getCI() == 2
    assert o.gchildA_getCIA() == 3
    assert o.gchildB_getI() == 1
    assert o.gchildB_getCI() == 2
    assert o.gchildB_getCIB() == 4
    assert o.ggchild_getI() == 1
    assert o.ggchild_getCI() == 2
    assert o.ggchild_getCIA() == 3
    assert o.ggchild_getCIB() == 4
    assert o.ggchild_getGI() == 5


def test_mvi_gggchild():
    o = ft.MVIGGGChild()
    assert o.i == 1
    assert o.ci == 2
    assert o.cia == 3
    assert o.cib == 4
    assert o.gi == 5
    assert o.base_getI() == 1
    assert o.child_getI() == 1
    assert o.child_getCI() == 2
    assert o.gchildA_getI() == 1
    assert o.gchildA_getCI() == 2
    assert o.gchildA_getCIA() == 3
    assert o.gchildB_getI() == 1
    assert o.gchildB_getCI() == 2
    assert o.gchildB_getCIB() == 4
    assert o.ggchild_getI() == 1
    assert o.ggchild_getCI() == 2
    assert o.ggchild_getCIA() == 3
    assert o.ggchild_getCIB() == 4
    assert o.ggchild_getGI() == 5
    assert o.gggchild_getI() == 1
    assert o.gggchild_getCI() == 2
    assert o.gggchild_getCIA() == 3
    assert o.gggchild_getCIB() == 4
    assert o.gggchild_getGI() == 5
