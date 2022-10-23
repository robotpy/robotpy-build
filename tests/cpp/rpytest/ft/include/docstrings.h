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

  /**
   * Construct a Ramsete unicycle controller.
   *
   * Tuning parameter (b > 0 rad²/m²) for which larger values make
   *
   *             convergence more aggressive like a proportional term.
   * Tuning parameter (0 rad⁻¹ < zeta < 1 rad⁻¹) for which larger
   *             values provide more damping in response.
   */
    void utf8_docstring() {}
};

/// This function returns something very important
[[nodiscard]]
int important_retval() { return 42; }
