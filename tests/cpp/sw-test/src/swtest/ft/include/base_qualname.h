
#pragma once

#include "base_qualname_hidden.h"

namespace bq::detail {

struct BaseQualname : public Hidden {
    BaseQualname() = default;
};

struct THBaseQualname : THiddenBase1<THiddenBase2<int>> {
    THBaseQualname() = default;
    virtual ~THBaseQualname() = default;
};



//
// Visible base (shouldn't require base_qualname override)
//

template <typename T>
struct TVisibleBase1 {
    TVisibleBase1() = default;
    virtual ~TVisibleBase1() = default;
};

template <typename T>
struct TVisibleBase2 {
    TVisibleBase2() = default;
    virtual ~TVisibleBase2() = default;
};

struct TVBaseQualname : TVisibleBase1<TVisibleBase2<int>> {
    TVBaseQualname() = default;
};


};
