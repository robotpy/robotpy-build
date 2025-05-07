#pragma once

template <int N>
struct TBaseGetN
{
    virtual ~TBaseGetN() {}
    int getIt()
    {
        return N;
    }
};

struct TChildGetN4 : TBaseGetN<4>
{
};

template <int N>
struct TChildGetN : TBaseGetN<N>
{
};