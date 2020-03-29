
#pragma once

template <typename T>
struct TBasic
{
    virtual ~TBasic() {}

    T getT() { return t; }
    virtual void setT(const T &t) { this->t = t; }

    T t;
};