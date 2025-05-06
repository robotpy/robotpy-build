#pragma once

#include <string>

struct TBase
{
    virtual std::string get()
    {
        return "TBase";
    }

    int baseFn()
    {
        return 42;
    }

    virtual ~TBase() {}
};
