// clang-format off
#pragma once

#include <string>

namespace inheritance
{

struct IBase
{
    IBase() {}
    virtual ~IBase() {}

    virtual std::string baseOnly()
    {
        return "base::baseOnly";
    }

    virtual std::string baseAndGrandchild()
    {
        return "base::baseAndGrandchild";
    }

    virtual std::string baseAndChild()
    {
        return "base::baseAndChild";
    }

    virtual std::string baseAndPyChild()
    {
        return "base::baseAndPyChild";
    }

    virtual std::string baseAndChildFinal()
    {
        return "base::baseAndChildFinal";
    }

    //
    // These static methods are for validating that python objects can override
    // the virtual methods correctly
    //

    static std::string getBaseOnly(IBase *base)
    {
        return base->baseOnly();
    }

    static std::string getBaseAndGrandchild(IBase *base)
    {
        return base->baseAndGrandchild();
    }

    static std::string getBaseAndChild(IBase *base)
    {
        return base->baseAndChild();
    }

    static std::string getBaseAndPyChild(IBase *base)
    {
        return base->baseAndPyChild();
    }

    static std::string getBaseAndChildFinal(IBase *base)
    {
        return base->baseAndChildFinal();
    }

protected:
    virtual int protectedMethod()
    {
        return 7;
    }

    virtual void protectedOutMethod(int *out, int inp)
    {
        *out = inp + 5;
    }
};

} // namespace inheritance
