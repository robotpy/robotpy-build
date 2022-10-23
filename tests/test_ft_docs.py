import inspect
from rpytest import ft


def test_docstrings():

    assert inspect.getdoc(ft.DocEnum) == inspect.cleandoc(
        """
        An enum that is documented
        Maybe it's not great docs, but it's something.

        Members:

          Value1 : value 1 doc
        
          Value2 : value 2 doc??
        """
    )

    assert inspect.getdoc(ft.DocClass) == inspect.cleandoc(
        """
        A class with documentation
        The docs are way cool.
        """
    )
    assert inspect.getdoc(ft.DocClass.fn) == inspect.cleandoc(
        """
        fn(self: rpytest.ft._rpytest_ft.DocClass) -> None
        
        Function with docstring for good measure
        """
    )
    assert (
        inspect.getdoc(ft.DocClass.sweet_var)
        == "An awesome variable, use it for something"
    )

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
