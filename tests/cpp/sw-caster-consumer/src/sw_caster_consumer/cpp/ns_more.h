#pragma once

#include <ns_inty.h>

namespace ns {

inline inty2 add_more_to_inty2(inty2 v, long value) {
    v.long_value += value;
    return v;
}

}
