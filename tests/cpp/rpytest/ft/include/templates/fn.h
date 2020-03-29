
#pragma once

struct TClassWithFn
{
    template <typename T>
    static T getT(T t)
    {
        return t;
    }
};
