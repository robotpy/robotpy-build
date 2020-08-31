
#pragma once

#include <sstream>

struct VBase
{
    virtual void pure_io(std::stringstream &ss) = 0;
    virtual void impure_io(std::stringstream &ss)
    {
        ss << "c++ vbase impure";
    }

    virtual ~VBase() {}
};

struct VChild : public VBase
{
    void pure_io(std::stringstream &ss) override
    {
        ss << "c++ vchild pure";
    }
    void impure_io(std::stringstream &ss) override
    {
        ss << "c++ vchild impure";
    }
};

std::string check_pure_io(VBase *base)
{
    std::stringstream ss;
    base->pure_io(ss);
    return ss.str();
}

std::string check_impure_io(VBase *base)
{
    std::stringstream ss;
    base->impure_io(ss);
    return ss.str();
}
