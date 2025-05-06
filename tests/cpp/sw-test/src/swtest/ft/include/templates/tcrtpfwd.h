#pragma once

#include "tbase.h"

template <typename T>
struct TCrtpFwd : TBase
{
    std::string get() override
    {
        return "TCrtpFwd";
    }
};
