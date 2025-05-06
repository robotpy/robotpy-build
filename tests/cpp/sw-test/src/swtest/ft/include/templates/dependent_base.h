#pragma once

// Template class that has a non-template base class in the same file

struct TDBase  {
    virtual ~TDBase() {}
};

template <typename T>
struct TDChild : TDBase {};
