
#pragma once

#include <rpyint.h>

int convertRpyintToInt(rpy::rpyint &i) {
    return i.int_value;
}
