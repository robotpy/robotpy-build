#pragma once

/**
    An enum that is documented

    Maybe it's not great docs, but it's something.
*/
enum DocEnum
{
    /** value 1 doc */
    Value1,
    /** value 2 doc?? */
    Value2,
};

/**
    A class with documentation

    The docs are way cool.
*/
struct DocClass
{
    /** Function with docstring for good measure */
    void fn() {}

    /** An awesome variable, use it for something */
    int sweet_var;
};