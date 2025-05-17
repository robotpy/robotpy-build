
#pragma once

struct TClassWithFn
{
    template <typename T>
    static T getT(T t)
    {
        return t;
    }
};

template <int I>
struct TTClassWithFn
{
    template <typename T>
    static T getT(T t)
    {
        return t + I;
    }
};
