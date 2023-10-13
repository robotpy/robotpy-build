#pragma once

#include "tvbase.h"

template <int N>
struct TVChild : TVBase<TVParam<N>> {

    std::string get(TVParam<N> t) const override {
        return "TVChild " + std::to_string(t.get());
    }

};