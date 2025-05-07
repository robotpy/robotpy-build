
#pragma once
#include "tcrtp.h"

struct TConcrete : TCrtp<TConcrete>
{
    int concrete()
    {
        return 32;
    }
};