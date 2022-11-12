import inspect
from rpytest import ft


def test_docstrings_enum():

    assert inspect.getdoc(ft.DocEnum) == inspect.cleandoc(
        """
        An enum that is documented
        Maybe it's not great docs, but it's something.

        Members:

          Value1 : value 1 doc
        
          Value2 : value 2 doc??
        """
    )


def test_docstrings_cls():
    assert inspect.getdoc(ft.DocClass) == inspect.cleandoc(
        """
        A class with documentation
        The docs are way cool.
        """
    )


def test_docstrings_meth():
    assert inspect.getdoc(ft.DocClass.fn) == inspect.cleandoc(
        """
        fn(self: rpytest.ft._rpytest_ft.DocClass) -> None
        
        Function with docstring for good measure
        """
    )


def test_docstrings_meth_kwd():
    assert inspect.getdoc(ft.DocClass.fn2) == inspect.cleandoc(
        """
        fn2(self: rpytest.ft._rpytest_ft.DocClass, from_: int) -> None
        
        Function with parameter that's a python keyword

        :param from_: The from parameter
        """
    )


def test_docstrings_meth_rename():
    assert inspect.getdoc(ft.DocClass.fn3) == inspect.cleandoc(
        """
        fn3(self: rpytest.ft._rpytest_ft.DocClass, ohai: int) -> None
        
        Function with renamed parameter

        :param ohai: The renamed parameter
        """
    )


def test_docstrings_var():
    assert (
        inspect.getdoc(ft.DocClass.sweet_var)
        == "An awesome variable, use it for something"
    )


def test_docstrings_fn():
    assert inspect.getdoc(ft.important_retval) == inspect.cleandoc(
        """
        important_retval() -> int

        This function returns something very important
        """
    )


def test_docstrings_append():

    assert inspect.getdoc(ft.DocAppendEnum) == inspect.cleandoc(
        """
        An enum that is documented
        Maybe it's not great docs, but it's something.
        Useful extra information about this enum


        Members:

          Value1 : value 1 doc
          Useful extra information about this value
          
        
          Value2 : value 2 doc??
        """
    )

    assert inspect.getdoc(ft.DocAppendClass) == inspect.cleandoc(
        """
        A class with documentation
        The docs are way cool.
        Useful extra information about this sweet class
        """
    )
    assert inspect.getdoc(ft.DocAppendClass.fn) == inspect.cleandoc(
        """
        fn(self: rpytest.ft._rpytest_ft.DocAppendClass) -> None
        
        Function with docstring for good measure
        Useful extra information about this fn
        """
    )
    assert inspect.getdoc(ft.DocAppendClass.sweet_var) == inspect.cleandoc(
        """
        An awesome variable, use it for something
        Useful extra information about this sweet var
        """
    )


def test_docstrings_template():
    assert inspect.getdoc(ft.DocTemplateSet) == "Set docs to this"

    assert inspect.getdoc(ft.DocTemplateAppend) == inspect.cleandoc(
        """
        A templated class
        Extra appended docs
    """
    )
