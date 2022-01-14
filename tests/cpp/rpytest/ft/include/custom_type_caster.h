
#pragma once

#include <rpyint.h>


int convertRpyintToInt(rpy::rpyint i = rpy::rpyint_plus_5(1)) {
    return i.get();
}

int checkConvertRpyintToInt() {
    return convertRpyintToInt();
}
