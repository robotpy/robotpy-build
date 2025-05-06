#pragma once

#include <inty.h>

inline inty add_more_to_inty(inty v, long value) {
    v.long_value += value;
    return v;
}
