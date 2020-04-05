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
