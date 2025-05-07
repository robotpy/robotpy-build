#pragma once

#include "inty.h"

inline inty add_to_inty(inty v, long value) {
    v.long_value += value;
    return v;
}
