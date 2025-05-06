
#pragma once

// basic template
template <typename T>
struct TBasic
{
    virtual ~TBasic() {}

    T getT() { return t; }
    virtual void setT(const T &t) { this->t = t; }

    T t;
};

// basic specialization
// - TODO: ignored for now since this is annoying
template <>
struct TBasic<int> {
    int add5() { return 5; }
};
