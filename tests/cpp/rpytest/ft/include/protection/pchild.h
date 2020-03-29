#pragma once
#include "pbase.h"

class PChild : public PBase
{
protected:
    explicit PChild(int channel) : PBase()
    {
        setChannel(channel);
    }
};